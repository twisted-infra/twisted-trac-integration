#!/usr/bin/python

# This file is maintained in revision control as part of
# lp:twisted-trac-integration.  Do not edit the deployed copy.

import sys
sys.path.append('/home/exarkun/Projects/twisted-trac-integration/trunk/svn-hooks')

from enforcenews import getOutput, iterchanges

def main():
    root, transaction = sys.argv[1:]
    changed = getOutput(['/usr/bin/svnlook', 'changed', '--transaction', transaction, root])
    for change in iterchanges(changed):
        if change.isTrunk():
            content = getOutput([
                    '/usr/bin/svnlook', 'cat', '--transaction', transaction,
                    root, '/'.join(change.path)])
            for line in content.splitlines():
                if line != line.rstrip():
                    raise SystemExit(1)

if __name__ == '__main__':
    main()
