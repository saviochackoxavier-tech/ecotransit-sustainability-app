"""
Gamification service layer: points, streak tracking, and achievement
milestones.

The numeric rules below are taken directly from the execution prompt
that finally specified them ("Full Implementation of Points, Streak &
Achievement Logic") — nothing here is invented; this closes out the
item that was deliberately left unimplemented through Phases 3–6
because no methodology had been provided until now.

Ambiguities in that prompt's wording, and how each was resolved:

- "Reset the streak count back to 0" (after a missed day) is applied as
  reset-then-recount: the journey that triggers this evaluation is
  itself a qualifying journey completed today, so the streak becomes 1
  (not 0) once the reset is applied — matching how every common
  streak-tracking product behaves. A user finishing a journey today
  would find "streak: 0" directly afterward confusing and wrong.
- The prompt's "48 hours without activity" phrasing and its "Daily
  Activity Definition" section describe the same rule two ways. This
  implementation uses the calendar-day comparison from "Daily Activity
  Definition" (the more precise of the two), since a raw 48-hour timer
  and a calendar-day boundary disagree near midnight and the prompt
  names calendar days as the canonical unit elsewhere.
- "Eco Warrior" idempotency is enforced by existence-check (has this
  user already earned this badge?) rather than by requiring the
  previous cumulative total to specifically sit under 10kg — this
  correctly fires exactly once even if a single journey's carbon
  savings jump the cumulative total past the threshold in one step
  (e.g. 6kg -> 15kg).
- "Week of Green" (7-day streak) is treated as re-earnable each time a
  user's streak freshly transitions from something other than 7 to
  exactly 7 (i.e. after a reset-and-rebuild cycle), not as a
  once-ever-in-a-lifetime badge. The prompt's "idempotency" requirement
  is read as "don't double-award for the same trigger event" (e.g.
  concurrent requests), not "only ever award this once" — flagged here
  since the prompt doesn't explicitly settle it either way.
- A negative carbon_saved_g (see core/services/carbon.py — not clamped
  to zero there, by design) is floored to 0 before computing
  carbon-based points, so a journey that technically emitted more than
  the baseline never *subtracts* points. The distance-based bonus is
  computed independently of this floor.
- Per-journey point totals are rounded to the nearest integer
  (round-half-up), since UserProfile.total_points and
  AchievementLog.points are both integer fields and the prompt's
  formula can produce fractional values (e.g. 15 pts/km * 2.3 km).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from core.models import AchievementLog, Journey, TransportMode, UserProfile

# --- Points rules, exactly as specified ---
CARBON_POINTS_PER_KG = Decimal("10")

DISTANCE_POINTS_PER_KM = {
    TransportMode.Code.WALKING: Decimal("15"),
    TransportMode.Code.CYCLING: Decimal("15"),
    TransportMode.Code.PUBLIC_TRANSIT: Decimal("8"),
    TransportMode.Code.ELECTRIC_VEHICLE: Decimal("3"),
    TransportMode.Code.DRIVING_CAR: Decimal("0"),
}

# --- Achievement thresholds/bonuses, exactly as specified ---
ECO_WARRIOR_THRESHOLD_G = Decimal("10000")  # 10 kg
STREAK_MILESTONE_DAYS = 7

FIRST_JOURNEY_BONUS = 50
ECO_WARRIOR_BONUS = 200
STREAK_MILESTONE_BONUS = 100

FIRST_JOURNEY_BADGE = "First Steps"
ECO_WARRIOR_BADGE = "Eco Warrior"
STREAK_MILESTONE_BADGE = "Week of Green"


@dataclass
class GamificationResult:
    points_awarded: int
    streak_before: int
    streak_after: int
    achievements: list = field(default_factory=list)


def _round_points(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_journey_points(journey: Journey) -> int:
    """
    Total journey points = base carbon points (10 pts/kg CO2 saved,
    floored at 0) + distance_km * mode multiplier.
    """
    carbon_saved_g = journey.carbon_saved_g if journey.carbon_saved_g is not None else Decimal("0")
    carbon_saved_kg = max(carbon_saved_g, Decimal("0")) / Decimal("1000")
    base_points = carbon_saved_kg * CARBON_POINTS_PER_KG

    distance_km = journey.distance_km if journey.distance_km is not None else Decimal("0")
    multiplier = DISTANCE_POINTS_PER_KM.get(journey.transport_mode.code, Decimal("0"))
    distance_points = distance_km * multiplier

    return _round_points(base_points + distance_points)


def check_and_update_streak(user, activity_date: date | None = None) -> tuple[int, int, UserProfile]:
    """
    Spec-named helper ("Implement a helper validation method
    check_and_update_streak(user) called during journey finalization").

    Locks (select_for_update) and updates the user's UserProfile streak
    counters for a qualifying journey completed on `activity_date`
    (defaults to today, in settings.TIME_ZONE). Must be called from
    within an existing transaction.atomic() block — award_points_for_journey
    provides one; a caller invoking this directly is responsible for its
    own transaction.

    Returns (streak_before, streak_after, profile).
    """
    if activity_date is None:
        activity_date = timezone.localdate()

    profile, _ = UserProfile.objects.select_for_update().get_or_create(user=user)
    streak_before = profile.current_streak_days

    if profile.last_activity_date is None:
        profile.current_streak_days = 1
    elif profile.last_activity_date == activity_date:
        pass  # already active today: don't double-increment
    elif profile.last_activity_date == activity_date - timedelta(days=1):
        profile.current_streak_days += 1
    else:
        # A full calendar day (or more) passed with no qualifying
        # journey: the streak resets, then today's journey starts a new one.
        profile.current_streak_days = 1

    profile.last_activity_date = activity_date
    profile.longest_streak_days = max(profile.longest_streak_days, profile.current_streak_days)
    profile.save(update_fields=["current_streak_days", "longest_streak_days", "last_activity_date"])

    return streak_before, profile.current_streak_days, profile


def award_points_for_journey(journey: Journey) -> GamificationResult:
    """
    Apply the full points/streak/achievement engine for one completed
    journey. Must be called with journey.status already COMPLETED and
    journey.carbon_saved_g / distance_km already finalized (i.e. after
    finalize_journey_emissions and finalize_journey_integrity_hash).

    Wraps everything in one transaction, holding a row lock on the
    user's UserProfile for its duration, so concurrent journey
    completions for the same user can't race on points/streak counters
    or double-award a milestone.
    """
    with transaction.atomic():
        activity_date = timezone.localtime(journey.ended_at).date() if journey.ended_at else timezone.localdate()
        streak_before, streak_after, profile = check_and_update_streak(journey.user, activity_date)

        journey_points = calculate_journey_points(journey)
        total_points_to_add = journey_points
        achievements = []

        is_first_journey = (
            not Journey.objects.filter(user=journey.user, status=Journey.Status.COMPLETED)
            .exclude(pk=journey.pk)
            .exists()
        )
        if is_first_journey:
            total_points_to_add += FIRST_JOURNEY_BONUS
            achievements.append(
                AchievementLog.objects.create(
                    user=journey.user,
                    journey=journey,
                    entry_type=AchievementLog.EntryType.BADGE_UNLOCKED,
                    points=FIRST_JOURNEY_BONUS,
                    badge_name=FIRST_JOURNEY_BADGE,
                    description="Completed your first EcoTransit journey.",
                )
            )

        cumulative_carbon_saved_g = (
            Journey.objects.filter(
                user=journey.user, status=Journey.Status.COMPLETED, carbon_saved_g__isnull=False
            ).aggregate(total=Sum("carbon_saved_g"))["total"]
            or Decimal("0")
        )
        already_has_eco_warrior = AchievementLog.objects.filter(
            user=journey.user, badge_name=ECO_WARRIOR_BADGE
        ).exists()
        if not already_has_eco_warrior and cumulative_carbon_saved_g >= ECO_WARRIOR_THRESHOLD_G:
            total_points_to_add += ECO_WARRIOR_BONUS
            achievements.append(
                AchievementLog.objects.create(
                    user=journey.user,
                    journey=journey,
                    entry_type=AchievementLog.EntryType.BADGE_UNLOCKED,
                    points=ECO_WARRIOR_BONUS,
                    badge_name=ECO_WARRIOR_BADGE,
                    description="Cumulative CO2 savings crossed 10 kg.",
                )
            )

        if streak_before != STREAK_MILESTONE_DAYS and streak_after == STREAK_MILESTONE_DAYS:
            total_points_to_add += STREAK_MILESTONE_BONUS
            achievements.append(
                AchievementLog.objects.create(
                    user=journey.user,
                    journey=journey,
                    entry_type=AchievementLog.EntryType.STREAK_MILESTONE,
                    points=STREAK_MILESTONE_BONUS,
                    badge_name=STREAK_MILESTONE_BADGE,
                    description="Reached a 7-day activity streak.",
                )
            )

        if journey_points:
            AchievementLog.objects.create(
                user=journey.user,
                journey=journey,
                entry_type=AchievementLog.EntryType.POINTS_EARNED,
                points=journey_points,
                description=f"Points earned for journey #{journey.pk}.",
            )

        UserProfile.objects.filter(pk=profile.pk).update(total_points=F("total_points") + total_points_to_add)
        profile.refresh_from_db()

        return GamificationResult(
            points_awarded=total_points_to_add,
            streak_before=streak_before,
            streak_after=streak_after,
            achievements=achievements,
        )
