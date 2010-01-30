# Delete working copies of branches which are associated with tickets which
# have been closed.

from os.path import expanduser
from sys import argv

from twisted.python.filepath import FilePath
from twisted.python.log import err
from twisted.internet import reactor

from cleanuplib import ticketsForBranchName, cleanup


def getBranches(branchesContainer):
    """
    Yield tuples of ticket numbers (as a list of strings) and directory (as
    a FilePath) of branches inside the given directory.
    """
    for branch in sorted(branchesContainer.children()):
        if branch.isdir():
            try:
                tickets = ticketsForBranchName(branch.basename())
            except ValueError, e:
                print 'Skipping', branch.basename(), ':', str(e)
            else:
                print 'Found', branch.basename(), 'for ticket(s):', ', '.join(tickets)
                yield tickets, branch


def main(project, tracker):
    branchesContainer = FilePath(
        expanduser('~')).child(
        'Projects').child(
        project).child(
        'branches')
    branches = getBranches(branchesContainer)
    d = cleanup(tracker, branches)
    d.addErrback(err, "Cleanup failed")
    reactor.callWhenRunning(d.addBoth, lambda ign: reactor.stop())
    reactor.run()



if __name__ == '__main__':
    if len(argv) != 3:
        print 'Usage: %s <project> <tracker>' % (argv[0],)
    else:
        main(argv[1], argv[2])
