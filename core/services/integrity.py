"""
SHA-256 journey integrity hashing.

Spec (Phase 3 execution prompt): "Implement cryptographic hashing utility
functions that compile journey details (user ID, start/end timestamps,
distance, carbon saved, sequence points) into an immutable SHA-256 hash
stored on the Journey model when a journey is stopped."

These are pure functions. Nothing here decides *when* a journey is
stopped or wires into an API endpoint — the master spec assigns
finalization to the `/api/journeys/<id>/stop/` endpoint, which is a later
phase's responsibility. `finalize_journey_integrity_hash` performs the one
persistence step the spec explicitly describes ("stored on the Journey
model"), so a later phase's stop-workflow has a single call to make once
distance/carbon/points are all finalized.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

from core.models import Journey

# Match the DecimalField precision declared on the relevant model fields
# (core/models.py) exactly. Values must be quantized before hashing so
# that the hash is stable regardless of whether a Journey/JourneyPoint
# instance is freshly constructed in Python (e.g. Decimal("3.5")) or
# re-read from the database (e.g. Decimal("3.500")) — those are the same
# number but stringify differently, which would otherwise make the hash
# depend on object provenance rather than actual data.
_DISTANCE_QUANTIZE = Decimal("0.001")   # Journey.distance_km, Journey.carbon_saved_g
_COORDINATE_QUANTIZE = Decimal("0.000001")  # JourneyPoint.latitude / .longitude


def _quantized(value: Decimal | None, places: Decimal) -> str:
    if value is None:
        return ""
    return str(Decimal(value).quantize(places))


def _canonical_journey_payload(journey: Journey) -> str:
    """
    Canonical, order-stable string built from exactly the fields the spec
    names: user ID, start/end timestamps, distance, carbon saved, and the
    ordered sequence points. Journey.pk is deliberately excluded — the
    spec's field list names "user ID", not "journey ID".
    """
    parts = [
        f"user_id={journey.user_id}",
        f"started_at={journey.started_at.isoformat() if journey.started_at else ''}",
        f"ended_at={journey.ended_at.isoformat() if journey.ended_at else ''}",
        f"distance_km={_quantized(journey.distance_km, _DISTANCE_QUANTIZE)}",
        f"carbon_saved_g={_quantized(journey.carbon_saved_g, _DISTANCE_QUANTIZE)}",
    ]

    points = journey.points.order_by("sequence").values_list("sequence", "latitude", "longitude")
    points_part = ";".join(
        f"{seq}:{_quantized(lat, _COORDINATE_QUANTIZE)}:{_quantized(lon, _COORDINATE_QUANTIZE)}"
        for seq, lat, lon in points
    )
    parts.append(f"points={points_part}")

    return "|".join(parts)


def compute_journey_integrity_hash(journey: Journey) -> str:
    """Return the SHA-256 hex digest of the journey's canonical field values."""
    canonical = _canonical_journey_payload(journey)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_journey_integrity_hash(journey: Journey) -> bool:
    """
    Return True if journey.integrity_hash matches a freshly computed hash
    of the journey's *current* field values — i.e. tamper detection. False
    if no hash has been stored yet, or if any hashed field (including any
    JourneyPoint) has changed since the hash was computed.
    """
    if not journey.integrity_hash:
        return False
    return journey.integrity_hash == compute_journey_integrity_hash(journey)


def finalize_journey_integrity_hash(journey: Journey) -> str:
    """
    Compute and persist the integrity hash on the journey. Does not set
    journey.status or any other field — sequencing the full "stop
    journey" workflow (which also touches distance/carbon calculation)
    is a later phase's responsibility.
    """
    journey.integrity_hash = compute_journey_integrity_hash(journey)
    journey.save(update_fields=["integrity_hash"])
    return journey.integrity_hash
