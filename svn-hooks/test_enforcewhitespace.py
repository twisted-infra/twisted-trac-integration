
from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from testlib import SubversionMixin, run

from enforcewhitespace import __file__ as hookFile

class MainTests(TestCase, SubversionMixin):
    """
    Tests for the main function in L{enforcewhitespace}.
    """
    def setUp(self):
        """
        Create a minimal svn repository which the hook can be tested against
        """
        self.repository = FilePath(self.mktemp())
        self.checkout = FilePath(self.mktemp())
        self.standardRepository(self.repository, self.checkout)
        self.trunk = self.checkout.child("trunk")
        self.branches = self.checkout.child("branches")
        self.tags = self.checkout.child("tags")
        self.installHook(self.repository, hookFile)


    def test_branchCommit(self):
        """
        Branch commits are not required to have sensible whitespace.
        """
        # Copy trunk to a branch.
        branch = self.branches.child("some-branch")
        run(["svn", "cp", self.trunk.path, branch.path])
        self.commit(self.branches, "Create some branch")
        someFile = branch.child("some-file")
        someFile.setContent("trailing whitespace and no terminal newline! ")
        self.add(someFile)
        self.commit(branch, "Add a file with poor whitespace.")

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


    def test_trunkCommit(self):
        """
        A trunk commit which introduces no new trailing whitespace nor causes
        any files to lack a final newline is accepted.
        """
        goodFile = self.trunk.child("good-file")
        goodFile.setContent("this file is nice\n")
        self.add(goodFile)
        self.commit(self.trunk, "Add a good file.")

        # It should have been added.
        changed = self.changed(2)
        self.assertSubstring("A   trunk/good-file", changed)


    def test_trunkCommitWithTrailingWhitespace(self):
        """
        A trunk commit which introduces trailing whitespace is rejected.
        """
        badFile = self.trunk.child("bad-file")
        badFile.setContent("this file is bad  \n")
        self.add(badFile)
        self.assertRaises(
            RuntimeError,
            self.commit, self.trunk, "Add a bad file")
