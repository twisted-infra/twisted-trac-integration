#!/usr/bin/python

"""
Force the Twisted buildmaster to run a builds on all supported builders for
a particular branch.
"""

import os, sys, pwd, urllib

import twisted
from twisted.internet import reactor, defer, protocol
from twisted.python import log
from twisted.web import client, http, http_headers

VERSION = "0.1"

SUPPORTED_BUILDERS_URL = (
    "http://buildbot.twistedmatrix.com/supported-builders.txt")

USER_AGENT = (
    "force-builds.py/%(version)s (%(name)s; %(platform)s) Twisted/%(twisted)s "
    "Python/%(python)s" % dict(
        version=VERSION, name=os.name, platform=sys.platform,
        twisted=twisted.__version__, python=hex(sys.hexversion)))



class _CollectBody(protocol.Protocol):
    def __init__(self, result):
        self.result = result
        self.buffer = []


    def dataReceived(self, data):
        self.buffer.append(data)


    def connectionLost(self, reason):
        if reason.check(client.ResponseDone):
            self.result.callback("".join(self.buffer))
        else:
            self.result.errback(reason)



class Disconnect(protocol.Protocol):
    def makeConnection(self, transport):
        transport.stopProducing()



def readBody(response):
    if response.code in (http.OK, http.FOUND):
        result = defer.Deferred()
        protocol = _CollectBody(result)
        response.deliverBody(protocol)
        return result
    response.deliverBody(Disconnect())
    raise Exception("Unexpected response code: %d", response.code)



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
        log.err(err, "Build force failure")

    def forced(result, builder):
        print 'Forced', builder, '.'

    args = [
        ('username', pwd.getpwuid(os.getuid())[0]),
        ('revision', ''),
        ('submit', 'Force Build'),
        ('branch', branch),
        ('comments', comments)]

    agent = client.Agent(reactor, pool=client.HTTPConnectionPool(reactor))

    headers = http_headers.Headers({'user-agent': [USER_AGENT]})
    d = agent.request('GET', SUPPORTED_BUILDERS_URL, headers)
    d.addCallback(readBody)
    def gotBuilders(buildersText):
        builders = buildersText.splitlines()

        if tests is not None:
            builders.remove('documentation')
            args.extend([
                ('property1name', 'test-case-name'),
                ('property1value', tests)])

        for builder in builders:

            def f(builder, headers):
                print 'Forcing', builder, '...'
                url = "http://buildbot.twistedmatrix.com/builders/" + builder + "/force"
                url = url + '?' + '&'.join([k + '=' + urllib.quote(v) for (k, v) in args])
                d = agent.request("GET", url, headers)
                d.addCallback(readBody)
                d.addCallback(forced, builder)
                return d
            requests.append(lock.run(f, builder, headers).addErrback(ebList))

        return defer.gatherResults(requests)
    d.addCallback(gotBuilders)
    d.addErrback(log.err)
    d.addCallback(lambda ign: reactor.stop())
    reactor.run()
    print 'See http://buildbot.twistedmatrix.com/boxes-supported?branch=%s' % (branch,)


if __name__ == '__main__':
    main()
