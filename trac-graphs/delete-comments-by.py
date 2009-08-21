
# Delete all trac ticket comments made by a particular user

import sys
from os.path import exists

from pysqlite2.dbapi2 import connect

def execute(cursor, statement, params=()):
    # print statement, params
    cursor.execute(statement, params)


def main(dbfile, commenter):
    if not exists(dbfile):
        raise SystemExit("No such database: %r" % (dbfile,))
    conn = connect(dbfile)
    curs = conn.cursor()
    execute(curs, 'SELECT ticket FROM ticket_change WHERE author = ?', (commenter,))
    tickets = list(curs)
    execute(curs, 'DELETE FROM ticket_change WHERE author = ?', (commenter,))
    for (id,) in tickets:
        execute(curs, 'SELECT MAX(time) FROM ticket_change WHERE ticket = ?', (id,))
        results = list(curs.fetchall())
        if results[0][0] is None:
            execute(curs, 'SELECT time FROM ticket WHERE id = ?', (id,))
            changetime = list(curs.fetchall())[0][0]
        else:
            changetime = results[0][0]
        execute(
            curs,
            'UPDATE ticket SET changetime = ? WHERE id = ?', (changetime, id))

    # Bonus round: delete their authentication token and session so they're signed out.
    execute(curs, 'DELETE FROM auth_cookie WHERE name = ?', (commenter,))
    execute(curs, 'DELETE FROM session WHERE sid = ?', (commenter,))

    conn.commit()
    conn.close()

main(sys.argv[1], sys.argv[2])
