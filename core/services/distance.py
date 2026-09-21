"""
Great-circle distance calculation for a journey's recorded GPS points.

ASSUMPTION: the spec names "total distance" as a Journey field (§3) but
does not specify how distance is derived from recorded GPS points. The
haversine formula (great-circle distance) is used here as the standard
approach for two lat/lng points. This is a mechanical geometry
calculation, not one of the frozen business-methodology decisions named
in the governing instruction (carbon methodology, point/streak logic,
etc.), so it is implemented directly rather than deferred.
"""

from __future__ import annotations

from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from core.models import Journey

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> Decimal:
    """Great-circle distance in km between two lat/lng points."""
    lat1_r, lon1_r, lat2_r, lon2_r = (radians(float(v)) for v in (lat1, lon1, lat2, lon2))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return Decimal(str(EARTH_RADIUS_KM * c))


def calculate_journey_distance_km(journey: Journey) -> Decimal:
    """
    Sum of consecutive great-circle distances between the journey's
    recorded points, ordered by sequence. Returns Decimal("0") if fewer
    than two points exist.
    """
    points = list(journey.points.order_by("sequence").values_list("latitude", "longitude"))
    if len(points) < 2:
        return Decimal("0")

    total = Decimal("0")
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        total += haversine_km(lat1, lon1, lat2, lon2)
    return total
