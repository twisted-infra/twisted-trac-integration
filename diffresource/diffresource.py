
from csv import reader
from os.path import expanduser, exists
from os import environ, close, mkdir
from tempfile import mkstemp

from zope.interface import implements

from combinator.branchmgr import theBranchManager

from twisted.web.server import NOT_DONE_YET
from twisted.web.resource import IResource
from twisted.web.error import Error
from twisted.web.client import getPage
from twisted.internet.utils import getProcessOutputAndValue
from twisted.python.filepath import FilePath
from twisted.internet.defer import DeferredLock, gatherResults

chbranch = expanduser("~/Projects/Divmod/trunk/Combinator/bin/chbranch")
unbranch = expanduser("~/Projects/Divmod/trunk/Combinator/bin/unbranch")


def getProcessOutput(command, argv, env):
    d = getProcessOutputAndValue(command, argv, env=env)
    def massage((out, err, code)):
        if err:
            raise IOError(err)
        return out
    d.addBoth(massage)
    return d


def csv(text):
    content = iter(reader(text.splitlines()))
    header = content.next()
    rows = []
    for entries in content:
        rows.append(dict(zip(header, entries)))
    return rows


def htmlQuote(s):
    return s.replace(
        '&', '&amp;').replace(
        '<', '&lt;').replace(
        '>', '&gt;')



class DiffContainer(object):
    implements(IResource)

    pageTemplate = '<html><head><title>Reviews</title></head><body>%(tickets)s</body></html>'
    ticketTemplate = '<div><a href="%(url)s">%(text)s</a></div>'

    trackerRoot = "http://twistedmatrix.com/trac/"
    projectName = "Twisted"

    # IResource
    isLeaf = False

    def getChild(self, path, request):
        """
        Create L{DiffResource}s.
        """
        if path == '':
            return self
        return DiffResource(self.trackerRoot, self.projectName, int(path))
    getChildWithDefault = getChild


    def render(self, request):
        """
        Render links to L{DiffResource}s for all tickets up for review which
        have branches.
        """
        location = self.trackerRoot + (
            'query?'
            'status=new&'
            'status=assigned&'
            'status=reopened&'
            'branch=%21&'
            'keywords=%7Ereview&'
            'order=priority&'
            'format=csv')
        reviewTicketsWithBranch = getPage(location)
        def gotTickets(tickets):
            return self.pageTemplate % {
                'tickets': ''.join([
                    self.ticketTemplate % {
                        'url': ticket['id'],
                        'text': htmlQuote(ticket['summary'])}
                    for ticket in tickets])}
        def ebRender(failure):
            failure.printTraceback(file=request)
        reviewTicketsWithBranch.addCallback(csv)
        reviewTicketsWithBranch.addCallback(gotTickets)
        reviewTicketsWithBranch.addCallbacks(request.write, ebRender)
        reviewTicketsWithBranch.addCallback(lambda ignored: request.finish())
        return NOT_DONE_YET


sourceLock = DeferredLock()


