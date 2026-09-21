"""
Tests for core/api/: journey management endpoints, ORS-backed endpoints,
authentication/ownership enforcement, and the security rule that
client-supplied user IDs must never determine ownership.
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.models import Journey, JourneyPoint, TransportMode, UserProfile
from core.services.integrity import verify_journey_integrity_hash
from core.services.openroute import GeocodeResult, OpenRouteServiceError, RouteResult

User = get_user_model()


def _post(client, url, data=None):
    return client.post(url, data=json.dumps(data or {}), content_type="application/json")


class ApiTestCase(TestCase):
    """Common fixtures: two users, a full mode set, one client logged in as user 1."""

    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", password="testpass123")

        self.driving_car = TransportMode.objects.create(
            code=TransportMode.Code.DRIVING_CAR,
            name="Driving / Car",
            default_emission_factor_g_per_km=Decimal("192.000"),
        )
        self.cycling = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING,
            name="Cycling",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        self.inactive_mode = TransportMode.objects.create(
            code=TransportMode.Code.ELECTRIC_VEHICLE,
            name="Electric Vehicle",
            default_emission_factor_g_per_km=Decimal("53.000"),
            is_active=False,
        )

        self.client = Client()
        self.client.login(username="user1", password="testpass123")

        self.other_client = Client()
        self.other_client.login(username="user2", password="testpass123")


# -----------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------
class AuthenticationTests(ApiTestCase):
    def test_all_endpoints_require_authentication(self):
        anon = Client()
        endpoints = [
            ("get", reverse("core_api:journey-list")),
            ("post", reverse("core_api:journey-start")),
            ("get", reverse("core_api:routes")),
            ("get", reverse("core_api:geocode")),
        ]
        for method, url in endpoints:
            response = getattr(anon, method)(url)
            self.assertEqual(response.status_code, 401, f"{method.upper()} {url} should require auth")

    def test_journey_detail_and_points_and_stop_require_authentication(self):
        journey = Journey.objects.create(user=self.user1, transport_mode=self.cycling)
        anon = Client()
        self.assertEqual(anon.get(reverse("core_api:journey-detail", args=[journey.id])).status_code, 401)
        self.assertEqual(anon.post(reverse("core_api:journey-add-point", args=[journey.id])).status_code, 401)
        self.assertEqual(anon.post(reverse("core_api:journey-stop", args=[journey.id])).status_code, 401)


# -----------------------------------------------------------------------
# journey_start
# -----------------------------------------------------------------------
class JourneyStartTests(ApiTestCase):
    def test_missing_consent_rejected(self):
        response = _post(
            self.client, reverse("core_api:journey-start"), {"transport_mode": "cycling"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("legal_disclaimer_accepted", response.json()["error"])

    def test_missing_transport_mode_rejected(self):
        response = _post(
            self.client,
            reverse("core_api:journey-start"),
            {"legal_disclaimer_accepted": True},
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_transport_mode_rejected(self):
        response = _post(
            self.client,
            reverse("core_api:journey-start"),
            {"legal_disclaimer_accepted": True, "transport_mode": "teleportation"},
        )
        self.assertEqual(response.status_code, 400)

    def test_inactive_transport_mode_rejected(self):
        response = _post(
            self.client,
            reverse("core_api:journey-start"),
            {"legal_disclaimer_accepted": True, "transport_mode": "electric_vehicle"},
        )
        self.assertEqual(response.status_code, 400)

    def test_successful_start(self):
        response = _post(
            self.client,
            reverse("core_api:journey-start"),
            {"legal_disclaimer_accepted": True, "transport_mode": "cycling", "start_label": "Home"},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["journey"]
        self.assertEqual(body["status"], "active")
        self.assertEqual(body["transport_mode"]["code"], "cycling")
        self.assertEqual(body["start_label"], "Home")
        self.assertTrue(body["legal_disclaimer_accepted"])

        journey = Journey.objects.get(pk=body["id"])
        self.assertEqual(journey.user, self.user1)

    def test_second_active_journey_rejected(self):
        Journey.objects.create(user=self.user1, transport_mode=self.cycling, status=Journey.Status.ACTIVE)
        response = _post(
            self.client,
            reverse("core_api:journey-start"),
            {"legal_disclaimer_accepted": True, "transport_mode": "cycling"},
        )
        self.assertEqual(response.status_code, 409)

    def test_completed_journey_does_not_block_new_start(self):
        Journey.objects.create(user=self.user1, transport_mode=self.cycling, status=Journey.Status.COMPLETED)
        response = _post(
            self.client,
            reverse("core_api:journey-start"),
            {"legal_disclaimer_accepted": True, "transport_mode": "cycling"},
        )
        self.assertEqual(response.status_code, 201)

    def test_client_supplied_user_id_is_ignored(self):
        """
        Security rule: ownership must always be derived from the
        authenticated session, never from client-supplied data.
        """
        response = _post(
            self.client,
            reverse("core_api:journey-start"),
            {
                "legal_disclaimer_accepted": True,
                "transport_mode": "cycling",
                "user": self.user2.id,
                "user_id": self.user2.id,
            },
        )
        self.assertEqual(response.status_code, 201)
        journey = Journey.objects.get(pk=response.json()["journey"]["id"])
        self.assertEqual(journey.user, self.user1)
        self.assertNotEqual(journey.user, self.user2)

    def test_malformed_json_body_rejected(self):
        response = self.client.post(
            reverse("core_api:journey-start"), data="not-json-{{{", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_non_object_json_body_rejected(self):
        response = self.client.post(
            reverse("core_api:journey-start"), data="[1, 2, 3]", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_get_method_not_allowed_on_start(self):
        response = self.client.get(reverse("core_api:journey-start"))
        self.assertEqual(response.status_code, 405)

    def test_post_method_not_allowed_on_journey_list(self):
        response = _post(self.client, reverse("core_api:journey-list"), {})
        self.assertEqual(response.status_code, 405)


# -----------------------------------------------------------------------
# journey_add_point
# -----------------------------------------------------------------------
class JourneyAddPointTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.journey = Journey.objects.create(
            user=self.user1, transport_mode=self.cycling, status=Journey.Status.ACTIVE
        )

    def test_add_point_success_and_sequence_autoincrement(self):
        url = reverse("core_api:journey-add-point", args=[self.journey.id])
        r1 = _post(self.client, url, {"latitude": "1.0", "longitude": "2.0"})
        r2 = _post(self.client, url, {"latitude": "3.0", "longitude": "4.0"})
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.json()["point"]["sequence"], 1)
        self.assertEqual(r2.json()["point"]["sequence"], 2)
        self.assertEqual(self.journey.points.count(), 2)

    def test_missing_coordinates_rejected(self):
        response = _post(
            self.client, reverse("core_api:journey-add-point", args=[self.journey.id]), {"latitude": "1.0"}
        )
        self.assertEqual(response.status_code, 400)

    def test_add_point_to_completed_journey_rejected(self):
        self.journey.status = Journey.Status.COMPLETED
        self.journey.save()
        response = _post(
            self.client,
            reverse("core_api:journey-add-point", args=[self.journey.id]),
            {"latitude": "1.0", "longitude": "2.0"},
        )
        self.assertEqual(response.status_code, 409)

    def test_non_owner_gets_404(self):
        response = _post(
            self.other_client,
            reverse("core_api:journey-add-point", args=[self.journey.id]),
            {"latitude": "1.0", "longitude": "2.0"},
        )
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_journey_gets_404(self):
        response = _post(
            self.client,
            reverse("core_api:journey-add-point", args=[999999]),
            {"latitude": "1.0", "longitude": "2.0"},
        )
        self.assertEqual(response.status_code, 404)


# -----------------------------------------------------------------------
# journey_stop
# -----------------------------------------------------------------------
class JourneyStopTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.journey = Journey.objects.create(
            user=self.user1, transport_mode=self.cycling, status=Journey.Status.ACTIVE
        )

    def test_stop_requires_at_least_two_points(self):
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("51.5"), longitude=Decimal("-0.1")
        )
        response = _post(self.client, reverse("core_api:journey-stop", args=[self.journey.id]))
        self.assertEqual(response.status_code, 400)

    def test_stop_success_finalizes_journey(self):
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("51.5074"), longitude=Decimal("-0.1278")
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=2, latitude=Decimal("51.5155"), longitude=Decimal("-0.1410")
        )

        response = _post(self.client, reverse("core_api:journey-stop", args=[self.journey.id]))
        self.assertEqual(response.status_code, 200)

        body = response.json()["journey"]
        self.assertEqual(body["status"], "completed")
        self.assertIsNotNone(body["ended_at"])
        self.assertIsNotNone(body["distance_km"])
        self.assertGreater(Decimal(body["distance_km"]), Decimal("0"))
        self.assertIsNotNone(body["carbon_saved_g"])
        self.assertEqual(len(body["integrity_hash"]), 64)

        self.journey.refresh_from_db()
        self.assertTrue(verify_journey_integrity_hash(self.journey))
        self.assertTrue(hasattr(self.journey, "emission_snapshot"))

    def test_stop_awards_points_and_first_journey_badge(self):
        """
        End-to-end: /stop/ wires into the gamification engine
        (core/services/gamification.py) and reports the result.
        """
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("51.5074"), longitude=Decimal("-0.1278")
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=2, latitude=Decimal("51.5155"), longitude=Decimal("-0.1410")
        )

        response = _post(self.client, reverse("core_api:journey-stop", args=[self.journey.id]))
        self.assertEqual(response.status_code, 200)
        body = response.json()["journey"]

        self.assertIn("points_awarded", body)
        self.assertGreater(body["points_awarded"], 0)
        self.assertEqual(body["streak_days"], 1)
        self.assertIn("First Steps", body["achievements_unlocked"])

        profile = UserProfile.objects.get(user=self.user1)
        self.assertEqual(profile.total_points, body["points_awarded"])
        self.assertEqual(profile.current_streak_days, 1)

    def test_stop_already_completed_journey_rejected(self):
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("1.0"), longitude=Decimal("1.0")
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=2, latitude=Decimal("2.0"), longitude=Decimal("2.0")
        )
        url = reverse("core_api:journey-stop", args=[self.journey.id])
        first = _post(self.client, url)
        self.assertEqual(first.status_code, 200)
        second = _post(self.client, url)
        self.assertEqual(second.status_code, 409)

    def test_stop_with_identical_points_yields_zero_distance_without_error(self):
        """
        Edge case (Phase 6 polish pass): two recorded points at the exact
        same coordinates must not crash distance/carbon calculation —
        distance and carbon saved should both come out to zero.
        """
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("51.5"), longitude=Decimal("-0.1")
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=2, latitude=Decimal("51.5"), longitude=Decimal("-0.1")
        )
        response = _post(self.client, reverse("core_api:journey-stop", args=[self.journey.id]))
        self.assertEqual(response.status_code, 200)
        body = response.json()["journey"]
        self.assertEqual(Decimal(body["distance_km"]), Decimal("0.000"))
        self.assertEqual(Decimal(body["carbon_saved_g"]), Decimal("0.000"))

    def test_non_owner_gets_404(self):
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("1.0"), longitude=Decimal("1.0")
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=2, latitude=Decimal("2.0"), longitude=Decimal("2.0")
        )
        response = _post(self.other_client, reverse("core_api:journey-stop", args=[self.journey.id]))
        self.assertEqual(response.status_code, 404)


# -----------------------------------------------------------------------
# journey_detail / journey_list
# -----------------------------------------------------------------------
class JourneyDetailAndListTests(ApiTestCase):
    def test_owner_can_view_detail(self):
        journey = Journey.objects.create(user=self.user1, transport_mode=self.cycling)
        response = self.client.get(reverse("core_api:journey-detail", args=[journey.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["journey"]["id"], journey.id)

    def test_non_owner_gets_404_not_403(self):
        """Spec-consistent choice: 404 avoids confirming the ID exists."""
        journey = Journey.objects.create(user=self.user1, transport_mode=self.cycling)
        response = self.other_client.get(reverse("core_api:journey-detail", args=[journey.id]))
        self.assertEqual(response.status_code, 404)

    def test_list_returns_only_own_journeys(self):
        Journey.objects.create(user=self.user1, transport_mode=self.cycling)
        Journey.objects.create(user=self.user1, transport_mode=self.cycling)
        Journey.objects.create(user=self.user2, transport_mode=self.cycling)

        response = self.client.get(reverse("core_api:journey-list"))
        self.assertEqual(response.status_code, 200)
        journeys = response.json()["journeys"]
        self.assertEqual(len(journeys), 2)
        for j in journeys:
            self.assertNotEqual(j["id"], Journey.objects.filter(user=self.user2).first().id)


# -----------------------------------------------------------------------
# transport_mode_list / profile_detail
# -----------------------------------------------------------------------
class TransportModeListTests(ApiTestCase):
    def test_requires_authentication(self):
        anon = Client()
        response = anon.get(reverse("core_api:transport-mode-list"))
        self.assertEqual(response.status_code, 401)

    def test_returns_only_active_modes(self):
        response = self.client.get(reverse("core_api:transport-mode-list"))
        self.assertEqual(response.status_code, 200)
        codes = {m["code"] for m in response.json()["transport_modes"]}
        self.assertIn("driving_car", codes)
        self.assertIn("cycling", codes)
        self.assertNotIn("electric_vehicle", codes)  # inactive in setUp


class ProfileDetailTests(ApiTestCase):
    def test_requires_authentication(self):
        anon = Client()
        response = anon.get(reverse("core_api:profile-detail"))
        self.assertEqual(response.status_code, 401)

    def test_creates_profile_on_first_access_with_defaults(self):
        self.assertFalse(UserProfile.objects.filter(user=self.user1).exists())
        response = self.client.get(reverse("core_api:profile-detail"))
        self.assertEqual(response.status_code, 200)
        profile = response.json()["profile"]
        self.assertEqual(profile["total_points"], 0)
        self.assertEqual(profile["current_streak_days"], 0)
        self.assertEqual(profile["longest_streak_days"], 0)
        self.assertIsNone(profile["preferred_transport_mode"])
        self.assertTrue(UserProfile.objects.filter(user=self.user1).exists())

    def test_returns_own_profile_only(self):
        UserProfile.objects.create(user=self.user1, total_points=42)
        UserProfile.objects.create(user=self.user2, total_points=999)

        response = self.client.get(reverse("core_api:profile-detail"))
        self.assertEqual(response.json()["profile"]["total_points"], 42)

    def test_includes_preferred_transport_mode_when_set(self):
        UserProfile.objects.create(user=self.user1, preferred_transport_mode=self.cycling)
        response = self.client.get(reverse("core_api:profile-detail"))
        self.assertEqual(response.json()["profile"]["preferred_transport_mode"]["code"], "cycling")


# -----------------------------------------------------------------------
# routes_view / geocode_view (ORS wrapper mocked — no live network calls)
# -----------------------------------------------------------------------
@override_settings(OPENROUTESERVICE_API_KEY="test-key")
class RoutesEndpointTests(ApiTestCase):
    def test_missing_coordinates_rejected(self):
        response = _post(self.client, reverse("core_api:routes"), {})
        self.assertEqual(response.status_code, 400)

    def test_single_coordinate_rejected(self):
        response = _post(self.client, reverse("core_api:routes"), {"coordinates": [[1.0, 2.0]]})
        self.assertEqual(response.status_code, 400)

    @patch("core.api.views.OpenRouteServiceClient")
    def test_successful_route_calculation(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get_route.return_value = RouteResult(
            distance_km=5.2, duration_seconds=1200, raw_response={}
        )
        mock_client_cls.return_value = mock_client

        response = _post(
            self.client,
            reverse("core_api:routes"),
            {"coordinates": [[-0.1, 51.5], [-0.2, 51.6]], "profile": "cycling-regular"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"distance_km": 5.2, "duration_seconds": 1200})
        mock_client.get_route.assert_called_once()

    @patch("core.api.views.OpenRouteServiceClient")
    def test_ors_failure_returns_502(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get_route.side_effect = OpenRouteServiceError("ORS timed out")
        mock_client_cls.return_value = mock_client

        response = _post(
            self.client, reverse("core_api:routes"), {"coordinates": [[-0.1, 51.5], [-0.2, 51.6]]}
        )
        self.assertEqual(response.status_code, 502)

    def test_missing_api_key_returns_503(self):
        with override_settings(OPENROUTESERVICE_API_KEY=""):
            response = _post(
                self.client, reverse("core_api:routes"), {"coordinates": [[-0.1, 51.5], [-0.2, 51.6]]}
            )
        self.assertEqual(response.status_code, 503)


@override_settings(OPENROUTESERVICE_API_KEY="test-key")
class GeocodeEndpointTests(ApiTestCase):
    def test_missing_query_and_coordinates_rejected(self):
        response = _post(self.client, reverse("core_api:geocode"), {})
        self.assertEqual(response.status_code, 400)

    @patch("core.api.views.OpenRouteServiceClient")
    def test_forward_geocode_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.geocode.return_value = GeocodeResult(
            latitude=51.5074, longitude=-0.1278, label="London, UK", raw_response={}
        )
        mock_client_cls.return_value = mock_client

        response = _post(self.client, reverse("core_api:geocode"), {"query": "London"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["label"], "London, UK")

    @patch("core.api.views.OpenRouteServiceClient")
    def test_reverse_geocode_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.reverse_geocode.return_value = GeocodeResult(
            latitude=51.5074, longitude=-0.1278, label="Near London", raw_response={}
        )
        mock_client_cls.return_value = mock_client

        response = _post(self.client, reverse("core_api:geocode"), {"lat": 51.5074, "lon": -0.1278})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["label"], "Near London")

    @patch("core.api.views.OpenRouteServiceClient")
    def test_ors_failure_returns_502(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.geocode.side_effect = OpenRouteServiceError("connection error")
        mock_client_cls.return_value = mock_client

        response = _post(self.client, reverse("core_api:geocode"), {"query": "Nowhere"})
        self.assertEqual(response.status_code, 502)

    def test_missing_api_key_returns_503(self):
        with override_settings(OPENROUTESERVICE_API_KEY=""):
            response = _post(self.client, reverse("core_api:geocode"), {"query": "London"})
        self.assertEqual(response.status_code, 503)
