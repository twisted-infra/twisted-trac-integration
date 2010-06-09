
from twisted.python.filepath import FilePath
from twisted.trial.unittest import TestCase

from testlib import SubversionMixin, run
from enforcenews import __file__ as hookFile, fileSetForTicket


class MainTests(TestCase, SubversionMixin):
    """
    Tests for the main function in L{enforcenews}.
    """
    def setUp(self):
        """
        Create a minimal svn repository which the hook can be tested against.
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


    def test_trunkRevertWithNews(self):
        """
        Reverting a previous trunk commit with a changelog message which uses
        I{Reopens} is required to remove the corresponding topfiles entry.
        """
        # First add something to revert.
        topfiles = self.trunk.child("topfiles")
        topfiles.makedirs()
        feature = topfiles.child("123.feature")
        feature.setContent("hello")
        self.add(topfiles)
        self.commit(self.trunk, "Add some junk.  Fixes: #123")

        # Now revert it.  More or less.
        run(["svn", "rm", feature.path])
        self.commit(self.trunk, "Revert some junk.  Reopens: #123")


    def test_trunkRevertWithoutNews(self):
        """
        If a I{Reopens} tag is used but no corresponding file is removed from
        topfiles, the commit is rejected.
        """
        # First add something to revert.
        topfiles = self.trunk.child("topfiles")
        topfiles.makedirs()
        feature = topfiles.child("123.feature")
        feature.setContent("hello")
        self.add(topfiles)
        self.commit(self.trunk, "Add some junk.  Fixes: #123")

        # Now revert it without removing the file.
        feature.setContent("goodbye")
        self.assertRaises(
            RuntimeError,
            self.commit, self.trunk, "Revert some junk.  Reopens: #123")



class OtherTests(TestCase):
    """
    Tests for other code in L{enforcenews}.
    """
    def test_fileSetForTicket(self):
        """
        L{fileSetForTicket} returns a C{set} with a name for each possible
        fragment type for the ticket passed to it.
        """
        self.assertEquals(
            fileSetForTicket(1234),
            set(["1234.feature", "1234.bugfix", "1234.doc",
                 "1234.removal", "1234.misc"]))
