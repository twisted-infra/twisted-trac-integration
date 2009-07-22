
import sys

from epsilon.extime import Time
from datetime import timedelta

import tracstats


def isClosingChange(change):
    return (
        change['field'] == 'status' and
        change['old'] != 'closed' and
        change['new'] == 'closed')


def isOpeningChange(change):
    return (
        change['field'] == 'status' and
        change['old'] == 'closed' and
        change['new'] != 'closed')


def main(cursor):
    # All the ticket data in the database
    tickets = tracstats.tickets(cursor)

    # For the purposes of means, anything that is open gets a "close" time of
    # right now.
    now = Time().asNaiveDatetime()

    # A mapping from ticket id to a two-tuple of open, closed times.  If a
    # ticket is closed multiple times, the closed time associated with it is
    # the final close time.  If the ticket is open, the closed time is None.
    ticketInfos = {}
    for id, tkt in tickets.iteritems():
        ticketInfos[id] = (tkt['time'], now)

    # Find all the latest close times for all the tickets
    for change in tracstats.changes(cursor,
                                    Time.fromPOSIXTimestamp(0).asNaiveDatetime(),
                                    now):
        id = change['ticket']
        open, close = ticketInfos[id]
        if isOpeningChange(change):
            ticketInfos[id] = (open, now)
        elif isClosingChange(change):
            ticketInfos[id] = (open, change['time'])

    # Create an ordering of ticket open and close times
    events = []
    for ticketId, (open, close) in ticketInfos.iteritems():
        if close is None:
            print 'Skipping', ticketId
            continue
        events.append((open, ticketId, 'open'))
        events.append((close, ticketId, 'close'))
    events.sort()

    # A mapping of tickets which are open at the point in the events which to
    # which processing has advanced.  Keys are ticket ids, values are times
    # when they opened.
    openTickets = {}

    # Data points for the output graph.  First element of each two-tuple is a
    # time, second element is mean ticket age at that time.
    output = []

    for (when, ticket, change) in events:
        if openTickets:
            output.append((
                    when,
                    sum([when - v
                         for v
                         in openTickets.itervalues()],
                        timedelta(0)) / len(openTickets)))
        if change == 'open':
            # A new ticket is now open.
            openTickets[ticket] = when
        elif change == 'closed':
            # An old open ticket is now closed.
            del openTickets[ticket]

    def toInt(delta):
        return delta.days * (60 * 60 * 24) + delta.seconds

    return tracstats.TimeSeries(
        "mean ticket age",
        [(when, toInt(mean))
         for (when, mean)
         in output])


if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
