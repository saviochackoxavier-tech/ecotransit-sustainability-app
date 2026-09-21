"""
JSON API views (spec §26).

Endpoints and their exact responsibilities/access constraints follow the
spec's API table precisely:

    GET  /api/journeys/                 -> journey_list
    POST /api/journeys/start/           -> journey_start
    POST /api/journeys/<id>/points/     -> journey_add_point
    POST /api/journeys/<id>/stop/       -> journey_stop
    GET  /api/journeys/<id>/            -> journey_detail
    GET/POST /api/routes/               -> routes_view
    GET/POST /api/geocode/              -> geocode_view

Security rule (spec §26): "Ownership must always be derived from the
authenticated session. Client-supplied user IDs must never determine
record ownership." No view reads a user id from the request body;
request.user is always the source of truth, and every per-journey lookup
filters by `user=request.user` so a non-owner gets 404 (not 403) rather
than a response confirming another user's journey ID exists.

Session authentication + Django's standard CSRF protection is used
throughout (spec §2: "Django standard session authentication and CSRF
protection") — no @csrf_exempt anywhere.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.api.auth import login_required_json as _json_login_required
from core.api.serializers import serialize_journey, serialize_transport_mode, serialize_user_profile
from core.models import Journey, JourneyPoint, TransportMode, UserProfile
from core.services.carbon import CarbonCalculationError, finalize_journey_emissions
from core.services.distance import calculate_journey_distance_km
from core.services.gamification import award_points_for_journey
from core.services.integrity import finalize_journey_integrity_hash
from core.services.openroute import OpenRouteServiceClient, OpenRouteServiceError


def _parse_json_body(request):
    """Return the parsed JSON body as a dict, {} for an empty body, or None if invalid."""
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _decimal_or_none(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _get_owned_journey_or_404(request, journey_id):
    """
    Look up a journey, scoped to the authenticated user. Returns
    (journey, None) on success or (None, error_response) on failure.
    Deliberately 404s (not 403) for a journey owned by someone else, to
    avoid confirming the ID exists.
    """
    try:
        return Journey.objects.get(pk=journey_id, user=request.user), None
    except Journey.DoesNotExist:
        return None, JsonResponse({"error": "Journey not found."}, status=404)


# -----------------------------------------------------------------------
# Journey endpoints
# -----------------------------------------------------------------------
@_json_login_required
@require_http_methods(["GET"])
def journey_list(request):
    """GET /api/journeys/ — return only the authenticated user's journeys."""
    journeys = Journey.objects.filter(user=request.user).order_by("-started_at")
    return JsonResponse({"journeys": [serialize_journey(j) for j in journeys]})


@_json_login_required
@require_http_methods(["POST"])
def journey_start(request):
    """
    POST /api/journeys/start/ — start a journey. Requires authentication
    (enforced by decorator) and location consent, and rejects the request
    if the user already has an active journey.

    ASSUMPTION: "location consent" is mapped onto the existing
    Journey.legal_disclaimer_accepted field, since the spec names that
    exact field on the Journey model (§3) and does not describe a
    separate consent mechanism. Expected body:
        {"transport_mode": "<code>", "legal_disclaimer_accepted": true,
         "start_label": "...", "start_latitude": ..., "start_longitude": ...}
    """
    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    if not data.get("legal_disclaimer_accepted"):
        return JsonResponse(
            {"error": "legal_disclaimer_accepted (location consent) is required to start a journey."},
            status=400,
        )

    mode_code = data.get("transport_mode")
    if not mode_code:
        return JsonResponse({"error": "transport_mode is required."}, status=400)

    try:
        transport_mode = TransportMode.objects.get(code=mode_code, is_active=True)
    except TransportMode.DoesNotExist:
        return JsonResponse({"error": f"Unknown or inactive transport_mode '{mode_code}'."}, status=400)

    if Journey.objects.filter(user=request.user, status=Journey.Status.ACTIVE).exists():
        return JsonResponse({"error": "You already have an active journey."}, status=409)

    journey = Journey.objects.create(
        user=request.user,
        transport_mode=transport_mode,
        start_label=data.get("start_label", ""),
        start_latitude=_decimal_or_none(data.get("start_latitude")),
        start_longitude=_decimal_or_none(data.get("start_longitude")),
        legal_disclaimer_accepted=True,
        status=Journey.Status.ACTIVE,
    )

    return JsonResponse({"journey": serialize_journey(journey)}, status=201)


