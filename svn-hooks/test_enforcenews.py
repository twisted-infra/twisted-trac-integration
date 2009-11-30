
import subprocess

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from enforcenews import getOutput, __file__ as hookFile


def run(command):
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE)
    code = pipe.wait()
    if code:
        raise RuntimeError("%r exited with code %d" % (command, code))


class MainTests(TestCase):
    """
    Tests for the main function in L{enforcenews}.
    """
    def fileURI(self, path):
        return 'file://' + path


    def add(self, *paths):
        run(["svn", "add"] + [p.path for p in paths])


    def commit(self, checkout, message):
        run(["svn", "commit", "-m", message, checkout.path])


    def setUp(self):
        """
        Create a minimal svn repository which the hook can be tested against
        """
        self.repository = FilePath(self.mktemp())
        self.checkout = FilePath(self.mktemp())
        run(["svnadmin", "create", self.repository.path])
        run(["svn", "checkout", self.fileURI(self.repository.path), self.checkout.path])
        self.trunk = self.checkout.child("trunk")
        self.trunk.makedirs()
        self.branches = self.checkout.child("branches")
        self.branches.makedirs()
        self.tags = self.checkout.child("tags")
        self.tags.makedirs()
        self.add(self.trunk, self.branches, self.tags)
        self.commit(self.checkout, "Initial repository structure")

        # Install the hook
        self.hook = self.repository.child("hooks").child("pre-commit")
        FilePath(hookFile).copyTo(self.hook)
        self.hook.chmod(0700)


    def test_branchCommit(self):
        """
        Branch commits are not required to do anything in particular.
        """
        # Copy trunk to a branch
        branch = self.branches.child("some-branch")
        run(["svn", "cp", self.trunk.path, branch.path])
        self.commit(self.branches, "Create some branch")
        someFile = branch.child("some-file")
        someFile.setContent("some bytes")
        self.add(someFile)
        self.commit(branch, "Add some file.  Fixes: #1234")

        # It should exist.
        changed = getOutput(
            ["/usr/bin/svnlook", "changed", self.repository.path, "--revision", "2"])
        print changed
