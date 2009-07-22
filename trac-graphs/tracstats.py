
import time
import datetime

try:
    from pysqlite2.dbapi2 import connect
except ImportError:
    from sqlite3 import connect

def udict(**kw):
    return dict([
        (k.decode('ascii'), v)
        for (k, v)
        in kw.iteritems()])



def allChanges(cursor, id):
    """
    Retrieve all ticket changes for the given ticket.
    """
    statement = ("select time, author, field, oldvalue, newvalue "
                 "from ticket_change "
                 "where ticket = ? "
                 "order by time asc")
    cursor.execute(statement, (id,))
    return [
        udict(time=datetime.datetime.fromtimestamp(row[0]),
              author=row[1],
              field=row[2],
              old=row[3],
              new=row[4])
        for row in cursor.fetchall()]



def tickets(cursor):
    """
    Retrieve all tickets.
    """
    statement = ("select time, id, type, component, summary, status, priority, resolution, reporter "
                 "from ticket "
                 "order by time asc")
    cursor.execute(statement)
    return dict([
        (row[1], udict(time=datetime.datetime.fromtimestamp(row[0]),
                       id=row[1], type=row[2], component=row[3],
                       summary=row[4], status=row[5], priority=row[6],
                       resolution=row[7], reporter=row[8],
                       changes=allChanges(cursor, row[1])))
        for row
        in cursor.fetchall()])



def changes(cursor, start, end):
    """
    Retrieve information about the changes which occurred to tickets over the
    given interval.
    """
    statement = ("select time, ticket, field, oldvalue, newvalue, author "
                 "from ticket_change "
                 "where field = 'status' and (time > %(start)d and time < %(end)d) "
                 "order by time asc") % {'start': time.mktime(start.utctimetuple()),
                                         'end': time.mktime(end.utctimetuple())}
    cursor.execute(statement)
    return [udict(time=datetime.datetime.fromtimestamp(row[0]), ticket=row[1],
                  field=row[2], old=row[3], new=row[4], author=row[5])
            for row
            in cursor.fetchall()]



def comments(cursor):
    """
    Retrieve information about the comments made on tickets.
    """
    statement = ("select time, ticket, field, oldvalue, newvalue, author "
                 "from ticket_change "
                 "where field = 'comment' "
                 "order by time asc")
    cursor.execute(statement)
    return [udict(time=datetime.datetime.fromtimestamp(row[0]), ticket=row[1],
                  field=row[2], old=row[3], new=row[4], author=row[5])
            for row
            in cursor.fetchall()]



class TimeSeries:
    def __init__(self, name, data):
        self.name = name
        self.data = data


    def display(self):
        for date, count in self.data:
            print date.isoformat(), count


    def plot(self, legend, colorer):
        from pylab import plot, title, polyfit, polyval
        when = []
        when2 = []
        what = []
        for (a, b) in self.data:
            when.append(a)
            when2.append(time.mktime(a.timetuple()))
            what.append(b)
        best = polyval(polyfit(when2, what, 1), when2)
        plot(when, what, colorer())
        plot(when, best, colorer())
        legend([self.name, self.name + " (best fit)"])


    def show(self, colorer):
        from pylab import show, legend
        self.plot(legend, colorer)
        show()

    def _computeChanges(self):
        results = iter(self.data)
        lastWhen, lastValue = results.next()
        for when, value in results:
            yield when, value - lastValue
            lastValue = value


    def changes(self):
        return TimeSeries(self.name + ' (changes)', self._computeChanges())


class Frequencies(TimeSeries):
    def display(self):
        for (label, value) in self.data:
            print label, value


    def plot(self, legend, colorer):
        from pylab import bar, xticks, show
        labels = [label for (label, value) in self.data]
        values = [value for (label, value) in self.data]

        plot = bar(range(len(values)), values, 1.0)
        xticks([x + 0.5 for x in range(len(labels))], labels)
        show()


def colorer():
    for style in "-.":
        for clr in "rgbcmy":
            yield clr + style


def driver(main, argv):
    args = []
    flags = {}
    for a in argv:
        if a.startswith('--'):
            flags[a[2:]] = True
        else:
            args.append(a)
    dbfilename = args.pop(0)
    connection = connect(dbfilename)
    cursor = connection.cursor()
    results = main(cursor, *args)
    if 'changes' in flags:
        results = results.changes()
    if 'plot' in flags:
        results.show(colorer().next)
    else:
        results.display()