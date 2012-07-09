
import time, urlparse

from twisted.internet import reactor, task
from twisted.spread import pb
from twisted.python import log
from twisted.web import error, http

import config, _http


class Ticket(pb.Copyable, pb.RemoteCopy):
    def __init__(self, tracker, id, author, kind, component, subject):
        self.tracker = tracker
        self.id = id
        self.author = author
        self.kind = kind
        self.component = component
        self.subject = subject

    def __repr__(self):
        return 'Ticket(%r, %d, %r, %r, %r, %r)' % (
            self.tracker, self.id, self.author, self.kind,
            self.component, self.subject)
pb.setUnjellyableForClass(Ticket, Ticket)



class TicketChangeListener:
    """
    Mixin for a PB Referenceable which accepts ticket change notifications.
    """
    def remote_ticket(self, ticket):
        log.msg(str(ticket))
        self.proto.ticket(ticket)



class TicketChange:
    ticketMessageFormat = (
        'new %(component)s %(kind)s #%(id)d by %(author)s: %(subject)s')

    def ticket(self, ticket):
        for (url, channels) in config.TICKET_RULES:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
            if '@' in netloc:
                netloc = netloc.split('@', 1)[1]
            url = urlparse.urlunparse((scheme, netloc, path, params, query, fragment))
            if ticket.tracker == url:
                for channel in channels:
                    self.join(channel)
                    self.msg(
                        channel,
                        self.ticketMessageFormat % vars(ticket),
                        config.LINE_LENGTH)



class TicketReview:
    """
    Automated review ticket reporting.
    """

    _ticketCall = None

    def signedOn(self):
        self._ticketCall = task.LoopingCall(self.reportAllReviewTickets)
        self._ticketCall.start(60 * 60 * 5)


    def privmsg(self, user, channel, message):
        if 'review branches' in message:
            for (url, channels) in config.TICKET_RULES:
                for existing_channel in channels:
                    if existing_channel == channel:
                        d = self.reportReviewTickets(url, channel)
                        d.addErrback(
                            log.err,
                            "Failed to satisfy review ticket request from "
                            "%r to %r" % (url, channel))


    def connectionLost(self, reason):
        if self._ticketCall is not None:
            self._ticketCall.stop()


    def reportAllReviewTickets(self):
        """
        Call L{reportReviewTickets} with each element of L{config.TICKET_RULES}.
        """
        for (url, channels) in config.TICKET_RULES:
            for channel in channels:
                d = self.reportReviewTickets(url, channel)
                d.addErrback(
                    log.err,
                    "Failed to report review tickets from %r to %r" % (
                        url, channel))


    def reportReviewTickets(self, trackerRoot, channel):
        """
        Retrieve the list of tickets currently up for review from the
        tracker at the given location and report them to the given channel.

        @param trackerRoot: The base URL of the trac instance from which to
        retrieve ticket information.  C{"http://example.com/trac/"}, for
        example.

        @param channel: The channel to which to send the results.

        @return: A Deferred which fires when the report has been completed.
        """
        d = self._getReviewTickets(trackerRoot)
        d.addCallback(self._reportReviewTickets, channel)
        return d


    def _getReviewTickets(self, trackerRoot):
        """
        Retrieve the list of tickets currently up for review from the
        tracker at the given location.

        @return: A Deferred which fires with a C{list} of C{int}s.  Each
        element is the number of a ticket up for review.
        """
        location = trackerRoot + (
            "query?"
            "status=new&"
            "status=assigned&"
            "status=reopened&"
            "format=tab&"
            "keywords=~review"
            "&order=priority")
        headers = {}
        scheme, netloc, url, params, query, fragment = urlparse.urlparse(location)
        credentials = None
        if '@' in netloc:
            credentials, netloc = netloc.split('@', 1)
            location = urlparse.urlunparse((
                scheme, netloc, url, params, query, fragment))
        factory = _http.getPage(location, headers=headers)
        if credentials is not None:
            factory.deferred.addErrback(self._handleUnauthorized, factory, location, credentials)
        factory.deferred.addCallback(self._parseReviewTicketQuery)
        return factory.deferred


    def _handleUnauthorized(self, err, factory, location, credentials):
        """
        Check failures to see if they are due to a 401 response and attempt to
        authenticate if they are.
        """
        err.trap(error.Error)
        if int(err.value.status) != http.UNAUTHORIZED:
            return err

        challenge = factory.response_headers.get('www-authenticate', [None])[0]
        if challenge is None:
            return err

        challenge = dict(
            _http.parseWWWAuthenticate(_http.tokenize([challenge])))

        challenge = challenge.get('digest')
        if challenge is None:
            return err

        scheme, netloc, url, params, query, fragment = urlparse.urlparse(location)
        uri = urlparse.urlunparse((None, None, url, params, query, None))

        response = challenge.get('response')
        nonce = challenge.get('nonce')
        cnonce = str(time.time())
        nc = '00000001'
        realm = challenge.get('realm')
        algo = challenge.get('algorithm', 'md5').lower()
        qop = challenge.get('qop', 'auth')

        username, password = credentials.split(':')

        response = _http.calcResponse(
            _http.calcHA1(algo, username, realm, password, nonce, cnonce),
            _http.calcHA2(algo, 'GET', uri, qop, None),
            algo, nonce, nc, cnonce, qop)


        challenge['username'] = username
        challenge['uri'] = uri
        challenge['response'] = response
        challenge['cnonce'] = cnonce
        challenge['nc'] = nc

        headers = {
            'authorization': 'Digest ' + ', '.join([
                    '%s="%s"' % x for x in challenge.iteritems()])}
        factory = _http.getPage(location, headers=headers)
        return factory.deferred


    def _parseReviewTicketQuery(self, result):
        """
        Split up a multi-line tab-delimited set of ticket information and
        return two-tuples of ticket numbers as integers and owners as
        strings.

        The first line of input is expected to be column definitions and is
        skipped.
        """
        for line in result.splitlines()[1:]:
            parts = line.split('\t')
            yield int(parts[0]), parts[4]


    def _reportReviewTickets(self, reviewTicketInfo, channel):
        """
        Format the given list of ticket numbers and send it to the given channel.
        """
        tickets = self._formatTicketNumbers(reviewTicketInfo)
        self.join(channel)
        if tickets:
            message = "Tickets pending review: " + tickets
        else:
            message = "No tickets pending review!"
        self.msg(channel, message)


    def _formatTicketNumbers(self, reviewTicketInfo):
        tickets = []
        for (id, owner) in reviewTicketInfo:
            if owner:
                tickets.append('#%d (%s)' % (id, owner))
            else:
                tickets.append('#%d' % (id,))
        return ', '.join(tickets)



def _sendTicket(ticket):
    cf = pb.PBClientFactory()
    reactor.connectTCP(config.BOT_HOST, config.BOT_PORT, cf)

    def cbRoot(rootObj):
        return rootObj.callRemote('ticket', ticket)

    rootD = cf.getRootObject()
    rootD.addCallback(cbRoot)
    rootD.addErrback(log.err)
    rootD.addCallback(lambda ign: reactor.stop())

def main(tracker, id, author, kind, component, subject):
    reactor.callWhenRunning(_sendTicket, Ticket(tracker, int(id), author, kind, component, subject))
    reactor.run()
