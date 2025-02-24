import os
import secret
import logging

logger = logging.getLogger('starship-arena.config')

TEMPLATE_DIR = 'arena_web/templates'

ROUND_ZERO_NAME = 'round-0'

ROUND_ZERO_TEMPLATE = 'round-zero.html'
ROUND_TEMPLATE = 'round-template.html'
ROUND_EMAIL_TEMPLATE = 'round-email-body.html'
SHIP_COMMAND_TEMPLATE = 'ship-command-round.txt'
MANUAL_TEMPLATE = 'manual.html'

GAME_DATA_DIR = os.environ.get('GAME_DATA_DIR')
if (not GAME_DATA_DIR) and ('GAME_DATA_DIR' in dir(secret)):
    GAME_DATA_DIR = secret.GAME_DATA_DIR
logger.info(f"cfg.py: Loading game data from {GAME_DATA_DIR}")

GRAVEYARD_TEMPLATE = "graveyard.pickle"
STATUS_FILE_TEMPLATE = "status_round_{}.pickle"
COMMANDS_DIR = 'commands/'
COMMAND_FILE_TEMPLATE = COMMANDS_DIR + "{}-commands-{}.txt"
ROUND_DIR_TEMPLATE = "round-{rnr}"
PICTURE_TEMPLATE = "round-{rnr}/{name}-round-{rnr}.png"
PDF_TEMPLATE = "round-{rnr}/{name}-round-{rnr}.pdf"

INIT_FILE_NAME = "ships.txt"
EMAIL_CFG_NAME = "email.txt"
MANUAL_FILENAME = "starship-arena-manual.pdf"

# ============================================= SHIP CORE METRICS

MAX_SCAN_MULTIPLIER = 6


def max_scan(value):
    return int(value * MAX_SCAN_MULTIPLIER)
