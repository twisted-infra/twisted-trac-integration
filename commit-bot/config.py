# Hostname where persistent bot process is listening
BOT_HOST = 'localhost'

# Port number of same
BOT_PORT = 15243

# Hostname of the IRC server to which we will connect
IRC_SERVER = 'irc.freenode.net'
IRC_PORT = 6667

# Nickname to use on that IRC server
BOT_NICK = 'kenaan7'

# Password for this nickname
BOT_PASS = 'abcdefg'

# Maximum number of characters to put into a single IRC message
LINE_LENGTH = 160

# Delay, in seconds, between IRC messages
LINE_RATE = 1.0

# Three-tuples of (repository path, filename expression, channel) defining
# the rules for announcing commit messages.
COMMIT_RULES = [
    ('/svn/Divmod', '.*', ['#divmod.test'])]

# Two-tuples of (tracker URL, channel) defining the rules for announcing
# ticket changes.
TICKET_RULES = [
    ('http://example.com/trac/', ['#bottest'])]

# Two-tuples of (project name, list of channels) defining the rules for
# announcing active Launchpad merge proposals.
LAUNCHPAD_MERGE_PROPOSAL_RULES = [
    ('Example', ['#bottest']),
    ]

# The channel to which to send alerts.
ALERT_CHANNEL = '#bottest'

# The directory in which log files will be written
LOG_ROOT = '~'
