
import sys
from datetime import datetime, timedelta

import tracstats

def _openTicketsOverTime(tickets, changes, interval):
    everything = [(t, True) for t in tickets]
    everything.extend([(c, False) for c in changes])
    everything.sort(key=lambda (data, ignored): data['time'])

    limit = everything[0][0]['time']
    openTickets = set()
    for (data, isTicket) in everything:
        if data['time'] >= limit:
            yield (limit, openTickets)
            limit += interval
        if isTicket:
            if data['status'] == 'closed':
                # If it's closed, make sure there is some record of this
                # happening.  Old roundup tickets don't have this, so we can't
                # count it as open.
                for change in data['changes']:
                    if change['field'] == 'status':
                        # Okay, it's got a valid close change.  Count it as
                        # open until we get there.
                        openTickets.add(data['id'])
                        break
                else:
                    # Never found a status change - count it as closed (by not
                    # adding it to the openTickets set).
                    pass
            else:
                # It's not closed, count it as open.
                openTickets.add(data['id'])
        else:
            if data['field'] == 'status':
                if data['old'] != 'closed' and data['new'] == 'closed':
                    openTickets.remove(data['ticket'])
                elif data['old'] == 'closed' and data['new'] != 'closed':
                    openTickets.add(data['ticket'])
    yield (limit, openTickets)



def openTicketsOverTime(tickets, changes, interval):
    """
    Return an iterator of two-tuples of timestamps and the number of tickets
    which were open immediately before that point in time.

    @param tickets: A list of dicts giving ticket information.  Each dict must
        have a C{'time'} key associated with a L{datetime} instance giving the
        time when the ticket was created.  The list need not be sorted.

    @param changes: A list of dicts giving ticket change information.  Each
        dict must have C{'time'}, C{'field'}, C{'old'}, and C{'new'} fields.
        If C{'field'} is C{'status'} then values for C{'old'} and C{'new'} of
        anything except C{'closed'} and C{'closed'} respectively indicate the
        closing of a ticket and the reverse indicates re-opening of a ticket.
        The list need not be sorted.

    @param interval: A L{timedelta} instance which will be used to determine
        how to space the yielded timestamps.
    """
    for when, tickets in _openTicketsOverTime(tickets, changes, interval):
        yield when, len(tickets)


def main(cursor):
    tickets = tracstats.tickets(cursor).values()
    changes = tracstats.changes(cursor, tickets[0]['time'], datetime.now())
    return tracstats.TimeSeries(
        'Open Tickets',
        openTicketsOverTime(tickets, changes, timedelta(days=7)))


if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
