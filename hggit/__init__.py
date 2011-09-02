# git.py - git server bridge
#
# Copyright 2008 Scott Chacon <schacon at gmail dot com>
#   also some code (and help) borrowed from durin42
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

'''push and pull from a Git server

This extension lets you communicate (push and pull) with a Git server.
This way you can use Git hosting for your project or collaborate with a
project that is in Git.  A bridger of worlds, this plugin be.

Try hg clone git:// or hg clone git+ssh://
'''

import inspect
import os
import re

from mercurial import bundlerepo
from mercurial import commands
from mercurial import demandimport
from mercurial import extensions
from mercurial import hg
from mercurial import localrepo
from mercurial import util as hgutil
from mercurial import url
from mercurial.i18n import _

demandimport.ignore.extend([
    'collections',
    ])

import gitrepo, hgrepo
from git_handler import GitHandler

# support for `hg clone git://github.com/defunkt/facebox.git`
# also hg clone git+ssh://git@github.com/schacon/simplegit.git
hg.schemes['git'] = gitrepo
hg.schemes['git+ssh'] = gitrepo

# support for `hg clone localgitrepo`
_oldlocal = hg.schemes['file']

try:
    urlcls = hgutil.url
except AttributeError:
    class urlcls(object):
        def __init__(self, path):
            self.p = hgutil.drop_scheme('file', path)

        def localpath(self):
            return self.p

def _local(path):
    p = urlcls(path).localpath()
    if (os.path.exists(os.path.join(p, '.git')) and
        not os.path.exists(os.path.join(p, '.hg'))):
        return gitrepo
    # detect a bare repository
    if (os.path.exists(os.path.join(p, 'HEAD')) and
        os.path.exists(os.path.join(p, 'objects')) and
        os.path.exists(os.path.join(p, 'refs')) and
        not os.path.exists(os.path.join(p, '.hg'))):
        return gitrepo
    return _oldlocal(path)

hg.schemes['file'] = _local

hgdefaultdest = hg.defaultdest
def defaultdest(source):
    for scheme in ('git', 'git+ssh'):
        if source.startswith('%s://' % scheme) and source.endswith('.git'):
            source = source[:-4]
            break
    return hgdefaultdest(source)
hg.defaultdest = defaultdest

# defend against tracebacks if we specify -r in 'hg pull'
def safebranchrevs(orig, lrepo, repo, branches, revs):
    revs, co = orig(lrepo, repo, branches, revs)
    if getattr(lrepo, 'changelog', False) and co not in lrepo.changelog:
        co = None
    return revs, co
if getattr(hg, 'addbranchrevs', False):
    extensions.wrapfunction(hg, 'addbranchrevs', safebranchrevs)

changeset_re = None # Cached regular expression for a changeset string
cached_repo = None  # Cached copy of the repo sent to reposetup
cached_git = None   # Cached githandler for cached_repo

def uisetup(ui):
    class ext_ui(ui.__class__):
        # Extend the UI class so that when it prints an hg changeset hash, it also prints a git changeset.
        def write(self, *args, **kwargs):
            super(ext_ui, self).write(*args, **kwargs)
            # Changesets are printed twice in the current hg code, always with label log.changeset
            if kwargs.has_key('label') and kwargs['label'] == 'log.changeset' and len(args) and cached_repo:
                global changeset_re
                global cached_git
                if not changeset_re:
                    changeset_re = re.compile('(\d+):\w+(\s*)$')
                match = changeset_re.search(args[0])
                if match:
                    # Parse out from the changeset string: The numeric local rev, and the line terminator
                    # (So that we know if we need to print the git revision with a newline or not)
                    rev, terminator = match.group(1,2)
                    from mercurial.templatefilters import hexfilter, short
                    hgsha = cached_repo.lookup(int(rev)) # Ints are efficient on lookup
                    if (hgsha):
                        hgsha = hexfilter(hgsha)
                        if not cached_git:
                            cached_git = GitHandler(cached_repo, self)
                        gitsha = cached_git.map_git_get(hgsha)
                    else: # Currently this case is hit when you do hg outgoing. I'm not sure why.
                        gitsha = None
                    
                    if gitsha:
                        if terminator == '\n': # hg log, etc
                            output = _("git-rev:     %s\n")
                        else:                  # hg sum
                            output = "git:%s "
                        super(ext_ui, self).write(output % (short(gitsha)), label='log.gitchangeset')

    ui.__class__ = ext_ui

