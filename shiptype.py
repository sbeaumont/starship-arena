from weapon import Laser, RocketLauncher


class Splinter(object):
    max_speed = 60
    explode_distance = 6
    explode_damage = 10
    scan_distance = 150
    scan_cone = 45
    max_battery = 125
    hull = 1


class H2545(object):
    max_delta_v = 25
    max_speed = 45
    max_turn = 35
    generators = 8
    max_battery = 500
    start_battery = 125
    hull = 100

    @property
    def shields(self):
        return {'N': 150, 'E': 100, 'S': 130, 'W': 100}

    @property
    def weapons(self):
        return {
            'Laser1': Laser('Laser1'),
            'Launcher1': RocketLauncher('Launcher1', Splinter())
        }
