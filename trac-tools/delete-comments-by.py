
# Delete all trac ticket comments made by a particular user

import sys

from psycopg2 import connect

def execute(cursor, statement, params=()):
    # print statement, params
    cursor.execute(statement, params)


def main(dbargs, commenter):
    conn = connect(dbargs)
    curs = conn.cursor()
    execute(curs, 'SELECT ticket FROM ticket_change WHERE author = %s', (commenter,))
    tickets = set(curs)
    execute(curs, "SELECT id FROM attachment WHERE type = 'ticket' AND author = %s", (commenter,))
    tickets.update(set(curs))
    execute(curs, 'DELETE FROM ticket_change WHERE author = %s', (commenter,))
    execute(curs, 'DELETE FROM attachment WHERE author = %s', (commenter,))
    for (id,) in tickets:
        execute(curs, 'SELECT MAX(time) FROM ticket_change WHERE ticket = %s', (id,))
        results = list(curs.fetchall())
        if results[0][0] is None:
            execute(curs, 'SELECT time FROM ticket WHERE id = %s', (id,))
            changetime = list(curs.fetchall())[0][0]
        else:
            changetime = results[0][0]
        execute(
            curs,
            'UPDATE ticket SET changetime = %s WHERE id = %s', (changetime, id))

    # Bonus round: delete their authentication token and session so they're signed out.
    execute(curs, 'DELETE FROM auth_cookie WHERE name = %s', (commenter,))
    execute(curs, 'DELETE FROM session WHERE sid = %s', (commenter,))

    conn.commit()
    conn.close()

main(sys.argv[1], sys.argv[2])
