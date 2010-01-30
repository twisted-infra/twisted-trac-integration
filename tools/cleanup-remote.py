from sys import argv
from os import environ, system

from twisted.python.log import err
from twisted.internet import reactor
from twisted.internet.utils import getProcessOutput

from cleanuplib import ticketsForBranchName, cleanup

def getBranches(branchesLocation):
    """
    Return a L{Deferred} which fires with a list of branch names relative to
    C{branchesLocation}.
    """
    d = getProcessOutput("svn", ["ls", branchesLocation], env=environ)
    def cbGotOutput(output):
        lines = output.splitlines()
        for name in lines:
            yield name.rstrip('/\n')
    d.addCallback(cbGotOutput)
    return d


class RemoteBranch:
    """
    Kind of look like a FilePath (minimally), but backed onto an svn
    repository.
    """
    def __init__(self, name, removed):
        self._name = name
        self._removed = removed


    def basename(self):
        return self._name


    def remove(self):
        self._removed[self._name] = True


    def sibling(self, name):
        return RemoteBranch(name, self._removed)


    def __cmp__(self, other):
        if isinstance(other, RemoteBranch):
            return cmp(self._name, other._name)
        return NotImplemented


    def __hash__(self):
        return hash(self._name)



def main(project, branchesLocation, tracker):
    removedBranches = {}
    branches = getBranches(branchesLocation)
    def cbGotBranchNames(branchNames):
        for name in branchNames:
            try:
                tickets = ticketsForBranchName(name)
            except ValueError, e:
                print "Skipping", name, ":", str(e)
            else:
                yield tickets, RemoteBranch(name, removedBranches)
    branches.addCallback(cbGotBranchNames)
    branches.addCallback(lambda branches: cleanup(tracker, branches))
    branches.addErrback(err, "Cleanup failed")
    reactor.callWhenRunning(branches.addBoth, lambda ign: reactor.stop())
    reactor.run()
    if not branchesLocation.endswith("/"):
        branchesLocation += "/"
    print "svn rm", " ".join([
        branchesLocation + name for name in removedBranches])



if __name__ == '__main__':
    if len(argv) != 4:
        print 'Usage: %s <project> <branches url> <tracker>' % (argv[0],)
    else:
        main(argv[1], argv[2], argv[3])
