
import sys

from datetime import timedelta

import tracstats


def commentsOverTime(changes, interval):
    """
    Return an iterator of two-tuples of timestamps and the number of comments
    across all tickets immediately before that point in time.

    @param changes: A list of dicts giving ticket change information.  Each
        dict must have C{'time'} and C{'field'} fields.  If the C{'field'} key
        is associated with the value C{'comment'}, the change is counted as a
        comment.  The list must be sorted by the value of the C{'time'} key,
        ascending.

    @param interval: A L{timedelta} instance which will be used to determine
        how to space the yielded timestamps.
    """
    limit = changes[0]['time']
    total = 0
    for data in changes:
        if data['time'] >= limit:
            yield (limit, total)
            limit += interval
        if data['field'] == 'comment':
            total += 1
    yield (limit, total)



def main(cursor):
    changes = tracstats.comments(cursor)
    return tracstats.TimeSeries(
        "Ticket Comments",
        commentsOverTime(changes, timedelta(days=7)))



if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
