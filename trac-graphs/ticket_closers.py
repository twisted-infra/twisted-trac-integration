
import sys

from datetime import datetime, timedelta

from epsilon.extime import Time

import tracstats


def main(cursor, start=None, end=None):
    if start is not None:
        start = Time.fromISO8601TimeAndDate(start).asDatetime()
    else:
        start = datetime.now() - timedelta(days=365)
    if end is not None:
        end = Time.fromISO8601TimeAndDate(end).asDatetime()
    else:
        end = datetime.now()

    closers = {}

    for change in tracstats.changes(cursor, start, end):
        if change['old'] != 'closed' and change['new'] == 'closed':
            closers[change['author']] = closers.get(change['author'], 0) + 1

    return tracstats.Frequencies(
            "Ticket Closers",
            sorted(closers.items(), key=lambda (a, b): b))

if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
