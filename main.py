"""
Recreation of a Play-By-Mail game of 1991.
"""

__version__ = '0.1'
__author__ = 'Serge Beaumont'

import argparse
import logging
import os
import sys

from cfg import *
from log import configure_logger

from engine.round import RoundZero, GameRound
from engine.gamedirectory import GameDirectory
from rep.send import send_results_for_round, check_ok_to_send
from rep.manual import generate_manual

logger = logging.getLogger(__name__)


def main():
    def create_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("-y", "--yolo", action="store_true", help="Don't ask safety questions.")
        parser.add_argument("-i", "--ignore", action="store_true", help="Ignore missing command files.")
        parser.add_argument("gamedir", help="The game directory you want to process.")
        parser.add_argument("action", choices=['manual', 'generate', 'send'], help="Action: generate manual, rounds or send results")
        parser.add_argument("-c", "--clean", action="store_true", help="Clean the output files of a game directory")
        parser.add_argument("-z", "--zero", action="store_true", help="Regenerate the zero round.")
        parser.add_argument("-a", "--all", action="store_true", help="Regenerate all rounds.")
        parser.add_argument("-s", "--send", nargs="*", choices=['manual', 'zero', 'last'], help="Send the results via email to the players")
        return parser

    def do_zero():
        init_file = game_dir.init_file
        if not os.path.exists(init_file):
            sys.exit(f"Can not find initialization file '{init_file}'")
        RoundZero(game_dir).run()

    def do_last(last_round):
        # Deal with last round ending up -1 if there's nothing.
        last_round = 1 if last_round == -1 else (last_round + 1)
        ans = None
        if not args.yolo:
            ans = input(f"Type 'Y' if you're sure you want to process new round '{last_round}'.\n")
        if args.yolo or (ans.upper() == 'Y'):
            gr = GameRound(game_dir, last_round)
            gr.do_round(not args.ignore)

    def redo_all():
        answer = None
        if not args.yolo:
            answer = input(f"Type 'Y' if you're sure you want to CLEAN AND REDO ALL.\n")
        if args.yolo or (answer.upper() == 'Y'):
            do_zero()
            round_nr = 1
            gr = GameRound(game_dir, round_nr)
            while not gr.missing_command_files:
                # This will never be done with ignore missing command files, otherwise never stops.
                gr.do_round()
                round_nr += 1
                gr = GameRound(game_dir, round_nr)

    def do_send(game_dir: GameDirectory, what_to_send: list, last_round):
        check_ok_to_send(EMAIL_CFG_NAME, game_dir.name, INIT_FILE_NAME)
        if not args.yolo:
            answer = input(f"Type 'Y' to send out email.\n")
        if args.yolo or (answer.upper() == 'Y'):
            send_manual = 'manual' in what_to_send
            if 'zero' in what_to_send:
                send_results_for_round(game_dir.name, INIT_FILE_NAME, EMAIL_CFG_NAME, 0, send_manual)
            if 'last' in what_to_send:
                send_results_for_round(game_dir.name, INIT_FILE_NAME, EMAIL_CFG_NAME, last_round, send_manual)

    configure_logger(False, ["fontTools", "PIL"])
    parser = create_parser()
    args = parser.parse_args()

    if not os.path.exists(args.gamedir):
        sys.exit(f"Game directory '{args.gamedir}' not found.")

    game_dir = GameDirectory(args.gamedir)
    last_round = game_dir.last_round_number

    if args.clean or args.all:
        answer = None
        if not args.yolo:
            answer = input(f"Type 'Y' if you're sure you want to clean directory '{args.gamedir}'.\n")
        if args.yolo or (answer.upper() == 'Y'):
            game_dir.clean()

    match args.action:
        case 'manual':
            generate_manual()
        case 'generate':
            if args.zero:
                do_zero()
            elif args.all:
                redo_all()
            else:
                do_last(last_round)
        case 'send':
            do_send(game_dir, args.send, last_round)
        case _:
            raise ValueError(f"Action {args.action} unknown. Try manual, generate or send")


if __name__ == '__main__':
    main()
