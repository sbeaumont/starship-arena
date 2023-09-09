import logging

from engine.round import GameRound
from engine.admin import setup_game


def go():
    gd = setup_game('test-game', './test-games')
    logger = logging.getLogger('starship-arena.test')

    for i in range(1, 2):
        logger.info("Starting game round %s", i)
        GameRound(gd, i).do_round()


if __name__ == '__main__':
    go()
