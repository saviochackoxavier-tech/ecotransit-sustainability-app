"""
Pure-function JSON serializers for the core domain models.

Not a Django REST Framework serializer class hierarchy — see
core/api/__init__.py for why. These are plain functions returning
JSON-safe dicts (Decimals and datetimes stringified).
"""

from __future__ import annotations

from core.models import Journey, JourneyPoint, TransportMode, UserProfile


def serialize_transport_mode(mode: TransportMode) -> dict:
    return {
        "id": mode.id,
        "code": mode.code,
        "name": mode.name,
        "default_emission_factor_g_per_km": str(mode.default_emission_factor_g_per_km),
        "is_active": mode.is_active,
    }


def serialize_journey_point(point: JourneyPoint) -> dict:
    return {
        "id": point.id,
        "sequence": point.sequence,
        "latitude": str(point.latitude),
        "longitude": str(point.longitude),
        "recorded_at": point.recorded_at.isoformat(),
    }


def serialize_journey(journey: Journey, include_points: bool = False) -> dict:
    data = {
        "id": journey.id,
        "transport_mode": serialize_transport_mode(journey.transport_mode),
        "status": journey.status,
        "start_label": journey.start_label,
        "start_latitude": _decimal_str(journey.start_latitude),
        "start_longitude": _decimal_str(journey.start_longitude),
        "end_label": journey.end_label,
        "end_latitude": _decimal_str(journey.end_latitude),
        "end_longitude": _decimal_str(journey.end_longitude),
        "distance_km": _decimal_str(journey.distance_km),
        "carbon_saved_g": _decimal_str(journey.carbon_saved_g),
        "integrity_hash": journey.integrity_hash,
        "legal_disclaimer_accepted": journey.legal_disclaimer_accepted,
        "started_at": journey.started_at.isoformat() if journey.started_at else None,
        "ended_at": journey.ended_at.isoformat() if journey.ended_at else None,
    }
    if include_points:
        data["points"] = [serialize_journey_point(p) for p in journey.points.order_by("sequence")]
    return data


def _decimal_str(value) -> str | None:
    return str(value) if value is not None else None


def serialize_user_profile(profile: UserProfile) -> dict:
    return {
        "user_id": profile.user_id,
        "preferred_transport_mode": (
            serialize_transport_mode(profile.preferred_transport_mode)
            if profile.preferred_transport_mode_id
            else None
        ),
        "total_points": profile.total_points,
        "current_streak_days": profile.current_streak_days,
        "longest_streak_days": profile.longest_streak_days,
        "last_activity_date": (
            profile.last_activity_date.isoformat() if profile.last_activity_date else None
        ),
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }
