"""The escort scenario: what it deals, where it puts everyone, and what the jump point notices."""
import random
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from arena.app.registrations import Registration
from arena.app.scenarios.vip_escort import (BEACON_NAME, ESCORT_BAND, ESCORT_X, HEIGHT, ROCKS,
                                            ROCKS_APART, SPREAD, THIRD, VIP_HULL, VIP_NAME,
                                            VipEscort, WIDTH)
from arena.app.services import AdminService, GameService
from arena.engine.objects.event import ArrivalEvent
from arena.engine.objects.registry import builder
from arena.engine.world import World
from arena.engine.gamedirectory import GameDirectory

FOUR = [Registration(player='Rik', names=['Voyager', 'Pathfinder'], faction='Escort'),
        Registration(player='Menno', names=['Rocinante'], faction='Escort'),
        Registration(player='Ilona', names=['Nauvoo'], faction='Hunters'),
        Registration(player='Dennis', names=['Tachi'], faction='Hunters')]


class TestWhatItDeals(TestCase):
    def setUp(self):
        self.scenario = VipEscort()
        self.roster = self.scenario.deal(FOUR, random.Random(1))

    def test_everybody_flies_what_they_registered(self):
        self.assertEqual({'Voyager', 'Pathfinder', 'Rocinante', 'Nauvoo', 'Tachi', VIP_NAME},
                         {s['name'] for s in self.roster})

    def test_the_vip_joins_the_escort_under_the_smallest_fleet(self):
        vip = next(s for s in self.roster if s['name'] == VIP_NAME)
        self.assertEqual(VIP_HULL, vip['type'])
        self.assertEqual('Escort', vip['faction'])
        self.assertEqual('Menno', vip['player'])

    def test_nobody_else_is_handed_the_vip_hull(self):
        others = [s for s in self.roster if s['name'] != VIP_NAME]
        self.assertNotIn(VIP_HULL, {s['type'] for s in others})

    def test_an_escort_is_required(self):
        hunters = [Registration(player='Ilona', names=['Nauvoo'], faction='Hunters')]
        with self.assertRaises(ValueError):
            self.scenario.deal(hunters, random.Random(1))


class TestWhereItPutsThem(TestCase):
    def setUp(self):
        self.scenario = VipEscort()
        self.placed = self.scenario.place(self.scenario.deal(FOUR, random.Random(1)),
                                          random.Random(2))

    def spots(self, faction):
        return [(s['x'], s['y']) for s in self.placed if s['faction'] == faction]

    def test_the_escort_starts_along_the_western_edge(self):
        for x, y in self.spots('Escort'):
            self.assertAlmostEqual(ESCORT_X, x, delta=SPREAD)

    def test_no_two_of_the_escort_share_a_band(self):
        """Strung out, so finding one hull says nothing about where the rest of them are."""
        ys = sorted(y for x, y in self.spots('Escort'))
        band = ESCORT_BAND / len(ys)
        for lower, higher in zip(ys, ys[1:]):
            self.assertGreater(higher - lower, 0)
        self.assertGreater(ys[-1] - ys[0], band)

    def test_the_hunters_start_together_in_the_middle(self):
        for x, y in self.spots('Hunters'):
            self.assertAlmostEqual(0, x, delta=SPREAD)

    def test_which_band_the_vip_is_in_is_a_fresh_draw(self):
        roster = self.scenario.deal(FOUR, random.Random(1))
        vip_y = {next(s['y'] for s in self.scenario.place(roster, random.Random(seed))
                      if s['name'] == VIP_NAME)
                 for seed in range(20)}
        self.assertGreater(len(vip_y), 10)


