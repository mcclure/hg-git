import os

from mercurial.node import bin
from mercurial import error
from mercurial.i18n import _

from git_handler import GitHandler
from gitrepo import gitrepo

def generate_repo_subclass(baseclass):
    class hgrepo(baseclass):
        def pull(self, remote, heads=None, force=False):
            if isinstance(remote, gitrepo):
                git = GitHandler(self, self.ui)
                return git.fetch(remote.path, heads)
            else: #pragma: no cover
                return super(hgrepo, self).pull(remote, heads, force)

        # TODO figure out something useful to do with the newbranch param
        def push(self, remote, force=False, revs=None, newbranch=None):
            if isinstance(remote, gitrepo):
                git = GitHandler(self, self.ui)
                git.push(remote.path, revs, force)
            else: #pragma: no cover
                # newbranch was added in 1.6
                if newbranch is None:
                    return super(hgrepo, self).push(remote, force, revs)
                else:
                    return super(hgrepo, self).push(remote, force, revs,
                                                    newbranch)

        def findoutgoing(self, remote, base=None, heads=None, force=False):
            if isinstance(remote, gitrepo):
                git = GitHandler(self, self.ui)
                base, heads = git.get_refs(remote.path)
                out, h = super(hgrepo, self).findoutgoing(remote, base, heads, force)
                return out
            else: #pragma: no cover
                return super(hgrepo, self).findoutgoing(remote, base, heads, force)

        def _findtags(self):
            (tags, tagtypes) = super(hgrepo, self)._findtags()

            git = GitHandler(self, self.ui)
            for tag, rev in git.tags.iteritems():
                tags[tag] = bin(rev)
                tagtypes[tag] = 'git'

            return (tags, tagtypes)

        def gitrefs(self):
            tagfile = self.join(os.path.join('git-remote-refs'))
            if os.path.exists(tagfile):
                tf = open(tagfile, 'rb')
                tagdata = tf.read().split('\n')
                td = [line.split(' ', 1) for line in tagdata if line]
                return dict([(name, bin(sha)) for sha, name in td])
            return {}

        def tags(self):
            if hasattr(self, 'tagscache') and self.tagscache:
                # Mercurial 1.4 and earlier.
                return self.tagscache
            elif hasattr(self, '_tags') and self._tags:
                # Mercurial 1.5 and later.
                return self._tags

            git = GitHandler(self, self.ui)
            tagscache = super(hgrepo, self).tags()
            tagscache.update(self.gitrefs())
            for tag, rev in git.tags.iteritems():
                if tag in tagscache:
                    continue

                tagscache[tag] = bin(rev)
                if hasattr(self, '_tagstypecache'):
                    # Only present in Mercurial 1.3 and earlier.
                    self._tagstypecache[tag] = 'git'

            return tagscache
            
        def lookup(self, key): # Allow for update, diff etc. against git rev #s
            try:
                return super(hgrepo, self).lookup(key)
            except error.RepoLookupError as notfound:
                if not key:             # If key is nonempty...
                    raise notfound
                if key[0] == 'g':       # To allow revs like g1144
                    key = key[1:]
                if not key:             # If key is STILL nonempty...
                    raise notfound
                found = None
                git = GitHandler(self, self.ui)
                for gitsha, hgsha in git._map_git.iteritems():
                    if gitsha.startswith(key):
                        try:
                            print hgsha
                            newfound = super(hgrepo, self).lookup(hgsha)
                            if found: # If we find more than one key...
                                raise error.LookupError(key, "hg-git",
                                    _('ambiguous identifier'))
                            else:
                                found = newfound
                        # hg-git knows about some revisions that hg doesn't. If these come
                        # up in _map_git, super().lookup() will throw a RepoLookupError.
                        # In this case we just pretend we never saw the revision.
                        except error.RepoLookupError:
                            pass
                            
                if found:
                    return found
                raise notfound # If still here, really nothing found

    return hgrepo
