from unittest import TestCase

from arena.engine.history import TICK_ZERO, Tick
from arena.engine.objects.geometry import Point, Vector
from arena.engine.objects.objectinspace import Stance
from arena.engine.objects.registry import builder
from arena.engine.objects.registry.bodies import Asteroid
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine.objects.registry.missiles import Rocket, Splinter
from arena.engine.round import GameRound

from .ois_fixtures import run_ticks, world_of


def asteroid(name='Rock', at=(0, 0)):
    return Asteroid().create(name, Vector(Point(*at), heading=0, speed=0))


class TestBody(TestCase):
    """Terrain: it takes up space, it stays put, and nothing kills it."""

    def setUp(self):
        self.rock = asteroid()

    def test_it_has_a_radius_where_everything_else_is_a_point(self):
        self.assertEqual(40, self.rock.radius)
        self.assertEqual(0, builder.create("Ship", "H2545", (0, 0)).radius)

    def test_it_is_immovable_and_a_ship_is_not(self):
        self.assertTrue(self.rock.is_immovable)
        self.assertFalse(builder.create("Ship", "H2545", (0, 0)).is_immovable)

    def test_it_cannot_be_destroyed(self):
        self.assertFalse(self.rock.is_destroyed)

    def test_it_stays_where_it_is(self):
        self.rock.vector = Vector(Point(0, 0), heading=90, speed=60)
        self.rock.move()
        self.assertEqual(Point(0.0, 0.0), self.rock.pos, "even told to move at 60")

    def test_it_says_what_it_is(self):
        self.assertEqual('Asteroid', self.rock.type_name)
        self.assertEqual('Terrain', self.rock.category_name)

    def test_it_belongs_to_no_faction(self):
        self.assertIsNone(self.rock.faction)
        self.assertIsNone(self.rock.owner.faction, "owns itself, so asking its owner works")

    def test_a_scanner_reaches_further_against_it(self):
        """The other end of a cloak. Nobody is ambushed by terrain."""
        self.assertEqual(540, self.rock.modify_scan_range(180), "three times an H2545's 180")
        self.assertEqual(180, builder.create("Ship", "H2545", (0, 0)).modify_scan_range(180))

    def test_the_snapshot_carries_the_radius(self):
        """So a map draws the real size rather than a number kept in the browser."""
        self.assertEqual(40, self.rock.snapshot['radius'])


class TestTerrainIsNobodysEnemy(TestCase):
    """A rock is on no side, so nothing shoots at it and nothing goes off near it."""

    def setUp(self):
        self.shooter = builder.create("Shooter", "H2545", (0, 0))
        self.shooter.faction = 'One'
        self.rock = asteroid('Rock', (100, 0))

    def _rocket_heading_east(self, world, y=0):
        rocket = Rocket().create("R", Vector(Point(0, y), heading=90, speed=0), owner=self.shooter)
        world.add(rocket)
        return rocket

    def test_a_warhead_does_not_trigger_on_it(self):
        """Clear of the rock by 20, so nothing was reached and nothing set it off."""
        world = world_of({'Shooter': self.shooter, 'Rock': self.rock})
        rocket = self._rocket_heading_east(world, y=60)

        run_ticks(world, 2)

        self.assertFalse(rocket.is_destroyed)
        self.assertEqual(Point(120.0, 60.0), rocket.pos)

    def test_running_into_one_is_what_sets_it_off(self):
        """Not a proximity trigger: it is stopped at the surface and the impact finishes it."""
        world = world_of({'Shooter': self.shooter, 'Rock': self.rock})
        rocket = self._rocket_heading_east(world)

        run_ticks(world, 2)

        self.assertTrue(rocket.is_destroyed)
        self.assertEqual(self.rock.radius, rocket.distance_to(self.rock.xy), "stopped on the surface")

    def test_a_guided_missile_does_not_track_it(self):
        world = world_of({'Shooter': self.shooter, 'Rock': self.rock})
        splinter = Splinter().create("S", Vector(Point(0, 0), heading=90, speed=0),
                                     owner=self.shooter)
        world.add(splinter)

        splinter.scan(world)

        self.assertIsNone(splinter.target, "a rock is terrain, not a target")

    def test_it_still_goes_off_on_an_enemy(self):
        """The rock has not made the warhead deaf, it has made it choosy."""
        enemy = builder.create("Enemy", "H2545", (100, 60))
        enemy.faction = 'Two'
        world = world_of({'Shooter': self.shooter, 'Rock': self.rock, 'Enemy': enemy})
        rocket = self._rocket_heading_east(world, y=60)

        run_ticks(world, 2)

        self.assertTrue(rocket.is_destroyed)


class TestStance(TestCase):
    """Friend, Foe, Neutral."""

    def setUp(self):
        self.ours = builder.create("Ours", "H2545", (0, 0))
        self.ours.faction = 'One'
        self.theirs = builder.create("Theirs", "H2545", (0, 0))
        self.theirs.faction = 'Two'
        self.ally = builder.create("Ally", "H2545", (0, 0))
        self.ally.faction = 'One'
        self.rock = asteroid()

    def test_the_three_answers(self):
        self.assertEqual(Stance.Foe, self.theirs.stance_towards(self.ours))
        self.assertEqual(Stance.Friend, self.ally.stance_towards(self.ours))
        self.assertEqual(Stance.Neutral, self.rock.stance_towards(self.ours))

    def test_it_reads_the_same_from_either_end(self):
        self.assertEqual(Stance.Neutral, self.ours.stance_towards(self.rock))

    def test_a_thing_is_its_own_friend(self):
        """Which is what keeps a warhead from going off on the launcher that fired it."""
        self.assertEqual(Stance.Friend, self.ours.stance_towards(self.ours))

    def test_what_a_ship_launches_takes_its_side(self):
        rocket = Rocket().create("R", Vector(Point(0, 0), heading=0, speed=0), owner=self.ours)
        self.assertEqual(Stance.Foe, self.theirs.stance_towards(rocket))
        self.assertEqual(Stance.Friend, self.ally.stance_towards(rocket))


