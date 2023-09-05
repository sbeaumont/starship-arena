import logging

from engine.gamedirectory import GameDirectory
from engine.admin import GameSetup, group_by_faction
from engine.round import GameRound
from log import configure_logger


def go():
    logging.getLogger().setLevel(logging.ERROR)
    configure_logger(logger_blocklist=('fonttools',))
    logger = logging.getLogger('starship-arena')
    gd = GameDirectory('./test-games', 'test-game')
    gd.clean()
    setup = GameSetup(gd)
    setup.run()

    for faction, ships in group_by_faction(setup.ships.values()).items():
        print("==", faction, "==")
        for ship in ships:
            print(ship.name, ship.faction, ship.pos, ship.type_name)
    setup.report()
    setup.save()
    logger.info("Current status: %s", gd.load_current_status())

    for i in range(1, 4):
        logger.info("Starting game round %s", i)
        GameRound(gd, i).do_round()


if __name__ == '__main__':
    go()
