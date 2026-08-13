"""Pushing a message out of the game: a Discord channel today, email one day.

Beside the layers rather than inside one, the way `log.py` is. A channel is handed text and knows
how to deliver it; nothing here knows what a round is.
See docs/adr/0029-announcements-leave-through-one-channel.md."""

import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from arena.cfg import DISCORD_WEBHOOK

logger = logging.getLogger('starship-arena.announce')

TIMEOUT = 5
# Cloudflare fronts Discord and bans the default `Python-urllib/x.y` with its error 1010, so a
# client that does not name itself gets a 403 before Discord ever sees the request.
USER_AGENT = 'Starship-Arena'


class Channel(ABC):
    """Somewhere a message can go."""

    @property
    @abstractmethod
    def name(self) -> str:
        """What to call this channel in a log line."""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this channel has somewhere to send. A channel without an address stays quiet."""
        ...

    @abstractmethod
    def send(self, message: str) -> None:
        ...


class DiscordWebhook(Channel):
    """A Discord channel, addressed by the webhook URL its server hands out."""

    def __init__(self, url: str):
        self.url = url

    @property
    def name(self) -> str:
        return 'Discord'

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    def send(self, message: str) -> None:
        request = urllib.request.Request(self.url,
                                         data=json.dumps({'content': message}).encode(),
                                         headers={'Content-Type': 'application/json',
                                                  'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
                logger.debug(f"Discord answered {answer.status}")
        except urllib.error.HTTPError as e:
            # The status line alone says nothing useful; the reason is in the body.
            raise RuntimeError(f"Discord refused it: {e.code} {e.read().decode()}") from e


class Announcer:
    """Says the same thing on every channel that has somewhere to say it."""

    def __init__(self, channels: list = None):
        self.channels = channels if channels is not None else [DiscordWebhook(DISCORD_WEBHOOK)]

    @property
    def configured(self) -> list:
        return [c for c in self.channels if c.is_configured]

    def announce(self, message: str) -> list:
        """The channels that took it. A caller with nothing riding on delivery can ignore that."""
        taken = []
        for channel in self.configured:
            # The round is already processed and saved by the time this runs. A webhook that is
            # down, or a host that will not let the call out, must not turn that into a failure.
            try:
                channel.send(message)
                logger.info(f"Announced on {channel.name}: {message}")
                taken.append(channel)
            except Exception as e:
                logger.warning(f"{channel.name} took nothing: {e}")
        return taken