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
from arena.cfg import GAMES_ROOT, LOG_FILE_NAME, PLAY_URL
from arena.log import configure_logger

from arena.app.clock import server_now
from arena.app.players import PlayerRegistry, DIRECTOR, PLAYER
from arena.app.services import AdminService
from arena.engine.admin import setup_game
from arena.engine.game import Game
from arena.engine.gamedirectory import GameDirectory
from arena.engine.reporting.manual import generate_manual

logger = logging.getLogger('starship-arena')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",
                        choices=['setup', 'generate', 'manual', 'link', 'players', 'process_due',
                                 'announce'],
                        help="Set a game up, generate its unprocessed rounds, build the manual, "
                             "issue a login link, list who can log in, process the games due "
                             "this hour, or send a test announcement")
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


def process_due():
    """Process every game whose settings name this hour. Run hourly by cron."""
    done = AdminService().process_due()
    for line in done:
        logger.info(line)
    if not done:
        logger.info(f"Nothing due at {server_now():%H:00 %Z}")


def announce_test():
    """Say something harmless on every channel. This is how a host proves it can reach them."""
    announcer = Announcer()
    if not announcer.configured:
        print("No channel has an address. Set DISCORD_MESSAGE_WEBHOOK in secret.py.")
        return
    announcer.announce(f"Starship Arena checking in at {server_now():%H:%M %Z}.")
    print(f"Sent to: {', '.join(c.name for c in announcer.configured)}")


def list_players():
    players = PlayerRegistry(GAMES_ROOT.root).all()
    if not players:
        print("Nobody can log in yet. Issue the first link with:")
        print("  python arena/cli/main.py link --name <you> --director")
        return
    for p in players:
        print(f"  {p.name:20} {p.role}{'' if p.active else '   deactivated'}")


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
    elif args.action == 'announce':
        announce_test()
    else:
        if not args.gamedir:
            sys.exit("Which game? Give its name.")
        game_dir = GameDirectory(str(GAMES_ROOT.games), args.gamedir)
        game_dir.check_ok()

        if args.action == 'setup':
            logger.info("Setting up fresh game...")
            do_setup(game_dir)
        else:
            logger.info("Generating unprocessed rounds...")
            generate(str(GAMES_ROOT.games), args.gamedir)


if __name__ == '__main__':
    main()