@_json_login_required
@require_http_methods(["POST"])
def journey_add_point(request, journey_id):
    """POST /api/journeys/<id>/points/ — add a GPS point to an active journey."""
    journey, error = _get_owned_journey_or_404(request, journey_id)
    if error:
        return error

    if journey.status != Journey.Status.ACTIVE:
        return JsonResponse({"error": "Journey is not active."}, status=409)

    data = _parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    latitude = _decimal_or_none(data.get("latitude"))
    longitude = _decimal_or_none(data.get("longitude"))
    if latitude is None or longitude is None:
        return JsonResponse({"error": "latitude and longitude are required."}, status=400)

    next_sequence = (journey.points.aggregate(Max("sequence"))["sequence__max"] or 0) + 1
    point = JourneyPoint.objects.create(
        journey=journey, sequence=next_sequence, latitude=latitude, longitude=longitude
    )

    return JsonResponse(
        {
            "point": {
                "id": point.id,
                "sequence": point.sequence,
                "latitude": str(point.latitude),
                "longitude": str(point.longitude),
                "recorded_at": point.recorded_at.isoformat(),
            }
        },
        status=201,
    )


@_json_login_required
@require_http_methods(["POST"])
def journey_stop(request, journey_id):
    """
    POST /api/journeys/<id>/stop/ — stop the journey and finalize
    distance, carbon calculations, and the SHA-256 integrity hash, then
    apply the points/streak/achievement gamification engine
    (core/services/gamification.py).
    """
    journey, error = _get_owned_journey_or_404(request, journey_id)
    if error:
        return error

    if journey.status != Journey.Status.ACTIVE:
        return JsonResponse({"error": "Journey is not active."}, status=409)

    if journey.points.count() < 2:
        return JsonResponse(
            {"error": "At least two recorded GPS points are required to finalize a journey."},
            status=400,
        )

    with transaction.atomic():
        distance_km = calculate_journey_distance_km(journey).quantize(Decimal("0.001"))
        journey.distance_km = distance_km
        journey.ended_at = timezone.now()
        journey.status = Journey.Status.COMPLETED
        journey.save(update_fields=["distance_km", "ended_at", "status"])

        try:
            finalize_journey_emissions(journey)
        except CarbonCalculationError as exc:
            transaction.set_rollback(True)
            return JsonResponse({"error": str(exc)}, status=400)

        finalize_journey_integrity_hash(journey)
        gamification_result = award_points_for_journey(journey)

    journey.refresh_from_db()
    response_body = serialize_journey(journey, include_points=True)
    response_body["points_awarded"] = gamification_result.points_awarded
    response_body["streak_days"] = gamification_result.streak_after
    response_body["achievements_unlocked"] = [a.badge_name for a in gamification_result.achievements]
    return JsonResponse({"journey": response_body})


@_json_login_required
@require_http_methods(["GET"])
def journey_detail(request, journey_id):
    """GET /api/journeys/<id>/ — return details only if the authenticated user owns it."""
    journey, error = _get_owned_journey_or_404(request, journey_id)
    if error:
        return error
    return JsonResponse({"journey": serialize_journey(journey, include_points=True)})


