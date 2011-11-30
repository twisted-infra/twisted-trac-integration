# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Trac macros for the Twisted website.
"""

from StringIO import StringIO
from urlparse import urlparse

from trac.core import TracError
from trac.util.html import Markup
from trac.wiki.formatter import OneLinerFormatter
from trac.wiki.macros import WikiMacroBase

from twisted.python.versions import Version
from twisted.python.filepath import FilePath



author = "Twisted Matrix Laboratories" 
revision = "0.1"
url = "$URL: https://launchpad.net/twisted-trac-integration $"
license = "MIT"


class VersionInformation(object):
    """
    C{dict}-alike providing values for interpolation into a format string, with
    support for lazy calculation of an md5 sum.
    """
    def __init__(self, format, version, md5sums):
        self.format = format
        self.version = version
        self.md5sums = md5sums


    def __getitem__(self, name):
        if name == 'md5':
            return self._md5()
        elif name == 'base':
            return self.version.base()
        try:
            return getattr(self.version, name)
        except AttributeError:
            raise KeyError(name)


    def _md5(self):
        """
        @rtype: C{str}
        """
        sep = '-----BEGIN PGP SIGNATURE-----\n'
        lines = self.md5sums.open().readlines()
        path = urlparse(self.format).path % dict(major=self.version.major,
            minor=self.version.minor, micro=self.version.micro,
            base=self.version.base(), md5="")
        filename = path.split('/')[-1]
        for entry in lines[3:lines.index(sep)]:
            entry = entry.rstrip('\n').split('  ')
            if entry[1] == filename:
                return entry[0]
        return ''



class ProjectVersionMacro(WikiMacroBase):
    """
    Macro that knows the current [http://twistedmatrix.com Twisted] version number.

    The version information is loaded from a folder containing text files with
    md5sums for each released package/installer. Also see the
    [http://twistedmatrix.com/trac/wiki/Downloads#SignedMD5Sums Twisted downloads]
    page.

    '''Standalone'''
    {{{
    [[ProjectVersion]]
    }}}

    produces:

    [[ProjectVersion]]

    '''URL'''

    {{{
    [[ProjectVersion(http://twistedmatrix.com/Releases/Twisted/%(major)s.%(minor)s/Twisted-%(base)s.win32-py2.7.msi Twisted %(base)s for Python 2.7)]]
    }}}

    produces:

    [[ProjectVersion(http://twistedmatrix.com/Releases/Twisted/%(major)s.%(minor)s/Twisted-%(base)s.win32-py2.7.msi Twisted %(base)s for Python 2.7)]]

    Including the MD5 hash (eg. `b568b504524fda2440c62aa1616b3fe5`):

    {{{
     - [[ProjectVersion(http://pypi.python.org/packages/source/T/Twisted/Twisted-%(base)s.tar.bz2#md5=%(md5)s Twisted %(base)s tar)]]
     - [[ProjectVersion(http://pypi.python.org/packages/2.7/T/Twisted/Twisted-%(base)s.win32-py2.7.msi#md5=%(md5)s Twisted %(base)s for Python 2.7)]]
    }}}

    produces:

     - [[ProjectVersion(http://pypi.python.org/packages/source/T/Twisted/Twisted-%(base)s.tar.bz2#md5=%(md5)s Twisted %(base)s tar)]]
     - [[ProjectVersion(http://pypi.python.org/packages/2.7/T/Twisted/Twisted-%(base)s.win32-py2.7.msi#md5=%(md5)s Twisted %(base)s for Python 2.7)]]

    '''Source browser'''

    {{{
    [[ProjectVersion(source:/tags/releases/twisted-%(base)s/ Tag for Twisted %(base)s)]]
    }}}

    produces:

    [[ProjectVersion(source:/tags/releases/twisted-%(base)s/ Tag for Twisted %(base)s)]]
    """

    RELEASES = FilePath('/srv/www-data/twisted/Releases/')

    def getVersion(self):
        versions = []
        pattern = 'twisted-%s-md5sums.txt'
        for md5sums in self.RELEASES.globChildren(pattern % '*'):
            try:
                components = map(int, md5sums.basename().split('-')[1].split('.'))
            except ValueError:
                pass
            else:
                versions.append(components)
        try:
            version = Version('Twisted', *max(versions))
        except ValueError:
            self.log.error(
                "Could not parse a version from files in the RELEASES directory %s" % (
                self.RELEASES.path,))
            raise TracError("Error loading Twisted version information")

        md5sums_file = self.RELEASES.child(pattern % version.base())
        return version, md5sums_file


    def _expandText(self, args):
        if not self.RELEASES.exists():
            self.log.error(
                "The specified RELEASES directory does not exist at %s" % (
                self.RELEASES.path,))
            raise TracError("Error loading Twisted version information")

        version, md5sums = self.getVersion()

        if args is None:
            text = version.base()
        else:
            uc = unicode(args).replace('%28', '(').replace('%29', ')')
            values = VersionInformation(uc, version, md5sums)

            if uc.find('%(md5)s') > -1 and values['md5'] == '':
                self.log.warn(
                    "Could not find a matching hexdigest for %s" % (
                    version.base(),))
                raise TracError("Error loading Twisted version information")

            url = urlparse(uc).netloc
            text = uc % values

            # handle links
            if args.startswith('source:') or url != '':
                text = "[%s]" % (text,)
        return text


    def expand_macro(self, formatter, name, args):
        """
        Return output that will be displayed in the Wiki content.

        @param name: the actual name of the macro
        @param args: the text enclosed in parenthesis at the call of the macro.
          Note that if there are ''no'' parenthesis (like in, e.g.
          [[ProjectVersion]]), then `args` is `None`.
        """
        text = self._expandText(args)

        out = StringIO()
        OneLinerFormatter(self.env, formatter.context).format(text, out)

        return Markup(out.getvalue())
