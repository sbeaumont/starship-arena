from engine.gamedirectory import GameDirectory
from engine.admin import GameSetup, group_by_faction
from engine.round import GameRound


def go():
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
    print("Current status:", gd.load_current_status())

    round_1 = GameRound(gd, 1)
    round_1.do_round()
    round_2 = GameRound(gd, 2)
    round_2.do_round()


if __name__ == '__main__':
    go()
