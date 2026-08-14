"""
Recreation of a Play-By-Mail game of 1991.

This is the command-line interface, not used by the web app. It is also how the first login is
made: a shell on the host is the one credential that cannot be handed out, so issuing the
director's link belongs here rather than on a web page.
"""

__version__ = '0.1'
__author__ = 'Serge Beaumont'

import argparse
import logging
import sys
import os

from arena.announce import Announcer
from arena.cfg import LOG_FILE_NAME, PLAY_URL
from arena.log import configure_logger

from arena.app.clock import server_now
from arena.app.players import PlayerRegistry, DIRECTOR, PLAYER
from arena.app.services import AdminService
from arena.engine.admin import setup_game
from arena.engine.game import Game
from arena.engine.gamedirectory import GAMES_ROOT, GameDirectory, GamesIn
from arena.engine.reporting.manual import generate_manual

logger = logging.getLogger('starship-arena')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",
                        choices=['setup', 'generate', 'regenerate', 'manual', 'link', 'players',
                                 'process_due', 'remind_due', 'announce', 'export'],
                        help="Set a game up, generate its unprocessed rounds, replay games from "
                             "their orders, build the manual, issue a login link, list who can log "
                             "in, process the games due this hour, remind whoever still owes "
                             "orders, send a test announcement, or export a game to the museum")
    parser.add_argument("gamedir", nargs='?',
                        help="The name of the game you want to process.")
    parser.add_argument("-n", "--name", help="Who to issue a login link for.")
    parser.add_argument("-d", "--director", action="store_true",
                        help="Issue the link with director rights.")
    parser.add_argument("-u", "--url", default="",
                        help="Where the game UI is, e.g. https://example.com. Left out, the "
                             "link is printed as a path.")
    return parser.parse_args()


def do_setup(game_dir: GameDirectory):
    init_file = game_dir.init_file
    if not os.path.exists(init_file):
        sys.exit(f"Can not find initialization file '{init_file}'")
    setup_game(game_dir)


def generate(data_root: str, game_name: str):
    """Process every round whose orders are all in, one after the other.

    A Game reads the round it is on when it is built, so each round gets a fresh one."""
    while True:
        game = Game(GameDirectory(data_root, game_name))
        if not game.current_round_ready:
            break
        logger.info(f"Processing round {game.current_round_nr}")
        game.process_current_round()


def issue_link(name: str, director: bool, url: str):
    """Give someone a fresh login link, printed for sending on.

    Issuing again replaces whatever they had, so this is also how a lost or leaked link is
    replaced. The first director's link has to come from here: the web pages need a director
    before they can hand out anything."""
    if not name:
        sys.exit("Who for? Use --name.")
    player = PlayerRegistry(GAMES_ROOT.root).issue(name, role=DIRECTOR if director else PLAYER)
    # The address given is the game UI's own, wherever that is, and it answers at the root of it.
    # A host that knows its own address says so in secret.py.
    where = url.rstrip('/') if url else PLAY_URL
    print(f"{player.name}{' (director)' if player.is_director else ''}")
    print(f"  {where}/?login={player.token}")
    if '://' not in where:
        print("  ^ a path, not a link. Give the address as the second argument, or set "
              "SITE_URL in secret.py.")


def regenerate(game_name: str = None) -> int:
    """Replay games from their ships file and orders, back to the round they were on.

    One game, or every playable one when none is named. Each round it ends on is printed against
    the round it was on: a game whose orders are missing for a round cannot be replayed past it,
    and the rounds after that are gone. Returns how many came back short.

    Read off the file names rather than through a listing, because a listing loads every world to
    say what each game is waiting for, and a world too old for this code to read is the whole
    reason to be here."""
    admin = AdminService()
    games = admin.playable_games_on_disk()
    if game_name:
        if game_name not in games:
            sys.exit(f"No playable game called '{game_name}'.")
        games = {game_name: games[game_name]}
    short = 0
    for name, was in games.items():
        now = admin.regenerate_game(name)
        short += (now < was)
        print(f"  {name:24} round {was} -> {now}{'   LOST ROUNDS' if now < was else ''}")
    return short


def process_due():
    """Process every game whose settings name this hour. Run hourly by cron."""
    done = AdminService().process_due()
    for line in done:
        logger.info(line)
    if not done:
        logger.info(f"Nothing due at {server_now():%H:00 %Z}")


def remind_due():
    """Poke whoever still owes orders and asked to be poked. Run by cron, on its own schedule."""
    done = AdminService().remind_due()
    for line in done:
        logger.info(line)
    if not done:
        logger.info(f"Nobody to remind at {server_now():%H:%M %Z}")


def announce_test():
    """Say something harmless on every channel. This is how a host proves it can reach them."""
    announcer = Announcer()
    if not announcer.configured:
        print("No channel has an address. Set DISCORD_MESSAGE_WEBHOOK in secret.py.")
        return
    announcer.announce(f"Starship Arena checking in at {server_now():%H:%M %Z}.")
    print(f"Sent to: {', '.join(c.name for c in announcer.configured)}")


def _reminders_of(p) -> str:
    """What this person asked to be reminded by. Somewhere to reach them counts as something."""
    if not p.discord_id:
        return ''
    asked = ([f"{p.remind_hours_before}h ahead"] if p.wants_deadline_reminder else []) \
        + ([f"daily at {p.remind_daily_hour:02d}:00 {p.timezone}"]
           if p.wants_daily_reminder else [])
    return f"   reminded {', '.join(asked)}" if asked else '   reachable, no reminder set'


def list_players():
    players = PlayerRegistry(GAMES_ROOT.root).all()
    if not players:
        print("Nobody can log in yet. Issue the first link with:")
        print("  python arena/cli/main.py link --name <you> --director")
        return
    for p in players:
        print(f"  {p.name:20} {p.role}{'' if p.active else '   deactivated'}"
              f"{_reminders_of(p)}")


def main():
    configure_logger(LOG_FILE_NAME)
    args = parse_args()
    if args.action == 'manual':
        logger.info("Generating manual...")
        generate_manual()
    elif args.action == 'link':
        issue_link(args.name, args.director, args.url)
    elif args.action == 'players':
        list_players()
    elif args.action == 'process_due':
        process_due()
    elif args.action == 'remind_due':
        remind_due()
    elif args.action == 'regenerate':
        logger.info("Regenerating...")
        if regenerate(args.gamedir):
            sys.exit("A game came back short. Restore the backup before anything else runs.")
    elif args.action == 'announce':
        announce_test()
    elif args.action == 'export':
        if not args.gamedir:
            sys.exit("Which game? Give its name.")
        print(f"Written to {AdminService(GAMES_ROOT.root).export_to_valhalla(args.gamedir)}")
    else:
        if not args.gamedir:
            sys.exit("Which game? Give its name.")
        game_dir = GAMES_ROOT.directory_in(GamesIn.Active, args.gamedir)
        game_dir.check_ok()

        if args.action == 'setup':
            logger.info("Setting up fresh game...")
            do_setup(game_dir)
        else:
            logger.info("Generating unprocessed rounds...")
            generate(str(GAMES_ROOT.games), args.gamedir)


if __name__ == '__main__':
    main()