import locale
import logging


locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')
logger = logging.getLogger('starship-arena')
LOG_FILE_NAME = "./logfile.txt"
FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(name)s %(levelname)s: %(message)s'


def deactivate_logger_blocklist(logger_blocklist=list()):
    logger_blocklist.append('fontTools')
    # Silence library logging
    for module in logger_blocklist:
        logging.getLogger(module).setLevel(logging.ERROR)


def configure_logger(create_log_file=False, logger_blocklist=list()):
    """Configure the file and console logging."""
    logging.getLogger().setLevel(logging.ERROR)

    logger.setLevel(FILE_LOG_LEVEL)
    formatter = logging.Formatter(LOG_FORMAT)

    if create_log_file:
        # create file handler
        fh = logging.FileHandler(LOG_FILE_NAME, 'w')
        fh.setLevel(FILE_LOG_LEVEL)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # create console handler with its own log level
    ch = logging.StreamHandler()
    ch.setLevel(CONSOLE_LOG_LEVEL)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    deactivate_logger_blocklist(logger_blocklist)
