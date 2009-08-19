
# Scan the database for redundant information about the last time a
# ticket was modified and update the ticket table itself to reflect
# this.

import sys
from os.path import exists

from pysqlite2.dbapi2 import connect

def execute(cursor, statement, params=()):
#    print statement, params
    cursor.execute(statement, params)


def main(dbfile):
    if not exists(dbfile):
        raise SystemExit("No such database: %r" % (dbfile,))
    conn = connect(dbfile)
    curs = conn.cursor()
    execute(curs, 'SELECT id, time, changetime FROM ticket')
    tickets = list(curs)
    for (id, time, changetime) in tickets:
        execute(curs, 'SELECT MAX(time) FROM ticket_change WHERE ticket = ?', (id,))
        lastChange = list(curs.fetchall())[0][0]
        # execute(curs, 'SELECT MAX(time) FROM attachment WHERE id = ?', (id,))
        # lastAttachment = list(curs.fetchall())[0][0]
        if lastChange is None:
            lastChange = time
        # if lastAttachment is None:
        #     lastAttachment = time
        if lastChange != changetime:
            print id, time, lastChangeTime
#            execute(
#                curs, 'UPDATE ticket SET changetime = ? WHERE id = ?',
#                (lastChangeTime, id))
    conn.commit()
    conn.close()

main(sys.argv[1])
