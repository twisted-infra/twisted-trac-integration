
import tempfile
import sys, time, datetime, random, StringIO
import email.Message, email.Generator, email.Utils

import psycopg2.extensions

import gdchart

import tracstats


def log(*args):
    sys.stderr.write(' '.join(map(str, args)))
    sys.stderr.write('\n')
    sys.stderr.flush()


def period(today=None):
    """
    Return a two-tuple of integers representing posix timestamps for midnight
    on the sunday before the most recent sunday and midnight the most recent
    sunday.
    """
    if today is None:
        today = datetime.date.today()
    today = datetime.datetime.fromordinal(today.toordinal())
    offset = datetime.timedelta(days=(today.weekday() + 1) % 7)
    end = today - offset
    start = end - datetime.timedelta(days=7)
    return start, end


def periods(howMany, today=None):
    assert howMany >= 2
    times = list(period(today))
    for i in xrange(howMany - len(times)):
        times.insert(0, period(times[0])[0])
    return times


def _describeTicketAge(ticket, kind):
    if ticket is not None:
        return '%s open ticket - [#%d] %s (since %s).' % (
            kind, ticket['id'], ticket['summary'], ticket['time'])
    else:
        return 'There is no oldest ticket.'



def describeOldestTicket(tickets):
    """
    Return a string describing the oldest open ticket.
    """
    ticket = None
    for id, tkt in tickets.iteritems():
        if tkt[u'status'] != u'closed':
            if ticket is None or tkt[u'time'] < ticket[u'time']:
                ticket = tkt
    return _describeTicketAge(ticket, 'Oldest')



def describeYoungestTicket(tickets):
    """
    Return a string describing the newest open ticket.
    """
    ticket = None
    for id, tkt in tickets.iteritems():
        if tkt[u'status'] != u'closed':
            if ticket is None or tkt[u'time'] > ticket[u'time']:
                ticket = tkt
    return _describeTicketAge(ticket, 'Newest')



def ticketAge(ticket, now):
    """
    Return a datetime.timedelta giving the amount of time since the given
    ticket's creation.
    """
    return now - ticket[u'time']



def describeAverageTicketAge(tickets):
    """
    Return a string describing the average age of open tickets.
    """
    now = datetime.datetime.now()
    openTickets = [
        tkt for tkt in tickets.values() if tkt[u'status'] != u'closed']

    times = []
    for tkt in openTickets:
        times.append(ticketAge(tkt, now))

    return (
        'Mean open ticket age: %s.\n'
        'Median: %s.\n'
        'Standard deviation: %s.\n'
        'Interquartile range: %s.' % timeStatistics(times))



def timeTicketOpen(ticket):
    """
    Return a timedelta giving the amount of time between the creation and the
    final resolution of the given ticket.
    """
    closed = None
    opened = ticket[u'time']
    for change in ticket[u'changes']:
        if change[u'field'] == u'status' and change[u'new'] == u'closed':
            closed = change[u'time']
    if closed is None:
        log('Sucky ticket:', ticket[u'id'])
        if ticket[u'changes']:
            closed = ticket[u'changes'][-1][u'time']
        else:
            closed = opened
    return closed - opened


def timeStatistics(times):
    mean = sum(times, datetime.timedelta(seconds=0)) / len(times)
    variance = 0
    for age in times:
        if age > mean:
            residual = age - mean
        else:
            residual = mean - age
        residualInt = residual.days * (60 * 60 * 24) + residual.seconds
        variance += residualInt ** 2
    variance /= len(times)
    stddev = datetime.timedelta(seconds=variance ** 0.5)

    times.sort()
    firstQuartile = times[len(times) / 4]
    thirdQuartile = times[len(times) / 4 * 3]
    iqr = thirdQuartile - firstQuartile
    return mean, times[len(times) / 2], stddev, iqr


