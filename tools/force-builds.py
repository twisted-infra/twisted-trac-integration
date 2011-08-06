#!/usr/bin/python

"""
Force the Twisted buildmaster to run a builds on all supported builders for
a particular branch.
"""

import os, sys, pwd, urllib

from twisted.internet import reactor, defer
from twisted.python import log
from twisted.web import client
from twisted.web.error import PageRedirect

BUILDERS = [
    'documentation',
    'debian64-py2.4-select',
    'debian-easy-py2.5-epoll',
    'hardy32-py2.5-glib2',
    'lucid64-py2.6-select',
    'lucid32-py2.6-select',
    'hardy32-py2.5-select',
    'lucid32-py2.7maint',
    # Skip py-select-gc
    'py-without-modules',
    'winxp32-py2.5',
    'winxp32-py2.6',
    'winxp32-py2.7',
    'windows7-64-py2.7',
    # Skip the MSI builders
    'fedora11-64bit-py2.7',
    'fedora32-py2.5-reactors',
    'lucid64-py2.6-poll',
    'lucid64-py2.6-epoll',
    'osx10.6-py2.6-select',
]

def main():
    if len(sys.argv) == 3:
        branch, comments = sys.argv[1:]
        tests = None
    elif len(sys.argv) == 4:
        branch, comments, tests = sys.argv[1:]
    else:
        raise SystemExit("Usage: %s <branch> <comments> [test-case-name]" % (sys.argv[0],))

    log.startLogging(sys.stdout)
    if not branch.startswith('/branches/'):
        branch = '/branches/' + branch

    lock = defer.DeferredLock()
    requests = []
    def ebList(err):
        if err.check(PageRedirect) is not None:
            return None
        log.err(err, "Build force failure")

    args = [
        ('username', pwd.getpwuid(os.getuid())[0]),
        ('revision', ''),
        ('submit', 'Force Build'),
        ('branch', branch),
        ('comments', comments)]
    if tests is not None:
        BUILDERS.remove('documentation')
        args.extend([
            ('property1name', 'test-case-name'),
            ('property1value', tests)])

    for builder in BUILDERS:
        print 'Forcing', builder, '...'
        url = "http://buildbot.twistedmatrix.com/builders/" + builder + "/force"
        
        url = url + '?' + '&'.join([k + '=' + urllib.quote(v) for (k, v) in args])
        requests.append(
            lock.run(client.getPage, url, followRedirect=False).addErrback(ebList))

    d = defer.gatherResults(requests)
    d.addErrback(log.err)
    d.addCallback(lambda ign: reactor.stop())
    reactor.run()
    print 'See http://buildbot.twistedmatrix.com/boxes-supported?branch=%s' % (branch,)


if __name__ == '__main__':
    main()
