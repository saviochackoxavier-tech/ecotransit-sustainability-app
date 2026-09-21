"""
OpenRouteService (ORS) integration wrapper.

Spec (Phase 3 execution prompt): "Create a robust backend wrapper
class/functions for routing and geocoding using OPENROUTESERVICE_API_KEY
from environment variables. Handle network exceptions, timeouts, and
fallback handling gracefully."

This is a service-layer client only — nothing here is wired into a view
or API endpoint (spec §26's `/api/routes/` and `/api/geocode/` endpoints
are a later phase's responsibility). No live network calls are made in
this project's test suite; tests mock the HTTP layer.

ASSUMPTION: the v2.1.1 spec text available at implementation time names
OpenRouteService as the routing/geocoding provider but does not itemize
exact endpoint paths or routing profiles. This wrapper follows ORS's
public API (https://openrouteservice.org/dev/#/api-docs) as of this
writing: POST /v2/directions/{profile}/geojson for routing, and
GET /geocode/search / /geocode/reverse for geocoding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings


class OpenRouteServiceError(Exception):
    """
    Raised for any ORS failure: missing API key, network/timeout errors,
    a non-200 response, or an unexpected response shape. Callers get one
    exception type to handle regardless of failure cause — this is the
    "fallback handling gracefully" behavior: a caller can catch this one
    exception and decide how to degrade (e.g. ask the user to enter
    distance manually) rather than crash on an unhandled network error.
    """


@dataclass
class RouteResult:
    distance_km: float
    duration_seconds: float
    raw_response: dict[str, Any]


@dataclass
class GeocodeResult:
    latitude: float
    longitude: float
    label: str
    raw_response: dict[str, Any]


class OpenRouteServiceClient:
    """Thin, mockable wrapper around the OpenRouteService HTTP API."""

    DEFAULT_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        session: requests.Session | None = None,
        timeout_seconds: float | None = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "OPENROUTESERVICE_API_KEY", "")
        self.base_url = (
            base_url or getattr(settings, "OPENROUTESERVICE_BASE_URL", "https://api.openrouteservice.org")
        ).rstrip("/")
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise OpenRouteServiceError(
                "OPENROUTESERVICE_API_KEY is not configured. Set it in the environment "
                "before calling the ORS API."
            )
        return self.api_key

    def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """
        Shared request/error-handling path so every public method degrades
        the same way: network errors, timeouts, bad status codes, and
        malformed JSON all surface as OpenRouteServiceError.
        """
        try:
            response = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
        except requests.exceptions.Timeout as exc:
            raise OpenRouteServiceError(f"ORS request to {url} timed out after {self.timeout_seconds}s.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise OpenRouteServiceError(f"ORS request to {url} failed: connection error.") from exc
        except requests.exceptions.RequestException as exc:
            raise OpenRouteServiceError(f"ORS request to {url} failed: {exc}") from exc

        if response.status_code != 200:
            raise OpenRouteServiceError(
                f"ORS request to {url} failed ({response.status_code}): {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise OpenRouteServiceError(f"ORS response from {url} was not valid JSON.") from exc

    def get_route(self, coordinates: list[tuple[float, float]], profile: str = "foot-walking") -> RouteResult:
        """
        coordinates: list of (longitude, latitude) pairs — ORS's expected
        coordinate order, not (latitude, longitude).
        profile: an ORS routing profile, e.g. "foot-walking",
        "cycling-regular", "driving-car".
        """
        if len(coordinates) < 2:
            raise ValueError("At least two coordinates (start and end) are required.")

        api_key = self._require_api_key()
        url = f"{self.base_url}/v2/directions/{profile}/geojson"
        payload = {"coordinates": [[lng, lat] for lng, lat in coordinates]}
        headers = {"Authorization": api_key, "Content-Type": "application/json"}

        data = self._request("POST", url, json=payload, headers=headers)

        try:
            summary = data["features"][0]["properties"]["summary"]
            distance_km = summary["distance"] / 1000
            duration_seconds = summary["duration"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouteServiceError(f"Unexpected ORS routing response shape: {exc}") from exc

        return RouteResult(distance_km=distance_km, duration_seconds=duration_seconds, raw_response=data)

    def geocode(self, query: str) -> GeocodeResult:
        api_key = self._require_api_key()
        url = f"{self.base_url}/geocode/search"
        params = {"api_key": api_key, "text": query}

        data = self._request("GET", url, params=params)
        return self._parse_geocode_response(data, fallback_label=query)

    def reverse_geocode(self, latitude: float, longitude: float) -> GeocodeResult:
        api_key = self._require_api_key()
        url = f"{self.base_url}/geocode/reverse"
        params = {"api_key": api_key, "point.lat": latitude, "point.lon": longitude}

        data = self._request("GET", url, params=params)
        return self._parse_geocode_response(data, fallback_label="")

    @staticmethod
    def _parse_geocode_response(data: dict[str, Any], fallback_label: str) -> GeocodeResult:
        try:
            feature = data["features"][0]
            lng, lat = feature["geometry"]["coordinates"]
            label = feature["properties"].get("label", fallback_label)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenRouteServiceError(f"Unexpected ORS geocoding response shape: {exc}") from exc

        return GeocodeResult(latitude=lat, longitude=lng, label=label, raw_response=data)
