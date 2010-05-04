
# Scan the database for redundant information about the last time a
# ticket was modified and update the ticket table itself to reflect
# this.

# This doesn't work right yet I suspect. -exarkun

import sys

from psycopg2 import connect

def execute(cursor, statement, params=()):
#    print statement, params
    cursor.execute(statement, params)


def main(dbargs):
    conn = connect(dbargs)
    curs = conn.cursor()
    execute(curs, 'SELECT id, time, changetime FROM ticket')
    tickets = list(curs)
    for (id, time, changetime) in tickets:
        execute(curs, 'SELECT MAX(time) FROM ticket_change WHERE ticket = %s', (id,))
        lastChange = list(curs.fetchall())[0][0]
        # execute(curs, 'SELECT MAX(time) FROM attachment WHERE id = %s', (id,))
        # lastAttachment = list(curs.fetchall())[0][0]
        if lastChange is None:
            lastChange = time
        # if lastAttachment is None:
        #     lastAttachment = time
        if lastChange != changetime:
            print id, time, lastChange
#            execute(
#                curs, 'UPDATE ticket SET changetime = %s WHERE id = %s',
#                (lastChangeTime, id))
    conn.commit()
    conn.close()

main(sys.argv[1])