def describeAverageTicketLifetime(tickets):
    """
    Return a string describing the average time between the opening and closing
    of a ticket.
    """
    now = datetime.datetime.now()
    closedTickets = [
        tkt for tkt in tickets.values() if tkt[u'status'] == u'closed']

    times = []
    for tkt in closedTickets:
        times.append(timeTicketOpen(tkt))

    return (
        "Mean time between ticket creation and ticket resolution: %s.\n"
        "Median: %s.\n"
        "Standard deviation is %s.\n"
        'The interquartile range is %s.' % timeStatistics(times))


def describeAverageReviewPeriod(tickets):
    """
    Return a string describing the average time tickets have spent in review.
    """
    now = datetime.datetime.now()
    times = []
    reviews = []
    for tkt in tickets.values():
        changed = False
        numReviews = 0
        reviewTime = datetime.timedelta(seconds=0)
        lastReviewStart = tkt[u'time']
        for ch in tkt[u'changes']:
            if ch[u'field'] == u'keywords':
                if u'review' in ch[u'old'] and u'review' not in ch[u'new']:
                    # It got reviewed
                    reviewTime += ch[u'time'] - lastReviewStart
                    lastReviewStart = None
                    numReviews += 1
                if u'review' in ch[u'new'] and u'review' not in ch[u'old']:
                    # It is up for review now
                    lastReviewStart = ch[u'time']
                    changed = True
        if changed:
            if lastReviewStart is not None:
                reviewTime += now - lastReviewStart
            times.append(reviewTime)
        if numReviews:
            reviews.append(numReviews)

    format = (
        "Mean time spent in review: %s.\n"
        "Median: %s.\n"
        "Standard deviation: %s.\n"
        "Interquartile range: %s.\n"
        "\n"
        "Mean number of times a ticket is reviewed: %s.\n"
        "Median: %s\n"
        "Standard deviation: %s.\n"
        "Interquartile range: %s.\n")

    reviews.sort()
    mean = sum(reviews) / float(len(reviews))
    variance = 0
    for count in reviews:
        variance += (count - mean) ** 2
    stddev = (variance / len(reviews)) ** 0.5
    return format % (timeStatistics(times) + (
        mean,
        reviews[len(reviews) / 2],
        stddev,
        reviews[len(reviews) / 4 * 3] - reviews[len(reviews) / 4]))



def describeOverallContributors(tickets):
    """
    Return a string containing descriptive statistics about the number of
    people who have made ticket changes.
    """
    now = datetime.datetime.now()

    def add(sets, value, time):
        """
        Add the given value to each appropriate set from the ascendingly sorted
        list of two-tuples of ages and sets.
        """
        for age, set in sets[::-1]:
            if now - time < age:
                set.add(value)

    # Corresponding not too closely with 1 month, 6 months, 12 months.
    periods = [
        datetime.timedelta(days=7 * 4 * 1),
        datetime.timedelta(days=7 * 4 * 6),
        datetime.timedelta(days=7 * 4 * 12)]

    created = [(p, set()) for p in periods]
    reviewed = [(p, set()) for p in periods]
    resolved = [(p, set()) for p in periods]

    for tkt in tickets.values():
        add(created, tkt[u'reporter'], tkt[u'time'])
        for ch in tkt[u'changes']:
            if ch[u'field'] == u'keywords':
                if u'review' in ch[u'old'] and u'review' not in ch[u'new']:
                    # It was reviewed, this person is a reviewer.
                    add(reviewed, ch[u'author'], ch[u'time'])
            if ch[u'field'] == u'resolution':
                if ch[u'old'] != u'fixed' and ch[u'new'] == u'fixed':
                    # It was resolved, this person is a resolver.
                    add(resolved, ch[u'author'], ch[u'time'])

    return ''.join([
        "In the last %d weeks,\n"
        "    %d unique ticket reporters\n"
        "    %d unique ticket reviewers\n"
        "    %d unique ticket resolvers\n" % (t.days / 7, len(cre), len(rev), len(res))
        for ((t, cre), (t, rev), (t, res))
        in zip(created, reviewed, resolved)])


def changeClosesTicket(change):
    if change[u'field'] == u'status':
        if change[u'old'] != u'closed' and change[u'new'] == u'closed':
            return True
    return False


