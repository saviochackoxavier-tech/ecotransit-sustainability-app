"""
Core EcoTransit domain models.

Phase 2 scope only: data models and their relationships. No views, forms,
API endpoints, carbon-calculation logic, SHA-256 hashing logic, streak/point
accounting logic, or service integrations are implemented here — those
belong to later phases per the v2.1.1 specification.

Each model's docstring cites the spec sentence (Section 3) it implements.
Fields not explicitly named in the spec are marked "ASSUMPTION" so a
reviewer (human or IBM Bob) can quickly see what was inferred versus what
was frozen.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TransportMode(models.Model):
    """
    "Transport Mode: Defines available modes (Walking, Cycling, Public
    Transit, Electric Vehicle, Driving/Car) with default emission factors
    (g CO2 / passenger-km)." — Spec §3.
    """

    class Code(models.TextChoices):
        WALKING = "walking", "Walking"
        CYCLING = "cycling", "Cycling"
        PUBLIC_TRANSIT = "public_transit", "Public Transit"
        ELECTRIC_VEHICLE = "electric_vehicle", "Electric Vehicle"
        DRIVING_CAR = "driving_car", "Driving / Car"

    # ASSUMPTION: the spec names five fixed modes; modeled as a constrained
    # choice field (rather than free text) so the set stays exactly the
    # five named modes unless a later phase deliberately changes it.
    code = models.CharField(max_length=32, choices=Code.choices, unique=True)
    name = models.CharField(max_length=100)

    # ASSUMPTION: units are g CO2 per passenger-km as stated in the spec;
    # stored as Decimal (not float) for accuracy in later carbon
    # calculations, which remain out of scope here.
    default_emission_factor_g_per_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Default emission factor in g CO2 per passenger-km.",
    )

    # ASSUMPTION: not named in the spec; added so a mode can be retired
    # without deleting historical journeys/snapshots that reference it.
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    "User Profile / Extension: Extends Django's built-in User model to
    track user preferences, total points, and streak counts." — Spec §3.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # ASSUMPTION: "user preferences" is not itemized in the spec. Modeled
    # as a single preferred transport mode, since that is the one
    # preference concretely tied to a spec'd entity. Additional
    # preference fields can be added in a later phase without breaking
    # this model.
    preferred_transport_mode = models.ForeignKey(
        TransportMode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    total_points = models.PositiveIntegerField(default=0)

    # ASSUMPTION: "streak counts" (plural) modeled as current + longest,
    # a standard pairing; last_activity_date is stored so a later phase
    # can compute streak continuity without redesigning this model.
    current_streak_days = models.PositiveIntegerField(default=0)
    longest_streak_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user}"


class Journey(models.Model):
    """
    "Journey / Trip Record: Stores user journeys, starting/ending points,
    total distance, calculated carbon savings, SHA-256 integrity hash, and
    legal disclaimer flags." — Spec §3.

    Only the record itself is modeled here. GPS tracking behavior, carbon
    calculation, and SHA-256 hash computation are later-phase logic (the
    master spec assigns hash/finalization to the `/api/journeys/<id>/stop/`
    endpoint, not to Phase 2).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="journeys",
    )

    # PROTECT: a transport mode must not be deletable while journeys still
    # reference it, to preserve historical journey records.
    transport_mode = models.ForeignKey(
        TransportMode,
        on_delete=models.PROTECT,
        related_name="journeys",
    )

    # ASSUMPTION: "starting/ending points" modeled as an optional label
    # plus optional lat/lng, since the spec doesn't specify whether points
    # are addresses, coordinates, or both. Nullable because Phase 2 does
    # not populate these via any tracking workflow.
    start_label = models.CharField(max_length=255, blank=True)
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    end_label = models.CharField(max_length=255, blank=True)
    end_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    end_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    carbon_saved_g = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Calculated carbon savings in grams CO2. Populated by later-phase logic.",
    )

    # ASSUMPTION: a status field is not named explicitly in the spec but
    # is implied by "active GPS journey" language in the master spec's API
    # table (Section 26); needed to distinguish an in-progress journey
    # from a finalized record.
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    # Storage only — no hashing logic implemented in Phase 2.
    integrity_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hex digest, populated on journey finalization by a later phase.",
    )

    legal_disclaimer_accepted = models.BooleanField(default=False)

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Journey #{self.pk} ({self.user}, {self.transport_mode})"


class JourneyPoint(models.Model):
    """
    "Journey Point: Sequential GPS coordinates linked to active journeys."
    — Spec §3 (ForeignKey to Journey, per the Phase 2 prompt).
    """

    journey = models.ForeignKey(Journey, on_delete=models.CASCADE, related_name="points")

    # ASSUMPTION: "sequential" implies an explicit order field rather than
    # relying solely on insertion/timestamp order.
    sequence = models.PositiveIntegerField()

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["journey", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["journey", "sequence"],
                name="unique_journey_point_sequence",
            )
        ]

    def __str__(self):
        return f"Point {self.sequence} of Journey #{self.journey_id}"


class EmissionFactorSnapshot(models.Model):
    """
    "Emission Factor Snapshot: Historical snapshot table capturing
    emission factors at the time of journey completion to ensure
    historical audit integrity." — Spec §3.

    Decoupled from TransportMode.default_emission_factor_g_per_km, which
    may change over time; this table freezes the value that applied to a
    specific journey.
    """

    # ASSUMPTION: one snapshot per journey (OneToOne), since the spec ties
    # the snapshot to "the time of journey completion" for a single
    # journey rather than describing a general emission-factor history log.
    journey = models.OneToOneField(
        Journey,
        on_delete=models.CASCADE,
        related_name="emission_snapshot",
    )
    transport_mode = models.ForeignKey(
        TransportMode,
        on_delete=models.PROTECT,
        related_name="emission_snapshots",
    )
    emission_factor_g_per_km = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Emission factor value as it stood at capture time.",
    )
    captured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Snapshot for Journey #{self.journey_id} ({self.transport_mode})"


class AchievementLog(models.Model):
    """
    "Achievement / Points Log: Records points earned, streak milestones,
    and unlocked badges." — Spec §3.
    """

    class EntryType(models.TextChoices):
        POINTS_EARNED = "points_earned", "Points Earned"
        STREAK_MILESTONE = "streak_milestone", "Streak Milestone"
        BADGE_UNLOCKED = "badge_unlocked", "Badge Unlocked"

    # ASSUMPTION: the spec names "Achievement / Points Log" with a slash,
    # read here as one combined ledger model (an event log with a type
    # discriminator) rather than two separate models, since all three
    # named event kinds (points, streak milestones, badges) share the same
    # shape: who, what happened, how many points, when.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="achievement_logs",
    )
    journey = models.ForeignKey(
        Journey,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="achievement_logs",
        help_text="Journey that triggered this entry, if any.",
    )
    entry_type = models.CharField(max_length=32, choices=EntryType.choices)
    points = models.IntegerField(default=0)
    badge_name = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_entry_type_display()} for {self.user} ({self.points} pts)"
