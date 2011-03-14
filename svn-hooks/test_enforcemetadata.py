
from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from testlib import SubversionMixin, run

from enforcemetadata import __file__ as hookFile


class MainTests(TestCase, SubversionMixin):
    """
    Tests for the main function in L{enforcemetadata}.
    """
    def setUp(self):
        """
        Create a minimal svn repository which the hook can be tested against.
        """
        self.createBasicRepository(hookFile)


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


    def test_normalTrunkCommit(self):
        """
        A commit to trunk with svn is allowed.
        """
        # Put some content in trunk
        content = self.trunk.child("content")
        content.setContent("data")
        run(["svn", "add", content.path])
        self.commit(self.tags, "Create some data")

        # Make sure it is there.
        changed = self.changed(2)
        self.assertSubstring("A    trunk/content", changed)


    def test_bzrsvnCommitRejected(self):
        """
        A commit to trunk with bzr-svn that includes bzr metadata is not
        allowed.
        """
        # Make a bzr branch with some content.
        branch = FilePath(self.mktemp())
        run(["bzr", "branch", self.trunk.path, branch.path])
        content = branch.child("content")
        content.setContent("data")
        run(["bzr", "add", content.path])
        run(["bzr", "commit", "-m", "content for you", content.path])

        # Merge it into svn
        run(["bzr", "merge", "-d", self.trunk.path, branch.path])

        # But not really
        self.assertRaises(
            RuntimeError,
            self.commit, self.trunk, "This is bad bzr stuff")
