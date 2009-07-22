
import sys, time
from datetime import datetime, timedelta

from epsilon.extime import Time

import tracstats

def main(cursor, forAuthor, start=None, end=None):
    if start is not None:
        start = Time.fromISO8601TimeAndDate(start).asDatetime()
    else:
        start = datetime.now() - timedelta(days=365)
    if end is not None:
        end = Time.fromISO8601TimeAndDate(end).asDatetime()
    else:
        end = datetime.now()

    statement = (
        "select time, ticket, field, oldvalue, newvalue, author "
        "from ticket_change "
        "where field = 'keywords' and (time > %(start)d and time < %(end)d) "
        "order by time asc") % {'start': time.mktime(start.utctimetuple()),
                                'end': time.mktime(end.utctimetuple())}
    cursor.execute(statement)
    for (when, ticket, field, old, new, author) in cursor.fetchall():

        # Check to see if it is by the right author
        if author != forAuthor:
            continue

        if 'review' in old and 'review' not in new:
            print 'Reviewed', ticket, 'on', datetime.fromtimestamp(when)

    raise SystemExit()

if __name__ == '__main__':
    tracstats.driver(main, sys.argv[1:])
