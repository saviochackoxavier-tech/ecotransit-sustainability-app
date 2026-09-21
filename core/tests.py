"""
Unit tests for the core domain models: relationships, validation rules,
string representations, and cascade-deletion behavior.

No views, forms, or API endpoints exist yet, so these tests exercise the
models directly via the ORM.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.utils import DataError
from django.test import TestCase

from core.models import (
    AchievementLog,
    EmissionFactorSnapshot,
    Journey,
    JourneyPoint,
    TransportMode,
    UserProfile,
)

User = get_user_model()


class TransportModeTests(TestCase):
    def test_str_representation(self):
        mode = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING,
            name="Cycling",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        self.assertEqual(str(mode), "Cycling")

    def test_code_must_be_unique(self):
        TransportMode.objects.create(
            code=TransportMode.Code.WALKING,
            name="Walking",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TransportMode.objects.create(
                    code=TransportMode.Code.WALKING,
                    name="Walking (duplicate)",
                    default_emission_factor_g_per_km=Decimal("0.000"),
                )

    def test_negative_emission_factor_fails_validation(self):
        mode = TransportMode(
            code=TransportMode.Code.DRIVING_CAR,
            name="Driving / Car",
            default_emission_factor_g_per_km=Decimal("-5.000"),
        )
        with self.assertRaises(Exception):
            mode.full_clean()

    def test_default_is_active_true(self):
        mode = TransportMode.objects.create(
            code=TransportMode.Code.ELECTRIC_VEHICLE,
            name="Electric Vehicle",
            default_emission_factor_g_per_km=Decimal("53.000"),
        )
        self.assertTrue(mode.is_active)


class UserProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")

    def test_str_representation(self):
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(str(profile), f"Profile: {self.user}")

    def test_defaults(self):
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.total_points, 0)
        self.assertEqual(profile.current_streak_days, 0)
        self.assertEqual(profile.longest_streak_days, 0)
        self.assertIsNone(profile.last_activity_date)

    def test_one_profile_per_user_enforced(self):
        UserProfile.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserProfile.objects.create(user=self.user)

    def test_cascade_delete_when_user_deleted(self):
        UserProfile.objects.create(user=self.user)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.user.delete()
        self.assertEqual(UserProfile.objects.count(), 0)

    def test_preferred_transport_mode_set_null_on_mode_delete(self):
        mode = TransportMode.objects.create(
            code=TransportMode.Code.WALKING,
            name="Walking",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        profile = UserProfile.objects.create(user=self.user, preferred_transport_mode=mode)
        mode.delete()
        profile.refresh_from_db()
        self.assertIsNone(profile.preferred_transport_mode)


class JourneyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bob", password="testpass123")
        self.mode = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING,
            name="Cycling",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )

    def test_str_representation(self):
        journey = Journey.objects.create(user=self.user, transport_mode=self.mode)
        self.assertIn(f"Journey #{journey.pk}", str(journey))
        self.assertIn(str(self.user), str(journey))

    def test_default_status_is_active(self):
        journey = Journey.objects.create(user=self.user, transport_mode=self.mode)
        self.assertEqual(journey.status, Journey.Status.ACTIVE)

    def test_default_legal_disclaimer_not_accepted(self):
        journey = Journey.objects.create(user=self.user, transport_mode=self.mode)
        self.assertFalse(journey.legal_disclaimer_accepted)

    def test_status_choice_validation_rejects_invalid_value(self):
        journey = Journey(user=self.user, transport_mode=self.mode, status="not_a_real_status")
        with self.assertRaises(Exception):
            journey.full_clean()

    def test_cascade_delete_when_user_deleted(self):
        Journey.objects.create(user=self.user, transport_mode=self.mode)
        self.assertEqual(Journey.objects.count(), 1)
        self.user.delete()
        self.assertEqual(Journey.objects.count(), 0)

    def test_transport_mode_protected_from_deletion_when_referenced(self):
        Journey.objects.create(user=self.user, transport_mode=self.mode)
        with self.assertRaises(Exception):
            with transaction.atomic():
                self.mode.delete()

    def test_negative_distance_fails_validation(self):
        journey = Journey(
            user=self.user,
            transport_mode=self.mode,
            distance_km=Decimal("-1.000"),
        )
        with self.assertRaises(Exception):
            journey.full_clean()

    def test_integrity_hash_blank_by_default(self):
        journey = Journey.objects.create(user=self.user, transport_mode=self.mode)
        self.assertEqual(journey.integrity_hash, "")


class JourneyPointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carol", password="testpass123")
        self.mode = TransportMode.objects.create(
            code=TransportMode.Code.WALKING,
            name="Walking",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        self.journey = Journey.objects.create(user=self.user, transport_mode=self.mode)

    def test_str_representation(self):
        point = JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("12.345678"), longitude=Decimal("98.765432")
        )
        self.assertEqual(str(point), f"Point 1 of Journey #{self.journey.pk}")

    def test_related_name_from_journey(self):
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("1.000000"), longitude=Decimal("1.000000")
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=2, latitude=Decimal("2.000000"), longitude=Decimal("2.000000")
        )
        self.assertEqual(self.journey.points.count(), 2)

    def test_duplicate_sequence_within_same_journey_rejected(self):
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("1.000000"), longitude=Decimal("1.000000")
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JourneyPoint.objects.create(
                    journey=self.journey, sequence=1, latitude=Decimal("2.000000"), longitude=Decimal("2.000000")
                )

    def test_same_sequence_allowed_across_different_journeys(self):
        other_journey = Journey.objects.create(user=self.user, transport_mode=self.mode)
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("1.000000"), longitude=Decimal("1.000000")
        )
        # Should not raise: sequence=1 is unique per-journey, not globally.
        JourneyPoint.objects.create(
            journey=other_journey, sequence=1, latitude=Decimal("1.000000"), longitude=Decimal("1.000000")
        )
        self.assertEqual(JourneyPoint.objects.filter(sequence=1).count(), 2)

    def test_cascade_delete_when_journey_deleted(self):
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("1.000000"), longitude=Decimal("1.000000")
        )
        self.assertEqual(JourneyPoint.objects.count(), 1)
        self.journey.delete()
        self.assertEqual(JourneyPoint.objects.count(), 0)


class EmissionFactorSnapshotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dave", password="testpass123")
        self.mode = TransportMode.objects.create(
            code=TransportMode.Code.PUBLIC_TRANSIT,
            name="Public Transit",
            default_emission_factor_g_per_km=Decimal("41.000"),
        )
        self.journey = Journey.objects.create(user=self.user, transport_mode=self.mode)

    def test_str_representation(self):
        snapshot = EmissionFactorSnapshot.objects.create(
            journey=self.journey,
            transport_mode=self.mode,
            emission_factor_g_per_km=Decimal("41.000"),
        )
        self.assertIn(f"Journey #{self.journey.pk}", str(snapshot))

    def test_one_snapshot_per_journey_enforced(self):
        EmissionFactorSnapshot.objects.create(
            journey=self.journey,
            transport_mode=self.mode,
            emission_factor_g_per_km=Decimal("41.000"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EmissionFactorSnapshot.objects.create(
                    journey=self.journey,
                    transport_mode=self.mode,
                    emission_factor_g_per_km=Decimal("41.000"),
                )

    def test_snapshot_survives_transport_mode_value_changes(self):
        """
        Changing the live TransportMode's default factor must not affect
        an already-captured snapshot value — this is the entire purpose
        of the snapshot table per the spec ("historical audit integrity").
        """
        snapshot = EmissionFactorSnapshot.objects.create(
            journey=self.journey,
            transport_mode=self.mode,
            emission_factor_g_per_km=Decimal("41.000"),
        )
        self.mode.default_emission_factor_g_per_km = Decimal("999.000")
        self.mode.save()
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.emission_factor_g_per_km, Decimal("41.000"))

    def test_cascade_delete_when_journey_deleted(self):
        EmissionFactorSnapshot.objects.create(
            journey=self.journey,
            transport_mode=self.mode,
            emission_factor_g_per_km=Decimal("41.000"),
        )
        self.assertEqual(EmissionFactorSnapshot.objects.count(), 1)
        self.journey.delete()
        self.assertEqual(EmissionFactorSnapshot.objects.count(), 0)

    def test_transport_mode_protected_from_deletion_when_referenced(self):
        EmissionFactorSnapshot.objects.create(
            journey=self.journey,
            transport_mode=self.mode,
            emission_factor_g_per_km=Decimal("41.000"),
        )
        with self.assertRaises(Exception):
            with transaction.atomic():
                self.mode.delete()


class AchievementLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="erin", password="testpass123")
        self.mode = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING,
            name="Cycling",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        self.journey = Journey.objects.create(user=self.user, transport_mode=self.mode)

    def test_str_representation(self):
        entry = AchievementLog.objects.create(
            user=self.user,
            entry_type=AchievementLog.EntryType.POINTS_EARNED,
            points=10,
        )
        self.assertIn("Points Earned", str(entry))
        self.assertIn("10 pts", str(entry))

    def test_default_points_zero(self):
        entry = AchievementLog.objects.create(
            user=self.user, entry_type=AchievementLog.EntryType.BADGE_UNLOCKED
        )
        self.assertEqual(entry.points, 0)

    def test_journey_is_optional(self):
        entry = AchievementLog.objects.create(
            user=self.user, entry_type=AchievementLog.EntryType.STREAK_MILESTONE, points=5
        )
        self.assertIsNone(entry.journey)

    def test_journey_set_null_on_journey_delete(self):
        entry = AchievementLog.objects.create(
            user=self.user,
            journey=self.journey,
            entry_type=AchievementLog.EntryType.POINTS_EARNED,
            points=5,
        )
        self.journey.delete()
        entry.refresh_from_db()
        self.assertIsNone(entry.journey)
        # The log entry itself must survive the journey's deletion.
        self.assertTrue(AchievementLog.objects.filter(pk=entry.pk).exists())

    def test_cascade_delete_when_user_deleted(self):
        AchievementLog.objects.create(
            user=self.user, entry_type=AchievementLog.EntryType.POINTS_EARNED, points=5
        )
        self.assertEqual(AchievementLog.objects.count(), 1)
        self.user.delete()
        self.assertEqual(AchievementLog.objects.count(), 0)

    def test_related_name_from_user(self):
        AchievementLog.objects.create(
            user=self.user, entry_type=AchievementLog.EntryType.POINTS_EARNED, points=3
        )
        AchievementLog.objects.create(
            user=self.user, entry_type=AchievementLog.EntryType.BADGE_UNLOCKED, points=0
        )
        self.assertEqual(self.user.achievement_logs.count(), 2)