class TestRunningIntoOne(TestCase):
    """A rock at (200, 0) with a radius of 40, so its surface faces west at x = 160."""

    def _run(self, objects, ticks=2):
        world = world_of(objects)
        game_round = GameRound(world, 1)
        for tick in Tick.for_start_of_round(1).ticks_for_round[:ticks]:
            game_round.do_tick(tick)
        return world

    def _ship(self, y, speed=45):
        ship = builder.create("S", "H2545", (100, y), player='Rik')
        ship.faction = 'One'
        ship.vector = Vector(Point(100, y), heading=90, speed=speed)
        return ship

    def test_head_on_it_comes_back_at_a_third(self):
        ship = self._ship(0)
        bow = ship.defense[0].max_strengths['N']
        self._run({'Rock': asteroid('Rock', (200, 0)), 'S': ship})

        self.assertEqual(270.0, ship.heading, "turned right around")
        self.assertEqual(13.5, ship.speed, "45 at a restitution of 0.3")
        self.assertEqual(bow - 45, ship.defense[0].strengths['N'], "struck on the bow at 45")

    def test_a_graze_barely_costs_anything(self):
        """The travel along the surface is kept, and only what drove into it is turned around."""
        ship = self._ship(38)
        bow = ship.defense[0].max_strengths['N']
        self._run({'Rock': asteroid('Rock', (200, 0)), 'S': ship})

        self.assertEqual(43.0, ship.speed, "45, near enough")
        self.assertEqual(66.2, ship.heading, "nudged off 90")
        self.assertEqual(bow, ship.defense[0].strengths['N'], "nothing on the bow")

    def test_it_spends_what_is_left_of_the_tick_on_the_new_course(self):
        """Stopping dead at the surface would cost a graze almost a whole tick of travel."""
        ship = self._ship(38)
        world = self._run({'Rock': asteroid('Rock', (200, 0)), 'S': ship})

        self.assertNotEqual(Point(187.5, 38.0), ship.pos, "not parked at the contact point")
        self.assertGreater(ship.pos.x, 188)

    def test_a_drifting_mine_settles_against_it(self):
        owner = builder.create("Layer", "H2545", (0, 0), player='Rik')
        owner.faction = 'One'
        mine = SplinterMine().create('M', Vector(Point(155, 0), heading=90, speed=13), owner=owner)
        self._run({'Rock': asteroid('Rock', (200, 0)), 'Layer': owner, 'M': mine}, ticks=1)

        self.assertFalse(mine.is_destroyed, "hull absorbed the tap")
        self.assertEqual(Point(160.0, 0.0), mine.pos, "resting on the surface")

    def test_a_mine_still_travelling_goes_off_on_it(self):
        owner = builder.create("Layer", "H2545", (0, 0), player='Rik')
        owner.faction = 'One'
        mine = SplinterMine().create('M', Vector(Point(155, 0), heading=90, speed=45), owner=owner)
        self._run({'Rock': asteroid('Rock', (200, 0)), 'Layer': owner, 'M': mine}, ticks=1)

        self.assertTrue(mine.is_destroyed, "too fast for the casing")

    def test_terrain_is_not_shoved_by_what_hits_it(self):
        rock = asteroid('Rock', (200, 0))
        self._run({'Rock': rock, 'S': self._ship(0)})

        self.assertEqual(Point(200.0, 0.0), rock.pos)


class TestBodyInARound(TestCase):
    """A body sits in world.objects like anything else, so every phase has to survive it."""

    def test_a_round_runs_with_terrain_in_it(self):
        ships = {'Blaster': builder.create("Blaster", "H2545", (0, 0), player='Rik')}
        ships['Blaster'].faction = 'One'
        ships['Rock'] = asteroid('Rock', (300, 0))
        world = world_of(ships)

        game_round = GameRound(world, 1)
        for tick in Tick.for_start_of_round(1).ticks_for_round:
            game_round.do_tick(tick)

        self.assertIn('Rock', world.objects, "terrain is never reaped")
        self.assertEqual(Point(300.0, 0.0), world.objects['Rock'].pos)


class TestBodyRegistry(TestCase):
    """Bodies are a family of their own, so nothing asking for ships gets one."""

    def test_asteroid_is_a_body_type_and_not_a_ship_type(self):
        self.assertIn('Asteroid', builder.all_body_types)
        self.assertNotIn('Asteroid', builder.all_ship_types)
        self.assertNotIn('Asteroid', builder.all_starbase_types)
        self.assertNotIn('Asteroid', builder.all_fielded_types)

    def test_it_can_still_be_looked_up_by_name(self):
        self.assertIn('Asteroid', builder.all_types)
        rock = builder.spawn('Asteroid', 'Rock', Vector(Point(0, 0), heading=0, speed=0))
        self.assertEqual(40, rock.radius)

    def test_the_roots_themselves_are_not_models(self):
        self.assertNotIn('BodyType', builder.all_body_types)
        self.assertNotIn('StarbaseType', builder.all_ship_types)
