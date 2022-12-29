
TEMPLATE_DIR = './templates'

ROUND_ZERO_NAME = 'round-0'

ROUND_ZERO_TEMPLATE = 'round-zero.html'
ROUND_TEMPLATE = 'round-template.html'
ROUND_EMAIL_TEMPLATE = 'round-email-body.html'
SHIP_COMMAND_TEMPLATE = 'ship-command-round.txt'
MANUAL_TEMPLATE = 'manual.html'

STATUS_FILE_TEMPLATE = "status_round_{}.pickle"
COMMAND_FILE_TEMPLATE = "{}-commands-{}.txt"

INIT_FILE_NAME = "ships.txt"
EMAIL_CFG_NAME = "email.txt"
MANUAL_FILENAME = 'starship-arena-manual.pdf'

# ============================================= SHIP CORE METRICS

MAX_SCAN_MULTIPLIER = 6


def max_scan(value):
    return int(value * MAX_SCAN_MULTIPLIER)
