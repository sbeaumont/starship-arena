import logging
from arena.log import deactivate_logger_blocklist

from arena.engine.round import GameRound
from arena.engine import setup_game
from arena.engine.gamedirectory import GameDirectory


def go():
    logging.basicConfig(level=logging.DEBUG)
    deactivate_logger_blocklist()
    gd = GameDirectory('./test/test-games', 'test-game')
    setup_game(gd)
    logger = logging.getLogger('starship-arena.test')

    for i in range(1, 3):
        logger.info("Starting game round %s", i)
        GameRound(gd, i).do_round()


if __name__ == '__main__':
    go()
