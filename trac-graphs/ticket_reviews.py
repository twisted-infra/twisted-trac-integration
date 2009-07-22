
import sys, time

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

    reviewers = {}

    statement = (
        "select time, ticket, field, oldvalue, newvalue, author "
        "from ticket_change "
        "where field = 'keywords' and (time > %(start)d and time < %(end)d) "
        "order by time asc") % {'start': time.mktime(start.utctimetuple()),
                                'end': time.mktime(end.utctimetuple())}
    cursor.execute(statement)
    for (when, ticket, field, old, new, author) in cursor.fetchall():
        if 'review' in old and 'review' not in new:
            reviewers[author] = reviewers.get(author, 0) + 1

    return tracstats.Frequencies(
            "Ticket Reviewers",
            sorted(reviewers.items(), key=lambda (a, b): b))

if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
