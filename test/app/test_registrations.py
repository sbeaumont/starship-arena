"""Putting yourself down for a game that has not started."""
import shutil
import tempfile
from unittest import TestCase

from arena.app.registrations import RegistrationFile


class TestRegistrationFile(TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.file = RegistrationFile(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_nothing_registered_yet(self):
        self.assertEqual([], self.file.all())
        self.assertIsNone(self.file.of('Rik'))

    def test_registering_and_reading_back(self):
        self.file.put('Rik', ['Voyager', 'Pathfinder'], max_ships=3)
        mine = RegistrationFile(self.dir).of('Rik')
        self.assertEqual(['Voyager', 'Pathfinder'], mine.names)
        self.assertEqual(2, mine.ships)

    def test_registering_again_replaces_your_own_line(self):
        self.file.put('Rik', ['Voyager'], max_ships=3)
        self.file.put('Menno', ['Rocinante'], max_ships=3)
        self.file.put('Rik', ['Endeavour', 'Discovery'], max_ships=3)
        self.assertEqual(2, len(self.file.all()))
        self.assertEqual(['Discovery', 'Endeavour'], sorted(self.file.of('Rik').names))
        self.assertEqual(['Rocinante'], self.file.of('Menno').names)

    def test_more_ships_than_allowed_is_refused(self):
        with self.assertRaises(ValueError):
            self.file.put('Rik', ['A', 'B', 'C', 'D'], max_ships=3)

    def test_the_limit_is_the_caller_s_to_set(self):
        self.file.put('Rik', ['A', 'B', 'C', 'D', 'E'], max_ships=5)
        self.assertEqual(5, self.file.of('Rik').ships)

    def test_no_ships_is_refused(self):
        with self.assertRaises(ValueError):
            self.file.put('Rik', [], max_ships=3)

    def test_two_of_your_own_ships_named_the_same(self):
        with self.assertRaises(ValueError):
            self.file.put('Rik', ['Voyager', 'Voyager'], max_ships=3)

    def test_a_name_somebody_else_took(self):
        self.file.put('Menno', ['Voyager'], max_ships=3)
        with self.assertRaises(ValueError) as raised:
            self.file.put('Rik', ['Voyager'], max_ships=3)
        self.assertIn('Voyager', str(raised.exception))

    def test_keeping_your_own_names_when_you_change_your_mind(self):
        self.file.put('Rik', ['Voyager'], max_ships=3)
        self.file.put('Rik', ['Voyager', 'Pathfinder'], max_ships=3)
        self.assertEqual(2, self.file.of('Rik').ships)

    def test_withdrawing(self):
        self.file.put('Rik', ['Voyager'], max_ships=3)
        self.file.put('Menno', ['Rocinante'], max_ships=3)
        self.file.remove('Rik')
        self.assertEqual(['Menno'], [e.player for e in self.file.all()])

    def test_a_line_that_will_not_parse_names_itself(self):
        self.file.put('Rik', ['Voyager'], max_ships=3)
        with open(self.file.path, 'a') as f:
            f.write('not json\n')
        with self.assertRaises(ValueError) as raised:
            self.file.all()
        self.assertIn('line 2', str(raised.exception))