from mercurial import repo, util
try:
    from mercurial.error import RepoError
except ImportError:
    from mercurial.repo import RepoError

from git_handler import GitHandler

class gitrepo(repo.repository):
    capabilities = ['lookup']

    def __init__(self, ui, path, create):
        if create: # pragma: no cover
            raise util.Abort('Cannot create a git repository.')
        self.ui = ui
        self.path = path

    def lookup(self, key):
        if isinstance(key, str):
            return key

    def local(self):
        if not self.path:
            raise RepoError

    def heads(self):
        return []

    def listkeys(self, namespace):
        return {}

    def pushkey(self, namespace, key, old, new):
        return False

    # used by incoming in hg <= 1.6
    def branches(self, nodes):
        return []

instance = gitrepo

def islocal(path):
    u = util.url(path)
    return not u.scheme or u.scheme == 'file'
