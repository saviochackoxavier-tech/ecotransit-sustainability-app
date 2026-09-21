"""
Unit tests for core/services/: carbon calculation, ORS wrapper, and
SHA-256 integrity hashing. No network calls are made — the ORS client's
HTTP layer is mocked throughout.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import EmissionFactorSnapshot, Journey, JourneyPoint, TransportMode
from core.services.carbon import (
    CarbonCalculationError,
    calculate_carbon_saved_g,
    calculate_emissions_g,
    finalize_journey_emissions,
    get_baseline_transport_mode,
)
from core.services.integrity import (
    compute_journey_integrity_hash,
    finalize_journey_integrity_hash,
    verify_journey_integrity_hash,
)
from core.services.openroute import (
    GeocodeResult,
    OpenRouteServiceClient,
    OpenRouteServiceError,
    RouteResult,
)

User = get_user_model()


# -----------------------------------------------------------------------
# Carbon calculation engine
# -----------------------------------------------------------------------
class CarbonCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="frank", password="testpass123")
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

    def test_calculate_emissions_g(self):
        result = calculate_emissions_g(Decimal("10"), Decimal("100"))
        self.assertEqual(result, Decimal("1000"))

    def test_get_baseline_transport_mode(self):
        baseline = get_baseline_transport_mode()
        self.assertEqual(baseline, self.driving_car)

    def test_get_baseline_transport_mode_missing_raises(self):
        self.driving_car.delete()
        with self.assertRaises(CarbonCalculationError):
            get_baseline_transport_mode()

    def test_carbon_saved_positive_for_lower_emission_mode(self):
        saved = calculate_carbon_saved_g(
            distance_km=Decimal("10"),
            actual_emission_factor_g_per_km=Decimal("0"),
            baseline_emission_factor_g_per_km=Decimal("192"),
        )
        self.assertEqual(saved, Decimal("1920"))

    def test_carbon_saved_zero_when_mode_equals_baseline(self):
        saved = calculate_carbon_saved_g(
            distance_km=Decimal("10"),
            actual_emission_factor_g_per_km=Decimal("192"),
            baseline_emission_factor_g_per_km=Decimal("192"),
        )
        self.assertEqual(saved, Decimal("0"))

    def test_carbon_saved_negative_for_higher_emission_mode(self):
        """
        A mode with a higher factor than the baseline yields a negative
        "savings" figure — not clamped to zero, per design note in
        core/services/carbon.py.
        """
        saved = calculate_carbon_saved_g(
            distance_km=Decimal("10"),
            actual_emission_factor_g_per_km=Decimal("300"),
            baseline_emission_factor_g_per_km=Decimal("192"),
        )
        self.assertEqual(saved, Decimal("-1080"))

    def test_finalize_journey_emissions_creates_snapshot_and_sets_carbon_saved(self):
        journey = Journey.objects.create(
            user=self.user,
            transport_mode=self.cycling,
            distance_km=Decimal("20"),
        )
        snapshot = finalize_journey_emissions(journey)

        self.assertIsInstance(snapshot, EmissionFactorSnapshot)
        self.assertEqual(snapshot.transport_mode, self.cycling)
        self.assertEqual(snapshot.emission_factor_g_per_km, Decimal("0.000"))

        journey.refresh_from_db()
        # cycling factor 0, baseline 192 g/km, distance 20km => 3840 g saved
        self.assertEqual(journey.carbon_saved_g, Decimal("3840.000"))

    def test_finalize_journey_emissions_without_distance_raises(self):
        journey = Journey.objects.create(user=self.user, transport_mode=self.cycling)
        with self.assertRaises(CarbonCalculationError):
            finalize_journey_emissions(journey)

    def test_finalize_journey_emissions_refuses_duplicate_snapshot(self):
        journey = Journey.objects.create(
            user=self.user, transport_mode=self.cycling, distance_km=Decimal("5")
        )
        finalize_journey_emissions(journey)
        with self.assertRaises(CarbonCalculationError):
            finalize_journey_emissions(journey)

    def test_snapshot_immutable_when_live_transport_mode_factor_changes_later(self):
        """
        Historical audit integrity: once frozen, a snapshot's value must
        not drift when the live TransportMode default changes.
        """
        journey = Journey.objects.create(
            user=self.user, transport_mode=self.cycling, distance_km=Decimal("10")
        )
        finalize_journey_emissions(journey)
        journey.refresh_from_db()
        original_carbon_saved = journey.carbon_saved_g

        # Cycling suddenly gets a (hypothetical) nonzero factor.
        self.cycling.default_emission_factor_g_per_km = Decimal("50.000")
        self.cycling.save()

        snapshot = EmissionFactorSnapshot.objects.get(journey=journey)
        journey.refresh_from_db()
        self.assertEqual(snapshot.emission_factor_g_per_km, Decimal("0.000"))
        self.assertEqual(journey.carbon_saved_g, original_carbon_saved)


# -----------------------------------------------------------------------
# OpenRouteService wrapper
# -----------------------------------------------------------------------
def _mock_response(status_code=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("no JSON")
    return resp


class OpenRouteServiceClientTests(TestCase):
    def setUp(self):
        self.session = MagicMock(spec=requests.Session)
        self.client = OpenRouteServiceClient(
            api_key="test-key", base_url="https://ors.example.test", session=self.session
        )

    def test_missing_api_key_raises_before_any_request(self):
        client = OpenRouteServiceClient(api_key="", session=self.session)
        with self.assertRaises(OpenRouteServiceError):
            client.get_route([(1.0, 2.0), (3.0, 4.0)])
        self.session.request.assert_not_called()

    def test_get_route_requires_two_coordinates(self):
        with self.assertRaises(ValueError):
            self.client.get_route([(1.0, 2.0)])

    def test_get_route_success(self):
        payload = {
            "features": [
                {"properties": {"summary": {"distance": 5000, "duration": 900}}}
            ]
        }
        self.session.request.return_value = _mock_response(200, payload)

        result = self.client.get_route([(-0.1, 51.5), (-0.2, 51.6)], profile="cycling-regular")

        self.assertIsInstance(result, RouteResult)
        self.assertEqual(result.distance_km, 5.0)
        self.assertEqual(result.duration_seconds, 900)
        called_url = self.session.request.call_args.args[1]
        self.assertIn("cycling-regular", called_url)

    def test_get_route_non_200_raises(self):
        self.session.request.return_value = _mock_response(401, text="unauthorized")
        with self.assertRaises(OpenRouteServiceError):
            self.client.get_route([(1.0, 2.0), (3.0, 4.0)])

    def test_get_route_timeout_raises_ors_error(self):
        self.session.request.side_effect = requests.exceptions.Timeout("timed out")
        with self.assertRaises(OpenRouteServiceError):
            self.client.get_route([(1.0, 2.0), (3.0, 4.0)])

    def test_get_route_connection_error_raises_ors_error(self):
        self.session.request.side_effect = requests.exceptions.ConnectionError("no route to host")
        with self.assertRaises(OpenRouteServiceError):
            self.client.get_route([(1.0, 2.0), (3.0, 4.0)])

    def test_get_route_malformed_json_raises_ors_error(self):
        self.session.request.return_value = _mock_response(200, json_data=None)
        with self.assertRaises(OpenRouteServiceError):
            self.client.get_route([(1.0, 2.0), (3.0, 4.0)])

    def test_get_route_unexpected_shape_raises_ors_error(self):
        self.session.request.return_value = _mock_response(200, {"features": []})
        with self.assertRaises(OpenRouteServiceError):
            self.client.get_route([(1.0, 2.0), (3.0, 4.0)])

    def test_geocode_success(self):
        payload = {
            "features": [
                {
                    "geometry": {"coordinates": [-0.1276, 51.5074]},
                    "properties": {"label": "London, UK"},
                }
            ]
        }
        self.session.request.return_value = _mock_response(200, payload)

        result = self.client.geocode("London")

        self.assertIsInstance(result, GeocodeResult)
        self.assertEqual(result.latitude, 51.5074)
        self.assertEqual(result.longitude, -0.1276)
        self.assertEqual(result.label, "London, UK")

    def test_reverse_geocode_success(self):
        payload = {
            "features": [
                {
                    "geometry": {"coordinates": [-0.1276, 51.5074]},
                    "properties": {"label": "Somewhere near London"},
                }
            ]
        }
        self.session.request.return_value = _mock_response(200, payload)

        result = self.client.reverse_geocode(51.5074, -0.1276)

        self.assertEqual(result.label, "Somewhere near London")

    def test_reverse_geocode_timeout(self):
        self.session.request.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(OpenRouteServiceError):
            self.client.reverse_geocode(0, 0)


# -----------------------------------------------------------------------
# SHA-256 integrity hashing
# -----------------------------------------------------------------------
class IntegrityHashingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="grace", password="testpass123")
        self.mode = TransportMode.objects.create(
            code=TransportMode.Code.WALKING,
            name="Walking",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        self.journey = Journey.objects.create(
            user=self.user,
            transport_mode=self.mode,
            distance_km=Decimal("3.5"),
            carbon_saved_g=Decimal("672.000"),
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=1, latitude=Decimal("1.111111"), longitude=Decimal("2.222222")
        )
        JourneyPoint.objects.create(
            journey=self.journey, sequence=2, latitude=Decimal("3.333333"), longitude=Decimal("4.444444")
        )

    def test_hash_is_64_char_hex(self):
        digest = compute_journey_integrity_hash(self.journey)
        self.assertEqual(len(digest), 64)
        int(digest, 16)  # raises ValueError if not valid hex

    def test_hash_is_deterministic(self):
        self.assertEqual(
            compute_journey_integrity_hash(self.journey),
            compute_journey_integrity_hash(self.journey),
        )

    def test_hash_changes_if_distance_changes(self):
        original = compute_journey_integrity_hash(self.journey)
        self.journey.distance_km = Decimal("99.0")
        changed = compute_journey_integrity_hash(self.journey)
        self.assertNotEqual(original, changed)

    def test_hash_changes_if_carbon_saved_changes(self):
        original = compute_journey_integrity_hash(self.journey)
        self.journey.carbon_saved_g = Decimal("1.000")
        changed = compute_journey_integrity_hash(self.journey)
        self.assertNotEqual(original, changed)

    def test_hash_changes_if_a_journey_point_is_tampered_with(self):
        """Tamper detection: altering a GPS point changes the hash."""
        original = compute_journey_integrity_hash(self.journey)
        point = self.journey.points.get(sequence=1)
        point.latitude = Decimal("0.000001")
        point.save()
        self.journey.refresh_from_db()
        changed = compute_journey_integrity_hash(self.journey)
        self.assertNotEqual(original, changed)

    def test_hash_changes_if_a_point_is_added(self):
        original = compute_journey_integrity_hash(self.journey)
        JourneyPoint.objects.create(
            journey=self.journey, sequence=3, latitude=Decimal("5.0"), longitude=Decimal("6.0")
        )
        changed = compute_journey_integrity_hash(self.journey)
        self.assertNotEqual(original, changed)

    def test_hash_unaffected_by_journey_id_or_transport_mode(self):
        """
        The spec's field list names "user ID", not "journey ID", and does
        not name transport mode — confirm those are excluded from the
        hash input as designed.
        """
        other_mode = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING,
            name="Cycling",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        clone = Journey.objects.create(
            user=self.user,
            transport_mode=other_mode,
            distance_km=self.journey.distance_km,
            carbon_saved_g=self.journey.carbon_saved_g,
        )
        # started_at is auto_now_add=True, so Journey.objects.create()
        # silently ignores any started_at kwarg and stamps "now" instead.
        # QuerySet.update() bypasses that (it doesn't call save()/pre_save()),
        # letting the test force clone.started_at/ended_at to match exactly.
        Journey.objects.filter(pk=clone.pk).update(
            started_at=self.journey.started_at,
            ended_at=self.journey.ended_at,
        )
        clone.refresh_from_db()

        for p in self.journey.points.all():
            JourneyPoint.objects.create(
                journey=clone, sequence=p.sequence, latitude=p.latitude, longitude=p.longitude
            )
        self.assertNotEqual(self.journey.pk, clone.pk)
        self.assertEqual(
            compute_journey_integrity_hash(self.journey),
            compute_journey_integrity_hash(clone),
        )

    def test_hash_stable_across_fresh_instance_and_db_reload(self):
        """
        Regression test: a Decimal assigned in Python (e.g. Decimal("3.5"))
        and the same value re-read from the database (Decimal("3.500"), per
        the field's decimal_places=3) must hash identically — the hash must
        depend on the actual numeric value, not on object provenance.
        """
        fresh_hash = compute_journey_integrity_hash(self.journey)
        reloaded = Journey.objects.get(pk=self.journey.pk)
        reloaded_hash = compute_journey_integrity_hash(reloaded)
        self.assertEqual(fresh_hash, reloaded_hash)

    def test_verify_returns_false_when_no_hash_stored(self):
        self.assertEqual(self.journey.integrity_hash, "")
        self.assertFalse(verify_journey_integrity_hash(self.journey))

    def test_finalize_persists_hash_and_verify_passes(self):
        digest = finalize_journey_integrity_hash(self.journey)
        self.journey.refresh_from_db()
        self.assertEqual(self.journey.integrity_hash, digest)
        self.assertTrue(verify_journey_integrity_hash(self.journey))

    def test_verify_fails_after_tampering_post_finalization(self):
        finalize_journey_integrity_hash(self.journey)
        self.journey.distance_km = Decimal("1000")
        self.journey.save(update_fields=["distance_km"])
        self.assertFalse(verify_journey_integrity_hash(self.journey))
