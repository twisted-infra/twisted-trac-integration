from twisted.application import service, internet

import config, commit, commit_bot

application = service.Application('Commit-Bot')
svc = internet.TCPClient(config.IRC_SERVER, config.IRC_PORT, commit_bot.CommitFactory())
svc.setServiceParent(application)
