
# Delete all trac ticket comments made by a particular user

import sys
from os.path import exists

from pysqlite2.dbapi2 import connect

def main(dbfile, commenter):
    if not exists(dbfile):
        raise SystemExit("No such database: %r" % (dbfile,))
    conn = connect(dbfile)
    curs = conn.cursor()
    curs.execute('SELECT ticket FROM ticket_change WHERE author = ?', (commenter,))
    tickets = list(curs)
    curs.execute('DELETE FROM ticket_change WHERE author = ?', (commenter,))
    for (id,) in tickets:
        curs.execute(
            'UPDATE ticket SET changetime = ('
                'SELECT MAX(time) FROM ticket_change WHERE ticket = ?) '
            'WHERE id = ?',
            (id, id))
    conn.commit()
    conn.close()

main(sys.argv[1], sys.argv[2])