def reposetup(ui, repo):
    if not isinstance(repo, gitrepo.gitrepo):
        klass = hgrepo.generate_repo_subclass(repo.__class__)
        repo.__class__ = klass
        
    global cached_repo
    cached_repo = repo

def gimport(ui, repo, remote_name=None):
    git = GitHandler(repo, ui)
    git.import_commits(remote_name)

def gexport(ui, repo):
    git = GitHandler(repo, ui)
    git.export_commits()

def gclear(ui, repo):
    repo.ui.status(_("clearing out the git cache data\n"))
    git = GitHandler(repo, ui)
    git.clear()
	
def gsummary(ui, repo):
    ctx = repo[None]
    parents = ctx.parents()
    git = GitHandler(repo, ui)
    for p in parents:
        repo.ui.status(_('git-rev: %s\n') % git.map_git_get(p.hex()))

def git_cleanup(ui, repo):
    new_map = []
    for line in repo.opener(GitHandler.mapfile):
        gitsha, hgsha = line.strip().split(' ', 1)
        if hgsha in repo:
            new_map.append('%s %s\n' % (gitsha, hgsha))
    f = repo.opener(GitHandler.mapfile, 'wb')
    map(f.write, new_map)
    ui.status(_('git commit map cleaned\n'))

# drop this when we're 1.6-only, this just backports new behavior
def sortednodetags(orig, *args, **kwargs):
    ret = orig(*args, **kwargs)
    ret.sort()
    return ret
extensions.wrapfunction(localrepo.localrepository, 'nodetags', sortednodetags)

try:
    from mercurial import discovery
    kwname = 'heads'
    if hg.util.version() >= '1.7':
        kwname = 'remoteheads'
    if getattr(discovery, 'findcommonoutgoing', None):
        kwname = 'onlyheads'
    def findoutgoing(orig, local, remote, *args, **kwargs):
        if isinstance(remote, gitrepo.gitrepo):
            # clean up this cruft when we're 1.7-only, remoteheads and
            # the return value change happened between 1.6 and 1.7.
            kw = {}
            kw.update(kwargs)
            for val, k in zip(args, ('base', kwname, 'force')):
                kw[k] = val
            git = GitHandler(local, local.ui)
            base, heads = git.get_refs(remote.path)
            newkw = {'base': base, kwname: heads}
            newkw.update(kw)
            kw = newkw
            if kwname == 'heads':
                r = orig(local, remote, **kw)
                return [x[0] for x in r]
            if kwname == 'onlyheads':
                del kw['base']
            return orig(local, remote, **kw)
        return orig(local, remote, *args, **kwargs)
    if getattr(discovery, 'findoutgoing', None):
        extensions.wrapfunction(discovery, 'findoutgoing', findoutgoing)
    else:
        extensions.wrapfunction(discovery, 'findcommonoutgoing',
                                findoutgoing)
except ImportError:
    pass

def getremotechanges(orig, ui, repo, other, *args, **opts):
    if isinstance(other, gitrepo.gitrepo):
        revs = opts.get('onlyheads', opts.get('revs'))
        git = GitHandler(repo, ui)
        r, c, cleanup = git.getremotechanges(other, revs)
        # ugh. This is ugly even by mercurial API compatibility standards
        if 'onlyheads' not in orig.func_code.co_varnames:
            cleanup = None
        return r, c, cleanup
    return orig(ui, repo, other, *args, **opts)
try:
    extensions.wrapfunction(bundlerepo, 'getremotechanges', getremotechanges)
except AttributeError:
    # 1.7+
    pass

cmdtable = {
  "gimport":
        (gimport, [], _('hg gimport')),
  "gexport":
        (gexport, [], _('hg gexport')),
  "gclear":
      (gclear, [], _('Clears out the Git cached data')),
  "gsummary":
      (gsummary, [], _('Shows current full Git revision hash')),
  "git-cleanup": (git_cleanup, [], _(
        "Cleans up git repository after history editing"))
}