def changeOpensTicket(change):
    if change[u'field'] == u'status':
        if change[u'old'] == u'closed' and change[u'new'] != u'closed':
            return True
    return False


def historicTicketCounts(dates, tickets):
    """
    Return an iterable of tuples of integers giving the number of total and
    open tickets at each date in C{dates}.
    """
    for d in dates:
        openCount = 0
        totalCount = 0
        for t in tickets.itervalues():
            # Skip tickets that did not exist at the given time
            if t[u'time'] >= d:
                continue

            # Start at the current time
            openState = t[u'status'] != u'closed'

            # Visit each change in reverse chronological order to play back the
            # state.
            for c in t[u'changes'][::-1]:

                # If the change is older than the given time, there is no
                # processing left to do for this ticket.
                if c[u'time'] < d:
                    break

                # Track changes which closed the ticket by marking it as open
                # (we are going backwards)
                if changeClosesTicket(c):
                    if not openState:
                        openState = True
                    else:
                        log('Bogus change', c, 'for', t[u'id'])

                # Track changes which opened the ticket by marking it as closed
                # (we are going backwards)
                elif changeOpensTicket(c):
                    if openState:
                        openState = False
                    else:
                        log('Bogus change', c, 'for', t[u'id'])

            # If it's open after applying all the changes, count it.
            if openState:
                openCount += 1
            totalCount += 1

        yield totalCount, openCount


def historicTicketCountsGraph(tickets, howMany=52 * 5):
    """
    Return png data for an image of a bar graph giving open tickets by week for
    the given number of historic weeks.
    """
    dates = periods(howMany)
    totalCounts = []
    openCounts = []
    for total, open in historicTicketCounts(dates, tickets):
        totalCounts.append(total)
        openCounts.append(open)
    line = gdchart.Line()
    line.setData(totalCounts, openCounts)
    line.setOption('title', 'Ticket Counts by Date')
    line.setOption('xtitle', 'Date')
    line.setOption('ytitle', '# Tickets')

    line.setOption('width', 640)
    line.setOption('height', 480)
    line.setOption('ylabel_density', 40)
    line.setOption('xlabel_spacing', 12)
    line.setOption('bg_color', 0xffffff)
    line.setOption('set_color', [0x00ff00, 0xff0000])

    labels = []
    for d in dates:
        labels.append(d.strftime('%b %Y'))
    line.setLabels(labels)


    fObj = tempfile.TemporaryFile()
    line.draw(fObj)
    fObj.seek(0, 0)
    bytes = fObj.read()
    fObj.close()
    return bytes


def formatCount(diff):
    if diff >= 0:
        return u'+%d' % (diff,)
    return u'%d' % (diff,)


def formatDifference(minuend, subtrahend):
    return formatCount(minuend - subtrahend)


def moreOf(d, k):
    d[k] = d.get(k, 0) + 1


def lessOf(d, k):
    d[k] = d.get(k, 0) - 1


def summarize(start, end, tickets, changes):
    t = change = tkt = None

    typeChanges = {}
    priorityChanges = {}
    componentChanges = {}

    # Not strictly correct with respect to the interval.
    totalOpenBugCount = len([t for t in tickets.itervalues() if t[u'status'] != u'closed'])

    bugsClosed = []
    bugsOpened = []
    for t in tickets.itervalues():
        if start <= t[u'time'] < end:
            bugsOpened.append(t)
            moreOf(typeChanges, t[u'type'])
            moreOf(priorityChanges, t[u'priority'])
            moreOf(componentChanges, t[u'component'])

    for change in changes:
        tkt = tickets[change[u'ticket']]
        if change[u'field'] == u'status':
            if change[u'old'] != u'closed' and change[u'new'] == u'closed':
                accumulator = bugsClosed
                modifier = lessOf
                tkt[u'closer'] = change[u'author']
            elif change[u'old'] == u'closed' and change[u'new'] != u'closed':
                accumulator = bugsOpened
                modifier = moreOf
            else:
                continue
            modifier(typeChanges, tkt[u'type'])
            modifier(priorityChanges, tkt[u'priority'])
            modifier(componentChanges, tkt[u'component'])
            accumulator.append(tkt)

    oldestTicket = describeOldestTicket(tickets)
    youngestTicket = describeYoungestTicket(tickets)
    averageTicketAge = describeAverageTicketAge(tickets)
    averageTicketLifetime = describeAverageTicketLifetime(tickets)
    averageReviewPeriod = describeAverageReviewPeriod(tickets)
    overallContributors = describeOverallContributors(tickets)

    historicTicketsGraph = historicTicketCountsGraph(tickets)

    del t, tkt, change
    return locals()


