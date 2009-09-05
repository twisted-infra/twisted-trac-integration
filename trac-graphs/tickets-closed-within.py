
import sys

import tracstats


def ticketsClosedWithin(tickets, cursor):
    """
    Return an iterator of two-tuples of L{timedelta} instances and the
    number of tickets which were closed less than that amount of time after
    being opened.
    """
    durationsOpen = []
    for t in tickets:
        if t['status'] == 'closed':
            # Find out when it changes
            change = closed = None
            for change in tracstats.allChanges(cursor, t['id']):
                if change['field'] == 'status' and change['new'] == 'closed':
                    closed = change['time']
            if closed is None:
                print 'Closed ticket (#%s) with no closed change!' % (t['id'],),
                if change is None:
                    print '(And it has no changes at all, what the hell)'
                else:
                    print '(Assuming it was closed at the time of its last change)'
                    closed = change['time']
            else:
                duration = closed - t['time']
                durationsOpen.append(duration)

    durationsOpen.sort()
    durationsOpen.reverse()
    counter = 1
    while durationsOpen:
        current = durationsOpen.pop()
        while durationsOpen and durationsOpen[-1] == current:
            counter += 1
            durationsOpen.pop()
        yield current, counter
        if durationsOpen:
            counter += 1
            current = durationsOpen.pop()
        else:
            break


def main(cursor):
    tickets = tracstats.tickets(cursor).values()
    return tracstats.DeltaSeries(
        'Tickets Closed Within',
        ticketsClosedWithin(tickets, cursor))

if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
