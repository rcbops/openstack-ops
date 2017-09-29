#!/usr/bin/env python

import sys

from hammertime.config import HammerTimeConfig
from hammertime.core import HammerTimeCore
from hammertime.cache import HammerTimeCache

if len(sys.argv) < 2:
    sys.exit('usage: %s ticket-number [ticket-number ...] [status]' % os.path.basename(sys.argv[0]))

ticket_numbers = sys.argv[1:-1]
if len(sys.argv) > 2:
    ticket_status = sys.argv[-1]
else:
    ticket_status = 'confirm-solved'

status = {
    'confirm-solved': 5687
}

config = HammerTimeConfig(
    {
        'nocolor': True,
        'skiproot': False,
        'show_passwords': False,
        'expect_timeout': 60,
        'ssh_args': '',
        'terminal': None,
        'quiet': False,
    })

cache = HammerTimeCache(config)
core = HammerTimeCore(config, cache)

for ticket_number in ticket_numbers:
    print('Setting ticket %s to %s' % (ticket_number, ticket_status))
    core.ticket.closeTicket(ticket_number, status[ticket_status])
