
import urlparse

from twisted.internet import reactor, task
from twisted.spread import pb
from twisted.python import log
from twisted.web import client

import config

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
        self.proto.ticket(ticket)

class TicketChange:
    ticketMessageFormat = (
        'new %(component)s %(kind)s #%(id)d by %(author)s: %(subject)s')

    def ticket(self, ticket):
        for (url, chan) in config.TICKET_RULES:
            if ticket.tracker == url:
                self.join(chan)
                self.msg(
                    chan,
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
            for (url, chan) in config.TICKET_RULES:
                if chan == channel:
                    d = self.reportReviewTickets(url, chan)
                    d.addErrback(
                        log.err,
                        "Failed to satisfy review ticket request from "
                        "%r to %r" % (url, chan))


    def connectionLost(self, reason):
        if self._ticketCall is not None:
            self._ticketCall.stop()


    def reportAllReviewTickets(self):
        """
        Call L{reportReviewTickets} with each element of L{config.TICKET_RULES}.
        """
        for (url, channel) in config.TICKET_RULES:
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
        if '@' in netloc:
            credentials, netloc = netloc.split('@', 1)
            location = urlparse.urlunparse((
                scheme, netloc, url, params, query, fragment))
            authorization = credentials.encode('base64').strip()
            headers['Authorization'] = 'Basic ' + authorization
        d = client.getPage(location, headers=headers)
        d.addCallback(self._parseReviewTicketQuery)
        return d


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
        self.msg(channel, "Tickets pending review: " + tickets)


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