# -----------------------------------------------------------------------
# Transport modes & profile
# -----------------------------------------------------------------------
@_json_login_required
@require_http_methods(["GET"])
def transport_mode_list(request):
    """
    GET /api/transport-modes/ — fetch available (active) transport modes.

    ASSUMPTION: "available" is read as is_active=True, matching the
    is_active flag already on TransportMode (added in Phase 2 precisely
    to let a mode be retired without deleting historical references).
    """
    modes = TransportMode.objects.filter(is_active=True).order_by("name")
    return JsonResponse({"transport_modes": [serialize_transport_mode(m) for m in modes]})


@_json_login_required
@require_http_methods(["GET"])
def profile_detail(request):
    """
    GET /api/profile/ — the authenticated user's profile settings.

    A UserProfile is created on first access if one doesn't exist yet —
    no registration/signup flow exists in this project yet to create one
    proactively, and get_or_create here only bootstraps the model's
    already-defined defaults (0 points, 0 streaks); it does not implement
    any points/streak business logic.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return JsonResponse({"profile": serialize_user_profile(profile)})


# -----------------------------------------------------------------------
# OpenRouteService-backed endpoints
# -----------------------------------------------------------------------
def _get_configured_ors_client():
    """Return an OpenRouteServiceClient, or None if no API key is configured."""
    if not getattr(settings, "OPENROUTESERVICE_API_KEY", ""):
        return None
    return OpenRouteServiceClient()


@_json_login_required
@require_http_methods(["GET", "POST"])
def routes_view(request):
    """GET/POST /api/routes/ — calculate a route via the ORS wrapper."""
    if request.method == "GET":
        raw_coordinates = request.GET.get("coordinates")
        try:
            coordinates = json.loads(raw_coordinates) if raw_coordinates else None
        except json.JSONDecodeError:
            return JsonResponse({"error": "coordinates must be valid JSON."}, status=400)
        profile = request.GET.get("profile", "foot-walking")
    else:
        data = _parse_json_body(request)
        if data is None:
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)
        coordinates = data.get("coordinates")
        profile = data.get("profile", "foot-walking")

    if not coordinates or not isinstance(coordinates, list) or len(coordinates) < 2:
        return JsonResponse(
            {"error": "coordinates must be a list of at least two [lng, lat] pairs."}, status=400
        )

    try:
        coord_pairs = [(float(c[0]), float(c[1])) for c in coordinates]
    except (TypeError, ValueError, IndexError):
        return JsonResponse({"error": "Each coordinate must be a [lng, lat] pair of numbers."}, status=400)

    client = _get_configured_ors_client()
    if client is None:
        return JsonResponse(
            {"error": "OpenRouteService is not configured (missing OPENROUTESERVICE_API_KEY)."}, status=503
        )

    try:
        result = client.get_route(coord_pairs, profile=profile)
    except OpenRouteServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({"distance_km": result.distance_km, "duration_seconds": result.duration_seconds})


@_json_login_required
@require_http_methods(["GET", "POST"])
def geocode_view(request):
    """GET/POST /api/geocode/ — geocode (forward) or reverse-geocode via the ORS wrapper."""
    if request.method == "GET":
        data = request.GET
    else:
        data = _parse_json_body(request)
        if data is None:
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    query = data.get("query") or data.get("text")
    lat = data.get("lat")
    lon = data.get("lon")

    client = _get_configured_ors_client()
    if client is None:
        return JsonResponse(
            {"error": "OpenRouteService is not configured (missing OPENROUTESERVICE_API_KEY)."}, status=503
        )

    try:
        if query:
            result = client.geocode(query)
        elif lat is not None and lon is not None:
            result = client.reverse_geocode(float(lat), float(lon))
        else:
            return JsonResponse(
                {"error": "Provide either 'query' (forward geocoding) or 'lat'+'lon' (reverse geocoding)."},
                status=400,
            )
    except OpenRouteServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    except (TypeError, ValueError):
        return JsonResponse({"error": "lat/lon must be numbers."}, status=400)

    return JsonResponse({"latitude": result.latitude, "longitude": result.longitude, "label": result.label})
