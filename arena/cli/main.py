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
from arena.engine.reporting.manual import generate_manual

logger = logging.getLogger('starship-arena')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",
                        nargs="*",
                        choices=['setup', 'generate', 'manual'],
                        help="Action: set a game up, generate its unprocessed rounds, or build the manual")
    parser.add_argument("gamedir",
                        help="The name of the game you want to process.")
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


def main():
    configure_logger(False, ["fontTools"])
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
            generate(GAME_DATA_DIR, args.gamedir)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    main()
