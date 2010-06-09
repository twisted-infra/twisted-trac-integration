import subprocess

from twisted.python.filepath import FilePath

from enforcenews import getOutput

def run(command):
    pipe = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    code = pipe.wait()
    if code:
        raise RuntimeError(
            "%r exited with code %d and stderr %s" % (command, code, stderr))

class SubversionMixin(object):
    def fileURI(self, path):
        return 'file://' + path


    def add(self, *paths):
        run(["svn", "add"] + [p.path for p in paths])


    def commit(self, checkout, message):
        run(["svn", "commit", "-m", message, checkout.path])


    def changed(self, revision):
        return getOutput(
            ["/usr/bin/svnlook", "changed", self.repository.path,
             "--revision", str(revision)])


    def standardRepository(self, repository, checkout):
        run(["svnadmin", "create", repository.path])
        run(["svn", "checkout", self.fileURI(repository.path), checkout.path])
        trunk = checkout.child("trunk")
        trunk.makedirs()
        branches = checkout.child("branches")
        branches.makedirs()
        tags = checkout.child("tags")
        tags.makedirs()
        self.add(trunk, branches, tags)
        self.commit(checkout, "Initial repository structure")


    def installHook(self, repository, hookFile):
        # Install the hook
        self.hook = self.repository.child("hooks").child("pre-commit")
        FilePath(hookFile).copyTo(self.hook)
        self.hook.chmod(0700)

