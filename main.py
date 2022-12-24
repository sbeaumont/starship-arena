import argparse
import logging
import os
import sys

from cfg import *
from engine.round import RoundZero, GameRound
from engine.gamedirectory import GameDirectory
from log import configure_logger
from rep.send import send_results_for_round
from rep.report import generate_manual

logger = logging.getLogger(__name__)


def main():
    configure_logger(False, ["fontTools", "PIL"])
    parser = argparse.ArgumentParser()
    parser.add_argument("gamedir", help="The game directory you want to process.")
    parser.add_argument("round", choices=['manual', 'zero', 'last', 'redo-all', 'none'], help="Which rounds to process")
    parser.add_argument("-m", "--manual", action="store_true", help="Generate and include manual")
    parser.add_argument("-y", "--yolo", action="store_true", help="Don't ask safety questions.")
    parser.add_argument("-c", "--clean", action="store_true", help="Clean the output files of a game directory")
    parser.add_argument("-i", "--ignore", action="store_true", help="Ignore missing command files.")
    parser.add_argument("-s", "--send", choices=['manual', 'zero', 'last', 'all'], help="Send the results via email to the players")
    args = parser.parse_args()

    if not os.path.exists(args.gamedir):
        sys.exit(f"Game directory '{args.gamedir}' not found.")

    game_dir = GameDirectory(args.gamedir)
    last_round = game_dir.last_round_number

    if args.clean or (args.round == 'redo-all'):
        answer = None
        if not args.yolo:
            answer = input(f"Type 'Y' if you're sure you want to clean directory '{args.gamedir}'.\n")
        if args.yolo or (answer == 'Y'):
            game_dir.clean()

    if args.manual:
        generate_manual()

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
        if args.yolo or (ans == 'Y'):
            gr = GameRound(game_dir, last_round)
            gr.do_round(not args.ignore)

    def redo_all():
        answer = None
        if not args.yolo:
            answer = input(f"Type 'Y' if you're sure you want to CLEAN AND REDO ALL.\n")
        if args.yolo or (answer == 'Y'):
            do_zero()
            round_nr = 1
            gr = GameRound(game_dir, round_nr)
            while not gr.missing_command_files:
                # This will never be done with ignore missing command files, otherwise never stops.
                gr.do_round()
                round_nr += 1
                gr = GameRound(game_dir, round_nr)

    match args.round:
        case 'zero':
            do_zero()
        case 'last':
            do_last(last_round)
        case 'redo-all':
            redo_all()
        case 'manual':
            generate_manual()
        case 'none':
            pass

    if args.send:
        answer = input(f"Type 'Y' to send out email.\n")
        if answer.upper() == 'Y':
            round_to_send = -1
            match args.send:
                case 'last':
                    round_to_send = last_round
                case 'zero':
                    round_to_send = 0
            if round_to_send > -1:
                send_results_for_round(game_dir.name, INIT_FILE_NAME, EMAIL_CFG_NAME, round_to_send, args.manual)


if __name__ == '__main__':
    main()
