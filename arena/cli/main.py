"""
Recreation of a Play-By-Mail game of 1991.

This is the command-line interface, not used by the web app.
"""

__version__ = '0.1'
__author__ = 'Serge Beaumont'

import argparse
import logging
import sys
import os

from arena.cfg import GAME_DATA_DIR
from arena.log import configure_logger

from arena.engine.admin import setup_game
from arena.engine.game import Game
from arena.engine.gamedirectory import GameDirectory
from arena.cli.send import send_results_for_round, check_ok_to_send
from arena.engine.reporting.manual import generate_manual

logger = logging.getLogger('starship-arena')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",
                        nargs="*",
                        choices=['setup', 'generate', 'manual', 'send'],
                        help="Action: clean, generate manual, rounds or send results")
    parser.add_argument("gamedir",
                        help="The name of the game you want to process.")
    parser.add_argument("-s", "--send",
                        nargs="*",
                        choices=['manual', 'zero', 'last'],
                        help="Send the results via email to the players")
    return parser.parse_args()


def do_setup(game_dir: GameDirectory):
    init_file = game_dir.init_file
    if not os.path.exists(init_file):
        sys.exit(f"Can not find initialization file '{init_file}'")
    setup_game(game_dir)


def generate(game_dir: GameDirectory, round_nr=1):
    game = Game(game_dir, round_nr)
    while game.round_ready:
        game.do_round()
        game.init_next_round()


def do_send(game_dir: GameDirectory, what_to_send: list):
    check_ok_to_send(game_dir)
    send_manual = 'manual' in what_to_send
    if 'zero' in what_to_send:
        send_results_for_round(game_dir, 0, send_manual)
    if 'last' in what_to_send:
        send_results_for_round(game_dir, game_dir.last_round_number, send_manual)


def main():
    configure_logger(False, ["fontTools", "PIL"])
    args = parse_args()
    if 'manual' in args.action:
        logger.info("Generating manual...")
        generate_manual()
    else:
        game_dir = GameDirectory(GAME_DATA_DIR, args.gamedir)
        game_dir.check_ok()

        if 'setup' in args.action:
            logger.info("Setting up fresh game...")
            do_setup(game_dir)
        if 'generate' in args.action:
            logger.info("Generating unprocessed rounds...")
            generate(game_dir)
        if 'send' in args.action:
            if os.path.exists(game_dir.email_file):
                logger.info("Sending results...")
                do_send(game_dir, args.send)
            else:
                sys.exit(f"Can't send results: no {game_dir.email_file} file found.")


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    main()
