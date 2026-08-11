"""The suite is a host with no address, so nothing it does reaches a real channel.

Set here because `arena.cfg` reads the webhook once at import, and this package is imported before
anything under it. A test that wants to watch an announcement injects its own channel, the way
`test_announcing.Loudspeaker` does.
"""

import os

os.environ['DISCORD_MESSAGE_WEBHOOK'] = ''