TEXT_FORMAT = u"""\
Bug summary
______________________
Summary for %(start)s through %(end)s
Bugs opened: %(bugsOpened)d    Bugs closed: %(bugsClosed)d  Total open bugs: %(totalOpenBugs)d (%(openBugChange)s)

%(countChanges)s

New / Reopened Bugs
______________________
%(openedTickets)s

Closed Bugs
______________________
%(closedTickets)s

Ticket Lifetime Stats
______________________
%(oldestTicket)s
%(youngestTicket)s

%(averageTicketAge)s

%(averageTicketLifetime)s

%(averageReviewPeriod)s

Contributor Stats
______________________
%(overallContributors)s
"""

HTML_FORMAT = u"""\
<html>
<body>
<pre>
Bug summary
______________________
Summary for %(start)s through %(end)s
Bugs opened: %(bugsOpened)d    Bugs closed: %(bugsClosed)d  Total open bugs: %(totalOpenBugs)d (%(openBugChange)s)

%(countChanges)s

<div>
<font color='green'>Total Tickets</font>
<font color='red'>Open Tickets</font>
<img src='data:image/png;base64,%(historicTicketsGraph)s' />
</div>

New / Reopened Bugs
______________________
%(openedTickets)s

Closed Bugs
______________________
%(closedTickets)s

Ticket Lifetime Stats
______________________
%(oldestTicket)s
%(youngestTicket)s

%(averageTicketAge)s

%(averageTicketLifetime)s

%(averageReviewPeriod)s

Contributor Stats
______________________
%(overallContributors)s
</pre>
</body>
</html>
"""

link = u"http://twistedmatrix.com/trac/ticket/%(id)d"

def formatChange(kind, info):
    if not info:
        return ''
    width = max([len(item[0]) for item in info]) + 3
    summary = [u'== %s changes ' % (kind,)]
    summary.extend([
        u'%s: %*s' % (k, width - len(k), formatCount(v)) for (k, v) in info])
    return summary


def juxtapose(*groups):
    summary = []
    widths = [max(map(len, g)) for g in groups]
    for lines in map(None, *groups):
        summary.append(''.join([u'%-*s' % (w + 3, (l and u'|' + l.title() or u'')) for (w, l) in zip(widths, lines)]))
    return u'\n'.join(summary) + u'\n'


PRIORITY_ORDER = [
    u'highest',
    u'high',
    u'normal',
    u'low',
    u'lowest']

OPEN_SUMMARY = (
    u'[#%(strid)s] %(summary)s (opened by %(reporter)s)%(sinceClosed)s\n'
    u'    %(type)-15s %(component)-10s ' + link + u'\n'
    )

CLOSE_SUMMARY = (
    u'[#%(strid)s] %(summary)s (opened by %(reporter)s, closed by %(closer)s, %(resolution)s)\n'
    u'    %(type)-15s %(component)-10s ' + link + u'\n'
    )
