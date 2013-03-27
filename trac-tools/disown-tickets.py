from time import time
from pprint import pprint
from random import choice

import psycopg2

def main():
    conn = psycopg2.connect("host=localhost user=trac-migration dbname=trac")
    curs = conn.cursor()
    curs.execute('BEGIN')
    curs.execute('SELECT id, owner FROM ticket')

    owners = {}

    now = int(time())

    for id, owner in curs.fetchall():
        owners.setdefault(owner, []).append(id)

    for (owner, tickets) in owners.iteritems():
        while len(tickets) > 10:
            ticket = choice(tickets)
            tickets.remove(ticket)
            curs.execute(
                'INSERT INTO ticket_change '
                '(ticket, time, author, field, oldvalue, newvalue) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (ticket, now, '<automation>', 'owner', owner, ''))
            curs.execute(
                'UPDATE ticket '
                'SET owner = %s, time = %s '
                'WHERE id = %s',
                ("", now, ticket))
    curs.execute('COMMIT')


if __name__ == '__main__':
    main()
