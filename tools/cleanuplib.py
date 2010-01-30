
from twisted.python.log import err
from twisted.internet.defer import deferredGenerator, waitForDeferred
from twisted.web.client import getPage

def ticketsForString(string):
    """
    Given a string containing the ticket number parts of a branch name,
    return a list of tickets which are associated with that branch name.
    """
    if string.isdigit():
        return [string]
    parts = string.split('+')
    if filter(str.isdigit, parts) == parts:
        return parts
    return []


def ticketsForBranchName(branchName):
    """
    Given the name of a branch relative to the /branches/ directory, return
    a list of tickets which are associated with that branch name or raise
    ValueError if the branch name cannot be parsed.
    """
    parts = branchName.rsplit('-', 2)
    if len(parts) == 1:
        raise ValueError("unknown")
    else:
        tickets = ticketsForString(parts[-2])
        if len(tickets) == 0:
            tickets = ticketsForString(parts[-1])
        if len(tickets) == 0:
            raise ValueError("unparseable")
        else:
            return tickets


def closedTicket(trackerLocation, ticket):
    """
    Retrieve status information for the given ticket and return a Deferred
    which will fire with C{True} if the ticket is closed, C{False} otherwise.
    """
    def examineStatus(result):
        header, data = result.splitlines()
        header = header.split('\t')
        data = data.split('\t')
        status = header.index('status')
        print 'Status of', ticket, 'is', data[status]
        return data[status] == 'closed'

    if not trackerLocation.endswith('/'):
        trackerLocation += '/'
    url = trackerLocation + 'ticket/' + ticket + '?format=tab'
    d = getPage(url)
    d.addCallback(examineStatus)
    return d


def cleanup(trackerLocation, branches):
    # Force this to be serial so as not to knock over trac.
    def check():
        toRemove = set()
        statuses = {}
        ticketToBranches = {}
        for tickets, branch in branches:
            for ticket in tickets:
                ticketToBranches.setdefault(ticket, []).append(branch)

                if ticket not in statuses:
                    closed = waitForDeferred(closedTicket(trackerLocation, ticket))
                    yield closed
                    try:
                        closed = closed.getResult()
                    except:
                        err(None, "Error determined status of %s" % (ticket,))
                        break
                    else:
                        statuses[ticket] = closed

                if not statuses[ticket]:
                    break
            else:
                print 'Removing closed:', branch.basename()
                toRemove.add(branch)

        for ticket, dupBranches in ticketToBranches.iteritems():
            for branch in dupBranches:
                parts = branch.basename().rsplit('-', 2)
                # Try to only examine foo-ticket-counter
                if len(parts) == 3:
                    # Try to skip foo-bar-ticket
                    if ticketsForString(parts[1]):
                        try:
                            which = int(parts[2])
                            if which > 100:
                                # This probably isn't real, but a misnamed
                                # branch of some sort.
                                print "Strange branch name:", branch.basename()
                                raise ValueError()
                        except ValueError:
                            continue
                        else:
                            # Check for a -N where 2 <= N < which
                            for i in range(2, which):
                                older = branch.sibling("%s-%s-%d" % (parts[0], parts[1], i))
                                if older in dupBranches:
                                    # Yep, remove it.
                                    print "Removing obsolete", older.basename(), "(obsoleted by", branch.basename(), ")"
                                    toRemove.add(older)
                            # Check for the special spelling of -1
                            older = branch.sibling("%s-%s" % (parts[0], parts[1]))
                            if older in dupBranches:
                                # Yep, remove it.
                                print "Removing obsolete", older.basename(), "(obsoleted by", branch.basename(), ")"
                                toRemove.add(older)

        for branch in toRemove:
            branch.remove()

    return deferredGenerator(check)()