def formatTickets(tickets, fmt):
    summary = []
    if tickets:
        ticketWidth = max(len(str(t[u'id'])) for t in tickets)
    else:
        ticketWidget = 6
    lastPriority = None
    seen = {}
    for tkt in sorted(tickets, key=lambda t: PRIORITY_ORDER.index(t[u'priority'])):
        if tkt[u'id'] in seen:
            continue
        seen[tkt[u'id']] = None
        if lastPriority != tkt[u'priority']:
            summary.append(u' ' * 20 + u'=' * 5 + u' ' + tkt[u'priority'].title() + u' ' + u'=' * 5)
            lastPriority = tkt[u'priority']
        tkt = tkt.copy()
        tkt[u'strid'] = u'%-*d' % (ticketWidth, tkt[u'id'])
        if tkt[u'status'] == u'closed':
            tkt[u'sinceClosed'] = u' (CLOSED, ' + tkt[u'resolution'] + ')'
        else:
            tkt[u'sinceClosed'] = u''
        summary.append(fmt % tkt)
    return u'\n'.join(summary) + u'\n'


def format(fmt, summary):
    return fmt % tracstats.udict(
        start=summary['start'].date().isoformat(),
        end=summary['end'].date().isoformat(),
        bugsOpened=len(summary['bugsOpened']),
        bugsClosed=len(summary['bugsClosed']),
        totalOpenBugs=summary['totalOpenBugCount'],
        openBugChange=formatDifference(len(summary['bugsOpened']), len(summary['bugsClosed'])),
        countChanges=juxtapose(formatChange(u'Type', sorted(summary['typeChanges'].items())),
                               formatChange(u'Priority', sorted(summary['priorityChanges'].items(), key=lambda t: PRIORITY_ORDER.index(t[0]))),
                               formatChange(u'Component', sorted(summary['componentChanges'].items()))),
        openedTickets=formatTickets(summary['bugsOpened'], OPEN_SUMMARY),
        closedTickets=formatTickets(summary['bugsClosed'], CLOSE_SUMMARY),
        oldestTicket=summary['oldestTicket'],
        youngestTicket=summary['youngestTicket'],
        averageTicketAge=summary['averageTicketAge'],
        averageTicketLifetime=summary['averageTicketLifetime'],
        averageReviewPeriod=summary['averageReviewPeriod'],
        overallContributors=summary['overallContributors'],
        historicTicketsGraph=summary['historicTicketsGraph'].encode('base64'),
        )


def sendmail(from_, to, fileObj):
    from twisted.internet import reactor
    from twisted.mail import smtp
    from twisted.python import log

    log.startLogging(sys.stdout)

    d = smtp.sendmail('twistedmatrix.com', from_, [to], fileObj)
    d.addErrback(log.err)
    d.addCallback(lambda ign: reactor.stop())
    reactor.run()


def report(from_, to, contentType, body):
    msg = email.Message.Message()
    msg.set_payload(body.encode('utf-8'))
    msg['From'] = from_
    msg['To'] = to
    msg['Subject'] = 'Weekly Bug Summary'
    msg['Message-ID'] = '%s.%s@%s' % (time.time(), random.randrange(sys.maxint), from_.rsplit('@', 1)[1])
    msg['Date'] = email.Utils.formatdate()
    msg['Content-Type'] = contentType + '; charset=utf-8'

    s = StringIO.StringIO()
    g = email.Generator.Generator(s)
    g.flatten(msg)
    s.seek(0, 0)

    sendmail(from_, to, s)


def main(db, from_, to, start=None, end=None):
    conn = psycopg2.connect(db)
    curs = conn.cursor()
    # Make text come back as unicode
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, curs)

    if start is None and end is None:
        start, end = period()
    report(
        from_, to, 'text/html',
        format(
            HTML_FORMAT,
            summarize(
                start, end,
                tracstats.tickets(curs),
                tracstats.changes(curs, start, end))))
    curs.close()
    conn.close()


if __name__ == '__main__':
    if len(sys.argv) == 4:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 6:
        main(sys.argv[1], sys.argv[2], sys.argv[3], datetime.datetime(*map(int, sys.argv[4].split('-'))), datetime.datetime(*map(int, sys.argv[5].split('-'))))
    else:
        raise SystemExit("Usage: %s <postgres connection> <from address> <to address> [<start date> <end date>]" % (sys.argv[0],))
