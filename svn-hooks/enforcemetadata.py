#!/usr/bin/python

# This file is maintained in revision control as part of
# lp:twisted-trac-integration.  Do not edit the deployed copy.

import sys, subprocess

def getOutput(command):
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout = pipe.communicate()[0]
    return stdout

def main():
    root, transaction = sys.argv[1:]
    changed = getOutput([
            "/usr/bin/svnlook", "proplist", root, "--revprop",
            "--transaction", transaction])
    for line in changed.splitlines():
        if line.strip().startswith('bzr:'):
            raise SystemExit("Commit with bzr metadata rejected")

if __name__ == '__main__':
    main()
