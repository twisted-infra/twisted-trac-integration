#!/usr/bin/python

# This file is maintained in revision control as part of
# lp:twisted-trac-integration.  Do not edit the deployed copy.

import re, sys, subprocess

def getOutput(command):
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout = pipe.communicate()[0]
    return stdout

_fragmentTypes = ['feature', 'bugfix', 'doc', 'removal', 'misc']
_fragmentSuggestion = "<ticket>.{" + ",".join(_fragmentTypes) + "}"

def fileSetForTicket(ticket):
    options = set()
    for type in _fragmentTypes:
        options.add('%d.%s' % (int(ticket), type))
    return options


class Change(object):
    def __init__(self, path):
        self.path = path


    def isTrunk(self):
        return self.path[:1] == ['trunk']


    def isTopfile(self):
        return len(self.path) >= 2 and self.path[-2] == 'topfiles'


    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.path)



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


def iterchanges(changed):
    for line in changed.splitlines():
        type = line[0]
        name = line[4:].split('/')
        change = changeTypes.get(type, Change)(name)
        yield change


def main():
    root, transaction = sys.argv[1:]
    changed = getOutput(['/usr/bin/svnlook', 'changed', root, '--transaction', transaction])
    addedTopfiles = set()
    deletedTopfiles = set()
    trunkChanged = False
    for change in iterchanges(changed):
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
                if change.path[-1] in required:
                    break
            else:
                raise SystemExit(
                    "Must add a " + _fragmentSuggestion + " " +
                    "file for resolved tickets.  For further details, refer "
                    "to "
                    "http://twistedmatrix.com/trac/wiki/ReviewProcess#Newsfiles")
        for ticket in reopens:
            required = fileSetForTicket(ticket)
            for change in deletedTopfiles:
                if change.path[-1] in required:
                    break
            else:
                raise SystemExit(
                    "Must remove a " + _fragmentSuggestion + " " +
                    "file for re-opened tickets.  For further details, refer to "
                    "http://twistedmatrix.com/trac/wiki/ReviewProcess#Newsfiles")



if __name__ == '__main__':
    main()
