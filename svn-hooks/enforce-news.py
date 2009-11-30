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


def main():
    root, transaction = sys.argv[1:]
    changed = getOutput(['/usr/bin/svnlook', 'changed', root, '--transaction', transaction])
    addedTopfiles = set()
    deletedTopfiles = set()
    for line in stdout.splitlines():
        if line[0] in ('A', 'D'):
            filename = line[4:]
            components = filename.split('/')
            if len(components) >= 2 and components[-2] == 'topfiles':
                {'A': addedTopfiles, 'D': deletedTopfiles}.get(line[0]).add(components[-1])
    log = getOutput(['/usr/bin/svnlook', 'log', root, '--transaction', transaction])

    fixes = re.findall('(?:Fixes|Closes): #(\d+)', log, re.I)
    reopens = re.findall('Reopens: #(\d+)', log, re.I)

    for ticket in fixes:
        if not (fileSetForTicket(ticket) & addedTopfiles):
            raise SystemExit("Must add a .{feature,bugfix,removal,misc} file for resolved tickets")
    for ticket in reopens:
        if not (fileSetForTicket(ticket) & deletedTopFiles):
            raise SystemExit("Must remove a .{feature,bugfix,removal,misc} file for re-opened tickets")



if __name__ == '__main__':
    main()
