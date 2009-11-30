
import subprocess

from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from enforcenews import getOutput, __file__ as hookFile


def run(command):
    pipe = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    code = pipe.wait()
    if code:
        raise RuntimeError(
            "%r exited with code %d and stderr %s" % (command, code, stderr))


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


    def changed(self, revision):
        return getOutput(
            ["/usr/bin/svnlook", "changed", self.repository.path,
             "--revision", str(revision)])


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
        changed = self.changed(3)
        self.assertSubstring("A   branches/some-branch/some-file", changed)


    def test_tagCommit(self):
        """
        Tag commits are not required to do anything in particular.
        """
        # Copy trunk to a tag
        tag = self.tags.child("some-tag")
        run(["svn", "cp", self.trunk.path, tag.path])
        self.commit(self.tags, "Create some tag")

        # It should exist.
        changed = self.changed(2)
        self.assertSubstring("A   tags/some-tag/", changed)


    def test_trunkCommitWithoutNews(self):
        """
        Committing to trunk with a I{Fixes} tag but without adding a ticket
        file to the topfiles directory results in a rejection from the
        pre-commit hook.
        """
        # Toss a file with the wrong ticket number in it into trunk.
        topfiles = self.trunk.child("topfiles")
        topfiles.makedirs()
        feature = topfiles.child("123.feature")
        feature.setContent("hello")
        self.add(topfiles)
        self.assertRaises(
            RuntimeError,
            self.commit, self.trunk, "Add some junk.  Fixes: #321")


    def test_trunkCommitWithNews(self):
        """
        Committing to trunk with a I{Fixes} tag is allowed if a corresponding
        file is added to the topfiles directory.
        """
        topfiles = self.trunk.child("topfiles")
        topfiles.makedirs()
        feature = topfiles.child("123.feature")
        feature.setContent("hello")
        self.add(topfiles)
        self.commit(self.trunk, "Add some junk.  Fixes: #123")

        # It should exist.
        changed = self.changed(2)
        self.assertSubstring("A   trunk/topfiles/123.feature", changed)
