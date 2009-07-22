
from datetime import timedelta, datetime

from twisted.trial.unittest import TestCase

from total_tickets import totalTicketsOverTime
from open_tickets import openTicketsOverTime
from ticket_comments import commentsOverTime

class OverTimeTests(TestCase):
    """
    Tests for L{totalTicketsOverTime}, L{openTicketsOverTime}, and
    L{commentsOverTime}.
    """
    def test_totals(self):
        """
        L{totalTicketsOverTime} returns an iterator of two-tuples.  The
        first element of each two-tuple is a L{datetime.datetime}.  The
        second element is the total number of tickets which existed just
        before that timestamp.  The timestamps are separated by the interval
        supplied.
        """
        tickets = [
            {'time': datetime.fromtimestamp(10000), 'id': 3},
            {'time': datetime.fromtimestamp(20000), 'id': 5},
            {'time': datetime.fromtimestamp(30000), 'id': 7}]
        self.assertEqual(
            list(totalTicketsOverTime(tickets, timedelta(seconds=15000))),
            [(datetime.fromtimestamp(10000), 0),
             (datetime.fromtimestamp(25000), 2),
             (datetime.fromtimestamp(40000), 3)])


    def test_open(self):
        """
        L{openTicketsOverTime} is similar to L{totalTicketsOverTime} but
        instead returns information about how many tickets are open.
        """
        def closed(when, which):
            return {
                'time': when, 'ticket': which, 'field': 'status',
                'old': 'open', 'new': 'closed'}
        def opened(when, which):
            return {
                'time': when, 'ticket': which, 'field': 'status',
                'old': 'closed', 'new': 'open'}

        tickets = [
            # A ticket which is gets closed but is later re-opened
            {'time': datetime.fromtimestamp(10000), 'id': 3,
             'status': 'open',
             'changes': [closed(datetime.fromtimestamp(15000), 3),
                         opened(datetime.fromtimestamp(24000), 3)]},
            # A ticket which has been closed
            {'time': datetime.fromtimestamp(20000), 'id': 5,
             'status': 'closed',
             'changes': [closed(datetime.fromtimestamp(21000), 5)]},
            # A ticket which was created by roundup, is closed, but has no
            # record of ever being closed.
            {'time': datetime.fromtimestamp(30000), 'id': 7,
             'status': 'closed',
             'changes': [{'time': datetime.fromtimestamp(31000),
                          'field': 'comment', 'old': '', 'new': 'hi'}]}]

        changes = [
            change
            for ticket in tickets
            for change in ticket['changes']]

        self.assertEqual(
            list(openTicketsOverTime(
                    tickets, changes, timedelta(seconds=15000))),
            [(datetime.fromtimestamp(10000), 0),
             (datetime.fromtimestamp(25000), 1),
             (datetime.fromtimestamp(40000), 1)])


    def test_comments(self):
        """
        L{commentsOverTime} is similar to L{totalTicketsOverTime} but instead
        returns information about how many comments have been made.
        """
        def comment(when):
            return {'time': datetime.fromtimestamp(when), 'field': 'comment'}
        changes = [
            comment(10000), comment(20000), comment(30000), comment(40000)]
        self.assertEqual(
            list(commentsOverTime(changes, timedelta(seconds=15000))),
            [(datetime.fromtimestamp(10000), 0),
             (datetime.fromtimestamp(25000), 2),
             (datetime.fromtimestamp(40000), 3),
             (datetime.fromtimestamp(55000), 4)])