class TestTheField(TestCase):
    def setUp(self):
        self.bodies = VipEscort().bodies(random.Random(3))

    def test_it_is_rocks_and_one_way_out(self):
        self.assertEqual(ROCKS + 1, len(self.bodies))
        self.assertEqual(1, len([b for b in self.bodies if b['name'] == BEACON_NAME]))

    def test_the_way_out_is_in_the_east_third(self):
        beacon = next(b for b in self.bodies if b['name'] == BEACON_NAME)
        self.assertGreater(beacon['x'], THIRD / 2)
        self.assertLess(beacon['x'], WIDTH / 2)
        self.assertLess(abs(beacon['y']), HEIGHT / 2)

    def test_no_two_rocks_are_closer_than_the_spacing(self):
        spots = [(b['x'], b['y']) for b in self.bodies if b['name'] != BEACON_NAME]
        for n, (x, y) in enumerate(spots):
            for other_x, other_y in spots[n + 1:]:
                self.assertGreater((x - other_x) ** 2 + (y - other_y) ** 2, ROCKS_APART ** 2)


class TestDocking(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def world_with(self, *objects):
        return World(GameDirectory(str(self.root), 'none'), {o.name: o for o in objects})

    def arrivals(self, ois):
        return [e for e in ois.history.current.events if isinstance(e, ArrivalEvent)]

    def test_coming_alongside_slowly_is_an_arrival(self):
        beacon = builder.create('Gate', 'JumpPoint', (0, 0))
        vip = builder.create(VIP_NAME, VIP_HULL, (5, 0))
        vip.speed = 5
        world = self.world_with(beacon, vip)
        beacon.post_move(world)

        self.assertEqual(1, len(self.arrivals(beacon)))
        self.assertEqual(vip, self.arrivals(beacon)[0].ship)
        self.assertEqual(1, len(self.arrivals(vip)))
        self.assertEqual({VIP_NAME}, beacon.docked)

    def test_staying_alongside_is_not_a_second_arrival(self):
        """Ten ticks parked at it would otherwise be ten lines in the log."""
        beacon = builder.create('Gate', 'JumpPoint', (0, 0))
        vip = builder.create(VIP_NAME, VIP_HULL, (5, 0))
        world = self.world_with(beacon, vip)
        for _ in range(10):
            beacon.post_move(world)

        self.assertEqual(1, len(self.arrivals(beacon)))

    def test_flying_past_at_speed_is_not(self):
        beacon = builder.create('Gate', 'JumpPoint', (0, 0))
        vip = builder.create(VIP_NAME, VIP_HULL, (5, 0))
        vip.speed = 30
        world = self.world_with(beacon, vip)
        beacon.post_move(world)

        self.assertEqual([], self.arrivals(beacon))

    def test_being_near_enough_is_not_the_same_as_alongside(self):
        beacon = builder.create('Gate', 'JumpPoint', (0, 0))
        vip = builder.create(VIP_NAME, VIP_HULL, (40, 0))
        world = self.world_with(beacon, vip)
        beacon.post_move(world)

        self.assertEqual([], self.arrivals(beacon))

    def test_it_cannot_be_destroyed_or_shoved(self):
        beacon = builder.create('Gate', 'JumpPoint', (0, 0))
        vip = builder.create(VIP_NAME, VIP_HULL, (5, 0))

        self.assertFalse(beacon.is_destroyed)
        self.assertIsNone(beacon.impulse_on(vip, 1))


class TestWhenItIsOver(TestCase):
    """The scenario's own verdict, on a world it is handed."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.scenario = VipEscort()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def world(self):
        beacon = builder.create('Jump Point', 'JumpPoint', (0, 0))
        vip = builder.create(VIP_NAME, VIP_HULL, (500, 0), player='Menno')
        vip.faction = 'Escort'
        guard = builder.create('Kestrel', 'H2545', (400, 0), player='Rik')
        guard.faction = 'Escort'
        hunter = builder.create('Tachi', 'R2531', (-400, 0), player='Ilona')
        hunter.faction = 'Hunters'
        return World(GameDirectory(str(self.root), 'none'),
                     {o.name: o for o in (beacon, vip, guard, hunter)})

    def test_a_game_in_progress_has_no_outcome(self):
        self.assertIsNone(self.scenario.outcome(self.world()))

    def test_docking_wins_it_for_the_escort(self):
        world = self.world()
        world.objects['Jump Point'].docked.add(VIP_NAME)
        outcome = self.scenario.outcome(world)

        self.assertEqual('Escort', outcome.faction)
        self.assertIn('Jump Point', outcome.reason)
        self.assertEqual({'Menno': 250, 'Rik': 250}, outcome.points)

    def test_killing_the_vip_wins_it_for_the_hunters(self):
        world = self.world()
        world.objects[VIP_NAME].hull = 0
        outcome = self.scenario.outcome(world)

        self.assertEqual('Hunters', outcome.faction)
        self.assertEqual({'Ilona': 500}, outcome.points)

    def test_a_dead_vip_in_the_graveyard_still_ends_it(self):
        world = self.world()
        vip = world.objects[VIP_NAME]
        vip.hull = 0
        world.move_to_graveyard(vip)

        self.assertEqual('Hunters', self.scenario.outcome(world).faction)


class TestAGameOfIt(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.admin = AdminService(str(self.root))
        self.game = GameService(str(self.root))
        for entry in FOUR:
            self.admin.issue_login(entry.player)
        self.admin.open_registrations('run', 'vip-escort')
        for entry in FOUR:
            self.admin.register('run', entry.player, entry.names)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def start(self):
        self.roster = VipEscort().deal(self.admin.registrations('run'), random.Random(1))
        self.admin.start_game('run', self.roster, self.admin.settings('run'))

    def someone_in(self, faction: str) -> str:
        """Whoever the deal actually put there. Registering says nothing about which side."""
        return next(s['player'] for s in self.roster
                    if s['faction'] == faction and s.get('player'))

    def play_a_round(self):
        for ship in self.game.list_ships('run'):
            self.game.save_commands('run', ship, ['1: A10'])
        self.admin.process_turn('run')

    def test_the_escort_is_briefed_on_the_way_out_and_the_hunters_are_not(self):
        self.start()
        self.play_a_round()
        escort, hunter = self.someone_in('Escort'), self.someone_in('Hunters')

        self.assertIn(BEACON_NAME,
                      {c.name for c in self.game.get_player_plan('run', escort).contacts})
        self.assertNotIn(BEACON_NAME,
                         {c.name for c in self.game.get_player_plan('run', hunter).contacts})

    def test_it_sets_up_and_plays_a_round(self):
        self.start()
        self.play_a_round()

        self.assertEqual(1, self.admin.game_overview('run').last_round)
        self.assertEqual('vip-escort', self.admin.scenario_of('run'))
        self.assertIsNone(self.admin.outcome('run'))
        self.assertEqual(['run'], [g.name for g in self.admin.list_games()])

    def test_the_round_that_kills_the_vip_closes_the_game(self):
        self.start()
        gd = self.admin._gd('run')
        world = gd.load_current_world()
        world.objects[VIP_NAME].hull = 0
        world.save(0)
        self.play_a_round()

        outcome = self.admin.outcome('run')
        self.assertEqual('Hunters', outcome.faction)
        self.assertEqual(500, sum(outcome.points.values()))
        self.assertEqual([], self.admin.list_games())
        self.assertEqual(['run'], [g.name for g in self.admin.list_finished_games()])

    def test_a_closed_game_takes_no_more_orders(self):
        self.start()
        gd = self.admin._gd('run')
        world = gd.load_current_world()
        world.objects[VIP_NAME].hull = 0
        world.save(0)
        self.play_a_round()

        with self.assertRaises(ValueError):
            self.game.save_commands('run', VIP_NAME, ['1: A10'])
        with self.assertRaises(ValueError):
            self.admin.process_turn('run')

    def test_the_journal_says_why_it_ended(self):
        self.start()
        gd = self.admin._gd('run')
        world = gd.load_current_world()
        world.objects[VIP_NAME].hull = 0
        world.save(0)
        self.play_a_round()

        finished = [e for e in self.admin.journal('run') if e.event == 'finished']
        self.assertEqual(1, len(finished))
        self.assertEqual('Hunters', finished[0].detail['faction'])