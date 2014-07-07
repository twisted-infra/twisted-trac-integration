import sys
from os.path import expanduser

import psycopg2

from twisted.python.filepath import FilePath

DB = "dbname=trac"
PASSWD = FilePath(expanduser("~/config/htpasswd"))

def loadUsernames(conn, queries):
    curs = conn.cursor()
    curs.execute('BEGIN')
    try:
        results = set()
        for q in queries:
            curs.execute(q)
            results.update([user for (user,) in curs.fetchall()])
    finally:
        curs.execute('ROLLBACK')
        curs.close()
    return results



def filterCredentials(htpasswd, validUsers):
    output = []
    for account in htpasswd.getContent().split('\n'):
        try:
            name, password = account.split(':', 1)
        except ValueError:
            continue
        if name in validUsers or password == 'x':
            output.append(account)
    new = htpasswd.sibling('htpasswd.new')
    new.setContent('\n'.join(output) + '\n')
    return new



def main():
    conn = psycopg2.connect(DB)
    possibleActivities = [
        ('ticket', 'owner'),
        ('ticket', 'reporter'),
        ('ticket_change', 'author'),
        ('wiki', 'author'),
        ('attachment', 'author'),
        ('component', 'owner'),
        ('permission', 'username'),
        ('report', 'author'),
        ]
    users = loadUsernames(conn, [
            "SELECT DISTINCT %s FROM %s WHERE %s != ''" % (column, table, column)
            for (table, column)
            in possibleActivities])

    possibleActivitiesWithCommas = [
        ('component_default_cc', 'cc'),
        ('ticket', 'cc'),
        ]
    for (table, column) in possibleActivitiesWithCommas:
        someUsers = loadUsernames(
            conn, ["SELECT %s FROM %s WHERE %s != ''" % (column, table, column)])
        for usernames in someUsers:
            for name in usernames.split(','):
                users.add(name.strip())

    curs = conn.cursor()
    curs.execute(
        'SELECT sid FROM session WHERE authenticated = 1 AND sid NOT IN (%s)' % (', '.join(['%s'] * len(users)),),
        list(users))

    credentials = filterCredentials(PASSWD, users)

    sessionIdentifiers = list(curs.fetchall())
    curs.execute('BEGIN')
    curs.executemany("DELETE FROM session_attribute WHERE sid = %s", sessionIdentifiers)
    curs.executemany("DELETE FROM session WHERE sid = %s", sessionIdentifiers)
    curs.execute('COMMIT')

    print >>sys.stderr, "New password file at", credentials.path

    conn.close()

if __name__ == '__main__':
    main()
