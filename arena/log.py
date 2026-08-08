"""Where log output goes. See docs/development.md."""

import logging
import logging.handlers
import os

from arena.cfg import LOG_DIR, LOG_FILE_BYTES, LOG_FILE_KEEP, LOG_FILE_LEVEL, LOG_LEVEL

logger = logging.getLogger('starship-arena')
LOG_FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'
NOISY = ['fontTools']


def deactivate_logger_blocklist(logger_blocklist=()):
    """Libraries that log about their own internals at DEBUG."""
    for module in NOISY + list(logger_blocklist):
        logging.getLogger(module).setLevel(logging.ERROR)


def configure_logger(log_file: str = '', logger_blocklist=()):
    """Log to the console, and to a rotating file when one is named.

    Naming a file is for a single process only: preforked workers fight over the rollover."""
    logging.getLogger().setLevel(logging.ERROR)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler()
    console.setLevel(LOG_LEVEL)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file:
        os.makedirs(LOG_DIR, exist_ok=True)
        rotating = logging.handlers.RotatingFileHandler(os.path.join(LOG_DIR, log_file),
                                                        maxBytes=LOG_FILE_BYTES,
                                                        backupCount=LOG_FILE_KEEP)
        rotating.setLevel(LOG_FILE_LEVEL)
        rotating.setFormatter(formatter)
        logger.addHandler(rotating)

    deactivate_logger_blocklist(logger_blocklist)