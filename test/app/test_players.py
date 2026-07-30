import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.players import PlayerRegistry, DIRECTOR


class TestPlayerRegistry(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.registry = PlayerRegistry(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_no_file_yet(self):
        self.assertEqual([], self.registry.all())
        self.assertIsNone(self.registry.by_token('anything'))

    def test_issue_and_resolve(self):
        issued = self.registry.issue('Menno')
        self.assertEqual('Menno', self.registry.by_token(issued.token).name)
        self.assertFalse(issued.is_director)

    def test_a_director_is_marked(self):
        self.registry.issue('Serge', role=DIRECTOR)
        self.assertTrue(self.registry.by_name('Serge').is_director)

    def test_issuing_again_replaces_the_token(self):
        first = self.registry.issue('Menno')
        second = self.registry.issue('Menno')
        self.assertNotEqual(first.token, second.token)
        self.assertIsNone(self.registry.by_token(first.token))
        self.assertEqual('Menno', self.registry.by_token(second.token).name)
        self.assertEqual(1, len(self.registry.all()))

    def test_revoke(self):
        issued = self.registry.issue('Menno')
        self.registry.revoke('Menno')
        self.assertIsNone(self.registry.by_token(issued.token))

    def test_survives_a_round_trip_through_the_file(self):
        self.registry.issue('Serge', role=DIRECTOR)
        self.registry.issue('Menno')
        reread = PlayerRegistry(self.root).all()
        self.assertEqual(['Menno', 'Serge'], [p.name for p in reread])
        self.assertEqual([False, True], [p.is_director for p in reread])

    def test_ignores_comments_and_the_header(self):
        with open(os.path.join(self.root, 'players.txt'), 'w') as f:
            f.write('Name   Token   Role\n# a note\nMenno  abc123\n')
        self.assertEqual(['Menno'], [p.name for p in self.registry.all()])
        self.assertEqual('Menno', self.registry.by_token('abc123').name)

    def test_a_file_without_the_column_reads_as_active(self):
        with open(os.path.join(self.root, 'players.txt'), 'w') as f:
            f.write('Name   Token   Role\nMenno  abc123\nSerge  def456  director\n')
        self.assertEqual([True, True], [p.active for p in self.registry.all()])

    def test_deactivating_keeps_the_name_and_closes_the_door(self):
        issued = self.registry.issue('Menno')
        self.registry.set_active('Menno', False)
        self.assertIsNone(self.registry.by_token(issued.token))
        self.assertFalse(self.registry.by_name('Menno').active)

    def test_reactivating_gives_the_same_token_back(self):
        issued = self.registry.issue('Menno')
        self.registry.set_active('Menno', False)
        self.registry.set_active('Menno', True)
        self.assertEqual('Menno', self.registry.by_token(issued.token).name)

    def test_a_new_link_does_not_reactivate(self):
        self.registry.issue('Menno')
        self.registry.set_active('Menno', False)
        again = self.registry.issue('Menno')
        self.assertIsNone(self.registry.by_token(again.token))

    def test_deactivating_a_stranger_says_so(self):
        with self.assertRaises(ValueError):
            self.registry.set_active('Nobody', False)

    def test_a_name_with_spaces_is_stored_without_them(self):
        issued = self.registry.issue('Serge Beaumont')
        self.assertEqual('Serge_Beaumont', issued.name)
        self.assertEqual('Serge_Beaumont', self.registry.by_token(issued.token).name)
        self.assertIsNotNone(self.registry.by_name('Serge Beaumont'))

    def test_issuing_again_under_the_spaced_name_replaces_the_same_row(self):
        self.registry.issue('Serge Beaumont')
        self.registry.issue('Serge_Beaumont')
        self.assertEqual(1, len(self.registry.all()))