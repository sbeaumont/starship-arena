import logging

from arena_engine.round import GameRound
from arena_engine.admin import setup_game
from arena_engine.gamedirectory import GameDirectory


def go():
    gd = GameDirectory('./test/test-games', 'test-game')
    setup_game(gd)
    logger = logging.getLogger('starship-arena.test')

    for i in range(1, 8):
        logger.info("Starting game round %s", i)
        GameRound(gd, i).do_round()


if __name__ == '__main__':
    go()
