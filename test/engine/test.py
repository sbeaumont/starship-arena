import logging
from arena.log import deactivate_logger_blocklist

from arena.engine.admin import setup_game
from arena.engine.gamedirectory import GameDirectory

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('starship-arena.test')
deactivate_logger_blocklist()

def go():
    gd = GameDirectory('./test/test-games', 'test-game')
    game = setup_game(gd)

    for i in range(3):
        logger.info("Starting game round %s", game.round_nr)
        if game.round_ready:
            game.do_round()
        else:
            break
        game.init_next_round()


if __name__ == '__main__':
    go()
