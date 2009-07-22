
import sys
from datetime import timedelta

import tracstats

def totalTicketsOverTime(tickets, interval):
    """
    Return an iterator of two-tuples of timestamps and the number of tickets
    which existed immediately before that point in time.

    @param tickets: A list of dicts giving ticket information.  Each dict
        must have a C{'time'} key associated with a L{datetime} instance
        giving the time when the ticket was created.  The list must be
        sorted by the value of the C{'time'} key, ascending.

    @param interval: A L{timedelta} instance which will be used to determine
        how to space the yielded timestamps.
    """
    limit = tickets[0]['time']
    total = 0
    for data in tickets:
        if data['time'] >= limit:
            yield (limit, total)
            limit += interval
        total += 1
    yield (limit, total)


def main(cursor):
    tickets = sorted(tracstats.tickets(cursor).values(), key=lambda t: t['time'])
    return tracstats.TimeSeries(
        'Total Tickets',
        totalTicketsOverTime(tickets, timedelta(days=7)))


if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
