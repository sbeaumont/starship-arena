from ois.comp.warhead import RocketWarhead, SplinterWarhead, NanocyteWarhead, PowerSplinterWarhead, EMPWarhead
from ois.missile import MissileType, Missile, GuidedMissile


class Rocket(MissileType):
    """Dumb rocket"""
    base_type = Missile
    max_speed = 60
    explode_distance = 20
    explode_damage = 50
    max_battery = 75
    start_battery = 75
    max_hull = 1
    scan_cone = 0
    max_scan_distance = 20

    @property
    def weapons(self):
        return [
            RocketWarhead('warhead'),
        ]


class Splinter(MissileType):
    """The basic guided missile"""
    base_type = GuidedMissile
    max_speed = 60
    explode_distance = 6
    explode_damage = 75
    max_battery = 75
    start_battery = 75
    max_hull = 1
    scan_cone = 45
    max_scan_distance = 150

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
        ]


class PowerSplinter(Splinter):
    @property
    def weapons(self):
        return [
            PowerSplinterWarhead('warhead'),
        ]


class NanoMissile(MissileType):
    """Guided missile with a nano warhead"""
    base_type = GuidedMissile
    max_speed = 60
    explode_distance = 6
    explode_damage = 50
    max_battery = 75
    start_battery = 75
    max_hull = 1
    scan_cone = 45
    max_scan_distance = 150

    @property
    def weapons(self):
        return [
            NanocyteWarhead('warhead'),
        ]


class EMPMissile(MissileType):
    """EMP missile. Drains shields and battery."""
    base_type = GuidedMissile
    max_speed = 50
    explode_distance = 20
    explode_damage = 50
    max_battery = 75
    start_battery = 75
    max_hull = 1
    scan_cone = 45
    max_scan_distance = 150

    @property
    def weapons(self):
        return [
            EMPWarhead('warhead'),
        ]


