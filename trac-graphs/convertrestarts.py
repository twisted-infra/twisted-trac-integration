from epsilon.extime import Time

def main():
    i = file('monitor-restarts.log')
    o = file('monitor-restarts.data', 'w')
    restarts = {}
    for L in i:
        t = Time.fromRFC2822(L)
        t = Time.fromDatetime(t.asDatetime().replace(hour=0, minute=0, second=0))
        t = t.asPOSIXTimestamp()
        restarts[t] = restarts.get(t, 0) + 1

    for k, v in sorted(restarts.iteritems()):
        o.write('%s %s\n' % (k, v))
    o.close()

if __name__ == '__main__':
    main()


# gnuplot
# set xdata time
# set timefmt "%s"
# plot './monitor-restarts.data' using 1:2
