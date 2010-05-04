
import sys

from datetime import timedelta

import tracstats


def commentersPerInterval(changes, interval):
    """
    Return an iterator of two-tuples of timestamps and the number of unique
    commenters since the previous timestamp.

    @param changes: A list of dicts giving ticket change information.  Each
        dict must have C{'time'} and C{'author'} fields.  The list must be
        sorted by the value of the C{'time'} key, ascending.

    @param interval: A L{timedelta} instance which will be used to determine
        how to space the yielded timestamps.
    """
    limit = changes[0]['time']
    commenters = set()
    for data in changes:
        if data['time'] >= limit:
            yield (limit, len(commenters))
            limit += interval
            commenters = set()
        commenters.add(data['author'])
    yield (limit, len(commenters))



def main(cursor):
    changes = tracstats.comments(cursor)
    return tracstats.TimeSeries(
        "Commenters Per Week",
        commentersPerInterval(changes, timedelta(days=7)))



if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
