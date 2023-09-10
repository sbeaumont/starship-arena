"""
Recreation of a Play-By-Mail game of 1991.
"""

__version__ = '0.1'
__author__ = 'Serge Beaumont'

import argparse
import logging
import sys
import os

from cfg import GAME_DATA_DIR
from log import configure_logger

from engine.admin import setup_game
from engine.round import GameRound
from engine.gamedirectory import GameDirectory
from rep.send import send_results_for_round, check_ok_to_send
from rep.manual import generate_manual

logger = logging.getLogger('starship-arena')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("gamedir",
                        help="The name of the game you want to process.")
    parser.add_argument("action",
                        nargs="*",
                        choices=['setup', 'generate', 'manual', 'send'],
                        help="Action: clean, generate manual, rounds or send results")
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


def generate(game_dir: GameDirectory):
    round_nr = 1
    gr = GameRound(game_dir, round_nr)
    while not gr.missing_command_files:
        if not gr.is_generated:
            gr.do_round()
        round_nr += 1
        gr = GameRound(game_dir, round_nr)


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
    game_dir = GameDirectory(GAME_DATA_DIR, args.gamedir)
    game_dir.check_ok()

    if 'setup' in args.action:
        print("Setting up fresh game...")
        do_setup(game_dir)
    if 'manual' in args.action:
        print("Generating manual...")
        generate_manual()
    if 'generate' in args.action:
        generate(game_dir)
    if 'send' in args.action:
        print("Sending results...")
        do_send(game_dir, args.send)


if __name__ == '__main__':
    main()
