"""
Tests for core/services/gamification.py: points calculation, streak
tracking, and achievement milestones — the previously deferred item,
now implemented against the rules given explicitly in the final merge
execution prompt.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models import AchievementLog, Journey, TransportMode, UserProfile
from core.services.gamification import (
    ECO_WARRIOR_BADGE,
    ECO_WARRIOR_BONUS,
    FIRST_JOURNEY_BADGE,
    FIRST_JOURNEY_BONUS,
    STREAK_MILESTONE_BADGE,
    STREAK_MILESTONE_BONUS,
    award_points_for_journey,
    calculate_journey_points,
    check_and_update_streak,
)

User = get_user_model()


def _completed_journey(user, mode, distance_km=None, carbon_saved_g=None, ended_at=None):
    return Journey.objects.create(
        user=user,
        transport_mode=mode,
        status=Journey.Status.COMPLETED,
        distance_km=distance_km,
        carbon_saved_g=carbon_saved_g,
        ended_at=ended_at or timezone.now(),
    )


class GamificationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gamer", password="testpass123")
        self.walking = TransportMode.objects.create(
            code=TransportMode.Code.WALKING, name="Walking", default_emission_factor_g_per_km=Decimal("0")
        )
        self.cycling = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING, name="Cycling", default_emission_factor_g_per_km=Decimal("0")
        )
        self.public_transit = TransportMode.objects.create(
            code=TransportMode.Code.PUBLIC_TRANSIT,
            name="Public Transit",
            default_emission_factor_g_per_km=Decimal("41"),
        )
        self.ev = TransportMode.objects.create(
            code=TransportMode.Code.ELECTRIC_VEHICLE,
            name="Electric Vehicle",
            default_emission_factor_g_per_km=Decimal("53"),
        )
        self.driving_car = TransportMode.objects.create(
            code=TransportMode.Code.DRIVING_CAR,
            name="Driving / Car",
            default_emission_factor_g_per_km=Decimal("192"),
        )


# -----------------------------------------------------------------------
# calculate_journey_points
# -----------------------------------------------------------------------
class CalculateJourneyPointsTests(GamificationTestCase):
    def test_carbon_points_10_per_kg(self):
        journey = _completed_journey(self.user, self.walking, distance_km=Decimal("0"), carbon_saved_g=Decimal("2000"))
        # 2000g = 2kg * 10 pts/kg = 20 pts, distance 0 * 15 = 0
        self.assertEqual(calculate_journey_points(journey), 20)

    def test_walking_distance_bonus_15_per_km(self):
        journey = _completed_journey(self.user, self.walking, distance_km=Decimal("4"), carbon_saved_g=Decimal("0"))
        self.assertEqual(calculate_journey_points(journey), 60)  # 4 * 15

    def test_cycling_distance_bonus_15_per_km(self):
        journey = _completed_journey(self.user, self.cycling, distance_km=Decimal("4"), carbon_saved_g=Decimal("0"))
        self.assertEqual(calculate_journey_points(journey), 60)

    def test_public_transit_distance_bonus_8_per_km(self):
        journey = _completed_journey(
            self.user, self.public_transit, distance_km=Decimal("10"), carbon_saved_g=Decimal("0")
        )
        self.assertEqual(calculate_journey_points(journey), 80)

    def test_ev_distance_bonus_3_per_km(self):
        journey = _completed_journey(self.user, self.ev, distance_km=Decimal("10"), carbon_saved_g=Decimal("0"))
        self.assertEqual(calculate_journey_points(journey), 30)

    def test_driving_car_distance_bonus_zero(self):
        journey = _completed_journey(
            self.user, self.driving_car, distance_km=Decimal("100"), carbon_saved_g=Decimal("0")
        )
        self.assertEqual(calculate_journey_points(journey), 0)

    def test_combined_carbon_and_distance_points(self):
        # cycling, 5km, 1500g (1.5kg) saved => 15pts/km * 5km = 75 + 10pts/kg * 1.5kg = 15 => 90
        journey = _completed_journey(self.user, self.cycling, distance_km=Decimal("5"), carbon_saved_g=Decimal("1500"))
        self.assertEqual(calculate_journey_points(journey), 90)

    def test_negative_carbon_saved_floored_to_zero(self):
        journey = _completed_journey(
            self.user, self.driving_car, distance_km=Decimal("10"), carbon_saved_g=Decimal("-500")
        )
        # Negative carbon savings must not subtract points; driving_car distance bonus is 0.
        self.assertEqual(calculate_journey_points(journey), 0)

    def test_fractional_points_round_half_up(self):
        # cycling, 1.03km * 15 = 15.45 -> rounds to 15
        journey = _completed_journey(self.user, self.cycling, distance_km=Decimal("1.03"), carbon_saved_g=Decimal("0"))
        self.assertEqual(calculate_journey_points(journey), 15)

    def test_none_distance_and_carbon_treated_as_zero(self):
        journey = Journey.objects.create(user=self.user, transport_mode=self.cycling, status=Journey.Status.COMPLETED)
        self.assertEqual(calculate_journey_points(journey), 0)


# -----------------------------------------------------------------------
# check_and_update_streak
# -----------------------------------------------------------------------
class CheckAndUpdateStreakTests(GamificationTestCase):
    def test_first_ever_activity_sets_streak_to_1(self):
        streak_before, streak_after, profile = check_and_update_streak(self.user, timezone.localdate())
        self.assertEqual(streak_before, 0)
        self.assertEqual(streak_after, 1)
        self.assertEqual(profile.longest_streak_days, 1)

    def test_same_day_does_not_double_increment(self):
        today = timezone.localdate()
        check_and_update_streak(self.user, today)
        streak_before, streak_after, profile = check_and_update_streak(self.user, today)
        self.assertEqual(streak_before, 1)
        self.assertEqual(streak_after, 1)

    def test_consecutive_day_increments(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        check_and_update_streak(self.user, yesterday)
        streak_before, streak_after, profile = check_and_update_streak(self.user, today)
        self.assertEqual(streak_before, 1)
        self.assertEqual(streak_after, 2)

    def test_gap_of_two_days_resets_then_recounts_to_1(self):
        today = timezone.localdate()
        three_days_ago = today - timedelta(days=3)
        check_and_update_streak(self.user, three_days_ago)
        streak_before, streak_after, profile = check_and_update_streak(self.user, today)
        self.assertEqual(streak_before, 1)
        self.assertEqual(streak_after, 1)  # reset, then today's activity counts as 1

    def test_longest_streak_persists_after_a_reset(self):
        base = timezone.localdate() - timedelta(days=20)
        for i in range(5):
            check_and_update_streak(self.user, base + timedelta(days=i))
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.current_streak_days, 5)
        self.assertEqual(profile.longest_streak_days, 5)

        # Big gap: current streak resets to 1, longest stays 5.
        check_and_update_streak(self.user, timezone.localdate())
        profile.refresh_from_db()
        self.assertEqual(profile.current_streak_days, 1)
        self.assertEqual(profile.longest_streak_days, 5)


# -----------------------------------------------------------------------
# award_points_for_journey — end to end, including milestones
# -----------------------------------------------------------------------
class AwardPointsForJourneyTests(GamificationTestCase):
    def test_first_journey_awards_bonus_and_badge(self):
        journey = _completed_journey(self.user, self.cycling, distance_km=Decimal("2"), carbon_saved_g=Decimal("0"))
        result = award_points_for_journey(journey)

        # 2km * 15 = 30 base points + 50 first-journey bonus = 80
        self.assertEqual(result.points_awarded, 80)
        self.assertEqual(len(result.achievements), 1)
        self.assertEqual(result.achievements[0].badge_name, FIRST_JOURNEY_BADGE)

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.total_points, 80)
        self.assertTrue(
            AchievementLog.objects.filter(
                user=self.user, badge_name=FIRST_JOURNEY_BADGE, points=FIRST_JOURNEY_BONUS
            ).exists()
        )

    def test_second_journey_does_not_reaward_first_journey_badge(self):
        j1 = _completed_journey(self.user, self.cycling, distance_km=Decimal("1"), carbon_saved_g=Decimal("0"))
        award_points_for_journey(j1)

        j2 = _completed_journey(
            self.user,
            self.cycling,
            distance_km=Decimal("1"),
            carbon_saved_g=Decimal("0"),
            ended_at=timezone.now() + timedelta(days=1),
        )
        result = award_points_for_journey(j2)

        self.assertEqual(result.points_awarded, 15)  # just the distance points, no bonus
        self.assertEqual(
            AchievementLog.objects.filter(user=self.user, badge_name=FIRST_JOURNEY_BADGE).count(), 1
        )

    def test_eco_warrior_awarded_on_crossing_threshold(self):
        journey = _completed_journey(
            self.user, self.cycling, distance_km=Decimal("0"), carbon_saved_g=Decimal("10000")
        )
        result = award_points_for_journey(journey)

        badge_names = [a.badge_name for a in result.achievements]
        self.assertIn(ECO_WARRIOR_BADGE, badge_names)
        self.assertTrue(AchievementLog.objects.filter(user=self.user, badge_name=ECO_WARRIOR_BADGE).exists())

    def test_eco_warrior_awarded_exactly_once_even_when_jumped_past_in_one_journey(self):
        journey = _completed_journey(
            self.user, self.cycling, distance_km=Decimal("0"), carbon_saved_g=Decimal("15000")
        )
        award_points_for_journey(journey)
        self.assertEqual(AchievementLog.objects.filter(user=self.user, badge_name=ECO_WARRIOR_BADGE).count(), 1)

        # A further journey (also above threshold cumulatively) must not re-award it.
        journey2 = _completed_journey(
            self.user,
            self.cycling,
            distance_km=Decimal("0"),
            carbon_saved_g=Decimal("5000"),
            ended_at=timezone.now() + timedelta(days=1),
        )
        award_points_for_journey(journey2)
        self.assertEqual(AchievementLog.objects.filter(user=self.user, badge_name=ECO_WARRIOR_BADGE).count(), 1)

    def test_eco_warrior_not_awarded_below_threshold(self):
        journey = _completed_journey(
            self.user, self.cycling, distance_km=Decimal("0"), carbon_saved_g=Decimal("9999")
        )
        result = award_points_for_journey(journey)
        self.assertNotIn(ECO_WARRIOR_BADGE, [a.badge_name for a in result.achievements])

    def test_week_of_green_awarded_on_7th_consecutive_day(self):
        base_day = timezone.localdate() - timedelta(days=6)
        result = None
        for i in range(7):
            journey = _completed_journey(
                self.user,
                self.walking,
                distance_km=Decimal("0"),
                carbon_saved_g=Decimal("0"),
                ended_at=timezone.make_aware(
                    timezone.datetime.combine(base_day + timedelta(days=i), timezone.datetime.min.time())
                )
                + timedelta(hours=12),
            )
            result = award_points_for_journey(journey)

        self.assertEqual(result.streak_after, 7)
        self.assertIn(STREAK_MILESTONE_BADGE, [a.badge_name for a in result.achievements])
        self.assertEqual(
            AchievementLog.objects.filter(user=self.user, badge_name=STREAK_MILESTONE_BADGE).count(), 1
        )

    def test_week_of_green_is_re_earnable_after_a_reset_and_rebuild(self):
        base_day = timezone.localdate() - timedelta(days=30)
        for i in range(7):
            journey = _completed_journey(
                self.user,
                self.walking,
                distance_km=Decimal("0"),
                ended_at=timezone.make_aware(
                    timezone.datetime.combine(base_day + timedelta(days=i), timezone.datetime.min.time())
                )
                + timedelta(hours=12),
            )
            award_points_for_journey(journey)
        self.assertEqual(
            AchievementLog.objects.filter(user=self.user, badge_name=STREAK_MILESTONE_BADGE).count(), 1
        )

        # Big gap resets the streak; rebuild a fresh 7-day streak.
        base_day_2 = timezone.localdate() - timedelta(days=6)
        for i in range(7):
            journey = _completed_journey(
                self.user,
                self.walking,
                distance_km=Decimal("0"),
                ended_at=timezone.make_aware(
                    timezone.datetime.combine(base_day_2 + timedelta(days=i), timezone.datetime.min.time())
                )
                + timedelta(hours=12),
            )
            award_points_for_journey(journey)

        self.assertEqual(
            AchievementLog.objects.filter(user=self.user, badge_name=STREAK_MILESTONE_BADGE).count(), 2
        )

    def test_points_earned_log_entry_created(self):
        journey = _completed_journey(self.user, self.cycling, distance_km=Decimal("3"), carbon_saved_g=Decimal("0"))
        award_points_for_journey(journey)
        self.assertTrue(
            AchievementLog.objects.filter(
                user=self.user, entry_type=AchievementLog.EntryType.POINTS_EARNED, journey=journey
            ).exists()
        )

    def test_no_points_earned_entry_when_zero_points(self):
        journey = _completed_journey(
            self.user, self.driving_car, distance_km=Decimal("0"), carbon_saved_g=Decimal("0")
        )
        award_points_for_journey(journey)
        self.assertFalse(
            AchievementLog.objects.filter(
                user=self.user, entry_type=AchievementLog.EntryType.POINTS_EARNED, journey=journey
            ).exists()
        )
        # First-journey badge still fires even with zero journey points.
        self.assertTrue(AchievementLog.objects.filter(user=self.user, badge_name=FIRST_JOURNEY_BADGE).exists())

    def test_total_points_accumulate_across_journeys(self):
        j1 = _completed_journey(self.user, self.cycling, distance_km=Decimal("1"), carbon_saved_g=Decimal("0"))
        award_points_for_journey(j1)
        j2 = _completed_journey(
            self.user,
            self.cycling,
            distance_km=Decimal("2"),
            carbon_saved_g=Decimal("0"),
            ended_at=timezone.now() + timedelta(days=1),
        )
        award_points_for_journey(j2)

        profile = UserProfile.objects.get(user=self.user)
        # j1: 15 (distance) + 50 (first journey) = 65; j2: 30 (distance) = 30; total 95
        self.assertEqual(profile.total_points, 95)
