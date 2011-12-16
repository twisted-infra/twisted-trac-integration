import sys
from os.path import expanduser

import psycopg2

from twisted.python.filepath import FilePath

DB = "host=localhost user=trac-migration dbname=trac"
PASSWD = FilePath(expanduser("~/Run/trac/htpasswd"))

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
    users = loadUsernames(conn, [
            "SELECT DISTINCT owner FROM ticket WHERE owner != ''",
            "SELECT DISTINCT reporter FROM ticket WHERE reporter != ''",
            "SELECT DISTINCT author FROM ticket_change WHERE author != ''",
            "SELECT DISTINCT author FROM wiki WHERE author != ''",
            ])
    curs = conn.cursor()
    curs.execute(
        'SELECT sid FROM session WHERE authenticated = 1 AND sid NOT IN (%s)' % (', '.join(['%s'] * len(users)),),
        list(users))

    credentials = filterCredentials(PASSWD, users)

    for (sid,) in curs.fetchall():
        assert "'" not in sid
        print "DELETE FROM session_attribute WHERE sid = '%s'" % (sid,)
        print "DELETE FROM session WHERE sid = '%s'" % (sid,)

    print >>sys.stderr, "New password file at", credentials.path

    conn.close()

if __name__ == '__main__':
    main()
