import os
import secret
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger('starship-arena.config')

REPO_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Everything the code needs to find is anchored to the repository, not to the working
# directory: a host decides for itself where it runs things from.
WEB_ROOT = os.path.join(REPO_ROOT, 'arena', 'admin_ui')
TEMPLATE_DIR = os.path.join(WEB_ROOT, 'templates')

MANUAL_TEMPLATE_DIR = TEMPLATE_DIR
MANUAL_TEMPLATE = 'manual.html'

# Where the interactive game UI lives, so the admin pages can link a player straight to their
# map. A prefix without its trailing slash, empty at the root: that is how a deployed game serves
# it, so a host needs no configuring. The dev runners point it at the Vite server instead.
GAME_UI_URL = os.environ.get('GAME_UI_URL', '')

# And back the other way, so a director can step from the game to the console. Defaults to how a
# deployed game serves it - one application, console under /director; the dev runner points it at
# the separate Flask server.
ADMIN_UI_URL = os.environ.get('ADMIN_UI_URL', '/director')

# The built game UI. `npm run build --prefix game-ui` writes it here; it is plain static files,
# so no Node is involved in serving it. Anchored to the repository rather than the working
# directory, because a host decides for itself where it runs things from.
GAME_UI_DIST = os.environ.get('GAME_UI_DIST', os.path.join(REPO_ROOT, 'game-ui', 'dist'))

# The address players use, so login links can be printed whole. Not "where this machine serves
# from": a link is handed to somebody else, so it has to point at the game they play, wherever
# it is issued from. Only login links want this; no page has to know its own name.
SITE_URL = os.environ.get('SITE_URL', '')
if (not SITE_URL) and ('SITE_URL' in dir(secret)):
    SITE_URL = secret.SITE_URL

# Where a login link points. A GAME_UI_URL that already names a host - the dev runner's Vite
# server - is whole as it stands; otherwise the site's address goes in front of the path.
PLAY_URL = GAME_UI_URL if '://' in GAME_UI_URL else SITE_URL.rstrip('/') + GAME_UI_URL

# Where announcements go. One webhook for the whole installation: a game says whether it announces,
# not where to. Empty means nothing is announced anywhere, which is what a test host wants.
# The environment has the last word, and setting it empty is how a host says "nowhere". That is
# what the test suite does: it must not be able to reach a real channel through secret.py.
DISCORD_WEBHOOK = os.environ.get('DISCORD_MESSAGE_WEBHOOK',
                                 getattr(secret, 'DISCORD_MESSAGE_WEBHOOK', ''))

# Only a single process may write here: two preforked workers would both rename the file at
# rollover and one of them would keep writing to an unlinked inode. So the CLI logs to a file and
# the web application logs to stderr, which the host captures and rotates itself.
LOG_DIR = os.environ.get('LOG_DIR')
if (not LOG_DIR) and ('LOG_DIR' in dir(secret)):
    LOG_DIR = secret.LOG_DIR
if not LOG_DIR:
    LOG_DIR = 'logs'
if not os.path.isabs(LOG_DIR):
    LOG_DIR = os.path.join(REPO_ROOT, LOG_DIR)
LOG_FILE_NAME = "arena.log"
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')             # what a console is shown
LOG_FILE_LEVEL = os.environ.get('LOG_FILE_LEVEL', 'DEBUG')  # what the file keeps
LOG_FILE_BYTES = int(os.environ.get('LOG_FILE_BYTES', 1_000_000))
LOG_FILE_KEEP = int(os.environ.get('LOG_FILE_KEEP', 10))

MANUAL_FILENAME = os.path.join(REPO_ROOT, "starship-arena-manual.pdf")

# File and directory names wrt the game data root

GAME_DATA_DIR = os.environ.get('GAME_DATA_DIR')
if (not GAME_DATA_DIR) and ('GAME_DATA_DIR' in dir(secret)):
    GAME_DATA_DIR = secret.GAME_DATA_DIR
if not GAME_DATA_DIR:
    raise RuntimeError("No GAME_DATA_DIR, in the environment or in secret.py.")
# A relative setting means "inside the repository", so it survives being run from elsewhere.
if not os.path.isabs(GAME_DATA_DIR):
    GAME_DATA_DIR = os.path.join(REPO_ROOT, GAME_DATA_DIR)
logger.info(f"cfg.py: Loading game data from {GAME_DATA_DIR}")

ARCHIVE_DIR_NAME = "archived"
REGISTERING_DIR_NAME = "registering"
GAMES_DIR_NAME = "games"
SOLO_DIR_NAME = "solo-games"
VALHALLA_DIR_NAME = "valhalla"
PLAYERS_FILE_NAME = "players.jsonl"


# The data root itself is `GamesRoot`, in arena/engine/gamedirectory.py: it hands out game
# directories, which is more than a name and a path.

# File and directory names inside each game folder

STATUS_FILE_TEMPLATE = "status_round_{}.pickle"
COMMANDS_DIR = 'commands/'
READY_DIR = 'ready/'
READY_FILE_TEMPLATE = READY_DIR + "{}.txt"
READY_LINE_TEMPLATE = "Round {} Ready"
COMMAND_FILE_TEMPLATE = COMMANDS_DIR + "{}-commands-{}.txt"
INIT_FILE_NAME = "ships.jsonl"
BODIES_FILE_NAME = "bodies.jsonl"
SPAWN_FILE_NAME = "spawns.jsonl"
REGISTRATION_FILE_NAME = "registrations.jsonl"
SETTINGS_FILE_NAME = "settings.jsonl"
JOURNAL_FILE_NAME = "journal.jsonl"
SCENARIO_FILE_NAME = "scenario.json"
REPLAY_FILE_NAME = "replay.json"

# ============================================= SHIP CORE METRICS

MAX_SCAN_MULTIPLIER = 6


def max_scan(value):
    return int(value * MAX_SCAN_MULTIPLIER)