class DiffResource(object):
    """
    Render the output of C{svn diff} 
    """
    implements(IResource)

    pageTemplate = '%(diffstat)s%(diff)s'

    def __init__(self, trackerRoot, projectName, ticket):
        self.trackerRoot = trackerRoot
        self.projectName = projectName
        self.projectTrunk = theBranchManager.projectBranchDir(projectName)
        self.ticket = ticket


    def _diffAndStat(self, request):
        request.setHeader('content-type', 'text/plain')

        # First find the branch for the ticket requested.
        ticketFields = getPage(
            self.trackerRoot + 'ticket/' + str(self.ticket) + '?format=csv')
        ticketFields.addCallback(csv)

        def gotFields(rows):
            fields = rows[0]
            if fields['status'] == 'closed':
                raise Exception("That ticket is closed.")
            return fields['branch'].split('/')[1]
        ticketFields.addCallback(gotFields)

        def checkBranchExistence(branch):
            # Only try to compute a diff if the branch still exists in
            # the HEAD revision.
            d = getPage(self.trackerRoot + 'browser/branches/' + branch)
            def succeeded(ignored):
                return branch
            def failed(reason):
                reason.trap(Error)
                raise Exception("That ticket's branch no long exists.")
            d.addCallbacks(succeeded, failed)
            return d
        ticketFields.addCallback(checkBranchExistence)

        def gotBranch(branch):
            # Check it out with Combinator
            return getProcessOutput(chbranch, (self.projectName, branch), env=environ)
        ticketFields.addCallback(gotBranch)

        def didChangeBranch(ignored):
            # Clean up trunk
            return getProcessOutput("svn", ("revert", "-R", self.projectTrunk), env=environ)
        ticketFields.addCallback(didChangeBranch)

        def didCleanUpTrunk(ignored):
            # Clean it up some more
            return getProcessOutput("svn", ("st", self.projectTrunk), env=environ)
        ticketFields.addCallback(didCleanUpTrunk)

        def gotStatus(lines):
            status = lines.splitlines()
            for aStatus in status:
                if aStatus.startswith('?'):
                    ignored, fileName = aStatus.split(None, 1)
                    FilePath(self.projectTrunk).preauthChild(fileName).remove()
        ticketFields.addCallback(gotStatus)

        def reallyCleanedUp(ignored):
            # Merge
            return getProcessOutput(unbranch, (self.projectName,), env=environ)
        ticketFields.addCallback(reallyCleanedUp)

        def didMerge(ignored):
            # Get the diff
            return getProcessOutput("svn", ("diff", self.projectTrunk), env=environ)
        ticketFields.addCallback(didMerge)

        def gotDiff(diff):
            # Get diffs for the adds, too.  Groan.
            mergeStatus = getProcessOutput("svn", ("status", self.projectTrunk), env=environ)
            def gotStatus(status):
                extraDiffs = []
                lines = status.splitlines()
                for L in lines:
                    if L.startswith('A'):
                        ignored, ignored, fileName = L.split(None, 2)
                        path = FilePath(self.projectTrunk).preauthChild(fileName)
                        if not path.isdir():
                            extraDiffs.append(
                                getProcessOutput(
                                    "diff", ("-u", "/dev/null", path.path), env=environ))
                return gatherResults(extraDiffs)
            def gotExtraDiffs(results):
                return '\n'.join(results + [diff])

            mergeStatus.addCallback(gotStatus)
            mergeStatus.addCallback(gotExtraDiffs)
            return mergeStatus
        ticketFields.addCallback(gotDiff)

        def gotAllDiffs(diff):
            # Get the diffstat for it.
            if not exists('tmp'):
                mkdir('tmp')
            fileFileno, diffFile = mkstemp(dir='tmp')
            fObj = file(diffFile, 'w')
            fObj.write(diff)
            fObj.close()
            close(fileFileno)
            diffStat = getProcessOutput('sh', ('-c', 'cat %s | diffstat' % (diffFile,)), env=environ)
            def gotStat(stat):
                return self.pageTemplate % {'diff': diff, 'diffstat': stat}
            diffStat.addCallback(gotStat)
            return diffStat
        ticketFields.addCallback(gotAllDiffs)

        def ebRender(failure):
            failure.printTraceback(file=request)
        ticketFields.addCallbacks(request.write, ebRender)

        ticketFields.addCallback(lambda ignored: request.finish())

        def cleanupSubversion(ignored):
            # After the user has their page, clean up svn's tempfiles.
            # Otherwise these accumulate over time and branching
            # becomes more and more expensive (in time and disk
            # usage).  We don't need to do this in the critical path
            # though.
            return getProcessOutput('svn', ('cleanup', self.projectTrunk), env=environ)
        ticketFields.addCallback(cleanupSubversion)

        return ticketFields


    def render(self, request):
        # Only one of these can run at a time, since the project source tree
        # is a shared resource.
        sourceLock.run(self._diffAndStat, request)
        return NOT_DONE_YET



if __name__ == '__main__':
    from twisted.web.server import Site
    from twisted.internet import reactor
    reactor.listenTCP(8080, Site(DiffContainer()))
    reactor.run()
