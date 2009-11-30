#!/usr/bin/python

import re, sys, subprocess

def getOutput(command):
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout = pipe.communicate()[0]
    return stdout


def fileSetForTicket(ticket):
    options = set()
    options.add(ticket + '.feature')
    options.add(ticket + '.bugfix')
    options.add(ticket + '.removal')
    options.add(ticket + '.misc')
    return options


class Change(object):
    def __init__(self, path):
        self.path = path


    def isTrunk(self):
        return self.path[:1] == ['trunk']


    def isTopfile(self):
        return len(self.path) >= 2 and self.path[-2] == 'topfiles'


class Add(Change):
    pass


class Delete(Change):
    pass


class Modify(Change):
    pass


changeTypes = {
    'A': Add,
    'D': Delete,
    'M': Modify,
    }

def main():
    root, transaction = sys.argv[1:]
    changed = getOutput(['/usr/bin/svnlook', 'changed', root, '--transaction', transaction])
    addedTopfiles = set()
    deletedTopfiles = set()
    trunkChanged = False
    for line in changed.splitlines():
        type = line[0]
        name = line[4:].split('/')
        change = changeTypes.get(type, Change)(name)
        if change.isTrunk():
            trunkChanged = True
            if change.isTopfile():
                if isinstance(change, Add):
                    addedTopfiles.add(change)
                elif isinstance(change, Delete):
                    deletedTopfiles.add(change)

    if trunkChanged:
        log = getOutput(['/usr/bin/svnlook', 'log', root, '--transaction', transaction])

        fixes = re.findall('(?:Fixes|Closes): #(\d+)', log, re.I)
        reopens = re.findall('Reopens: #(\d+)', log, re.I)

        for ticket in fixes:
            required = fileSetForTicket(ticket)
            for change in addedTopfiles:
                print change.path[-1], required
                if change.path[-1] in required:
                    break
            else:
                raise SystemExit(
                    "Must add a .{feature,bugfix,removal,misc} file for resolved tickets")
        for ticket in reopens:
            required = fileSetForTicket(ticket)
            for change in deletedTopfiles:
                print change.path[-1], required
                if change.path[-1] in required:
                    break
            else:
                raise SystemExit(
                    "Must remove a .{feature,bugfix,removal,misc} file for re-opened tickets")



if __name__ == '__main__':
    main()
