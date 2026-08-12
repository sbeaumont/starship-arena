"""Damage travels inwards along the defence components, and every layer answers the same way."""
from unittest import TestCase

from arena.engine.objects.components.defense import Shields
from arena.engine.objects.event import DamageType, HitEvent, Outcome
from arena.engine.objects.registry.builder import create
from arena.engine.objects.ship import BATTERY, HULL

FULL_SHIELD = 90   # what an A2527 carries on each quadrant


def struck(target, damage, damage_type=DamageType.Laser, faction='Two'):
    """Lasered from due south, so the blow lands on the target's aft quadrant."""
    shooter = create('Blaster', 'H2545', (0, 0))
    shooter.faction = 'One'
    target.faction = faction
    hit = HitEvent(target.pos, damage_type, shooter, target, damage)
    target.take_damage_from(hit)
    return hit


def a_ship(name='Shaper'):
    return create(name, 'A2527', (0, 100))


class TestALayerAnswersForItself(TestCase):
    def test_a_shield_that_holds(self):
        hit = struck(a_ship(), 60)
        self.assertEqual([('Shields', Outcome.Damaged, 60, 30, 0)],
                         [(e.part, e.outcome, e.amount, e.points, e.passed_on) for e in hit.effects])

    def test_a_shield_that_is_breached_hands_on_what_is_left(self):
        hit = struck(a_ship(), 150)
        shield, hull = hit.effects[0], hit.effects[1]
        self.assertEqual((Outcome.Breached, FULL_SHIELD, 150 - FULL_SHIELD),
                         (shield.outcome, shield.amount, shield.passed_on))
        self.assertEqual((HULL, Outcome.Damaged, 60), (hull.part, hull.outcome, hull.amount))

    def test_the_hull_is_the_last_layer_and_breaching_it_is_the_end(self):
        target = a_ship()
        hit = struck(target, 400)
        self.assertTrue(target.is_destroyed)
        self.assertEqual([Outcome.Breached, Outcome.Damaged, Outcome.Breached],
                         [e.outcome for e in hit.effects])
        self.assertEqual([Outcome.Breached], [e.outcome for e in hit.effects if e.part == HULL
                                              and e.amount == 0])

    def test_an_emp_reaches_the_battery_rather_than_the_hull(self):
        target = a_ship()
        hit = struck(target, 400, DamageType.EMP)
        self.assertIn(BATTERY, [e.part for e in hit.effects])
        self.assertFalse(target.is_destroyed)

    def test_nanocytes_do_nothing_at_all_to_a_live_shield(self):
        hit = struck(a_ship(), 30, DamageType.Nanocyte)
        self.assertEqual([(Outcome.Unaffected, 0, 0)],
                         [(e.outcome, e.amount, e.passed_on) for e in hit.effects])

    def test_a_downed_shield_passes_everything_through(self):
        target = a_ship()
        for quadrant in target.defense[0].strengths:
            target.defense[0].strengths[quadrant] = 0
        hit = struck(target, 40)
        shield, hull = hit.effects[0], hit.effects[1]
        self.assertEqual((Outcome.Unaffected, 40), (shield.outcome, shield.passed_on))
        self.assertEqual((HULL, 40), (hull.part, hull.amount))


class TestTwoLayersOfDefence(TestCase):
    """What armour behind a shield will do. Nothing in the registry carries two yet."""

    def setUp(self):
        self.target = a_ship()
        armour = Shields('Armour', {'N': 50, 'E': 50, 'S': 50, 'W': 50})
        armour.attach(self.target)
        self.target.defense.append(armour)
        self.target.all_components[armour.name] = armour

    def test_the_second_layer_takes_only_what_got_past_the_first(self):
        hit = struck(self.target, 130)
        shield, armour = hit.effects[0], hit.effects[1]
        self.assertEqual((Outcome.Breached, FULL_SHIELD, 40),
                         (shield.outcome, shield.amount, shield.passed_on))
        # 40 reached the armour, not the original 130, and 50 of armour holds that.
        self.assertEqual(('Armour', Outcome.Damaged, 40, 0),
                         (armour.part, armour.outcome, armour.amount, armour.passed_on))
        self.assertEqual(2, len(hit.effects))

    def test_the_hull_is_reached_only_once_both_are_through(self):
        hit = struck(self.target, 200)
        self.assertEqual(['Shields', 'Armour', HULL], [e.part for e in hit.effects])
        self.assertEqual(200 - FULL_SHIELD - 50, hit.effects[2].amount)


class TestScoringFollowsTheEffects(TestCase):
    def test_the_score_is_the_sum_of_what_each_layer_granted(self):
        hit = struck(a_ship(), 400)
        self.assertEqual(sum(e.points for e in hit.effects), hit.score)
        self.assertEqual(275, hit.score)   # 45 shield + 25 break + 105 hull + 100 kill

    def test_hitting_your_own_faction_still_reports_but_scores_nothing(self):
        hit = struck(a_ship(), 400, faction='One')
        self.assertEqual(0, hit.score)
        self.assertIn(Outcome.Breached, [e.outcome for e in hit.effects])