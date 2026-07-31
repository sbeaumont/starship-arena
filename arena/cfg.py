import os
import secret
import logging

logger = logging.getLogger('starship-arena.config')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Everything the code needs to find is anchored to the repository, not to the working
# directory: a host decides for itself where it runs things from.
WEB_ROOT = os.path.join(REPO_ROOT, 'arena', 'admin_ui')
TEMPLATE_DIR = os.path.join(WEB_ROOT, 'templates')

MANUAL_TEMPLATE_DIR = TEMPLATE_DIR
MANUAL_TEMPLATE = 'manual.html'

# Where the interactive game UI lives, so the admin pages can link a player straight to their
# map. Defaults to how a deployed game serves it (arena/serve.py puts it at /play), so a host
# needs no configuring; the dev runners override it to point at the Vite dev server instead.
GAME_UI_URL = os.environ.get('GAME_UI_URL', '/play')

# And back the other way, so a director can step from the game to the console. Defaults to how a
# deployed game serves it - one application, console at the root; the dev runner points it at the
# separate Flask server.
ADMIN_UI_URL = os.environ.get('ADMIN_UI_URL', '/')

# The built game UI. `npm run build --prefix game-ui` writes it here; it is plain static files,
# so no Node is involved in serving it. Anchored to the repository rather than the working
# directory, because a host decides for itself where it runs things from.
GAME_UI_DIST = os.environ.get('GAME_UI_DIST', os.path.join(REPO_ROOT, 'game-ui', 'dist'))

GAME_DATA_DIR = os.environ.get('GAME_DATA_DIR')
if (not GAME_DATA_DIR) and ('GAME_DATA_DIR' in dir(secret)):
    GAME_DATA_DIR = secret.GAME_DATA_DIR
# A relative setting means "inside the repository", so it survives being run from elsewhere.
if GAME_DATA_DIR and not os.path.isabs(GAME_DATA_DIR):
    GAME_DATA_DIR = os.path.join(REPO_ROOT, GAME_DATA_DIR)
logger.info(f"cfg.py: Loading game data from {GAME_DATA_DIR}")

# The address players use, so login links can be printed whole. Not "where this machine serves
# from": a link is handed to somebody else, so it has to point at the game they play, wherever
# it is issued from. Only the CLI wants this; the web app never has to know its own name.
SITE_URL = os.environ.get('SITE_URL', '')
if (not SITE_URL) and ('SITE_URL' in dir(secret)):
    SITE_URL = secret.SITE_URL

STATUS_FILE_TEMPLATE = "status_round_{}.pickle"
COMMANDS_DIR = 'commands/'
READY_DIR = 'ready/'
READY_FILE_TEMPLATE = READY_DIR + "{}.txt"
READY_LINE_TEMPLATE = "Round {} Ready"
COMMAND_FILE_TEMPLATE = COMMANDS_DIR + "{}-commands-{}.txt"
INIT_FILE_NAME = "ships.jsonl"
SPAWN_FILE_NAME = "spawns.jsonl"
ARCHIVE_DIR_NAME = "archived"
REGISTERING_DIR_NAME = "registering"
REGISTRATION_FILE_NAME = "registrations.jsonl"
SETTINGS_FILE_NAME = "settings.jsonl"
SCENARIO_FILE_NAME = "scenario.json"
# Who may log in, across every game. Lives at the data root rather than inside a game, because a
# player's name is their identity everywhere.
PLAYERS_FILE_NAME = "players.jsonl"
MANUAL_FILENAME = os.path.join(REPO_ROOT, "starship-arena-manual.pdf")

# ============================================= SHIP CORE METRICS

MAX_SCAN_MULTIPLIER = 6


def max_scan(value):
    return int(value * MAX_SCAN_MULTIPLIER)
