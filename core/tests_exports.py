"""
Tests for Phase 6: export endpoints (CSV/JSON/PDF) and the custom admin
analytics view.
"""

import csv
import io
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Journey, TransportMode

User = get_user_model()


class ExportTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="exportuser1", password="testpass123")
        self.user2 = User.objects.create_user(username="exportuser2", password="testpass123")

        self.cycling = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING,
            name="Cycling",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )

        self.journey1 = Journey.objects.create(
            user=self.user1,
            transport_mode=self.cycling,
            status=Journey.Status.COMPLETED,
            distance_km=Decimal("5.500"),
            carbon_saved_g=Decimal("1056.000"),
            integrity_hash="a" * 64,
            legal_disclaimer_accepted=True,
        )
        self.journey2 = Journey.objects.create(
            user=self.user1,
            transport_mode=self.cycling,
            status=Journey.Status.ACTIVE,
        )
        # Belongs to a different user — must never appear in user1's export.
        self.other_journey = Journey.objects.create(
            user=self.user2,
            transport_mode=self.cycling,
            status=Journey.Status.COMPLETED,
            distance_km=Decimal("99.000"),
        )

        self.client = Client()
        self.client.login(username="exportuser1", password="testpass123")


class CsvExportTests(ExportTestCase):
    def test_requires_authentication(self):
        anon = Client()
        response = anon.get(reverse("core_api:export-journeys-csv"))
        self.assertEqual(response.status_code, 401)

    def test_returns_csv_with_attachment_header(self):
        response = self.client.get(reverse("core_api:export-journeys-csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("exportuser1", response["Content-Disposition"])

    def test_csv_is_parseable_and_scoped_to_owner(self):
        response = self.client.get(reverse("core_api:export-journeys-csv"))
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        ids = {row["id"] for row in rows}
        self.assertEqual(ids, {str(self.journey1.id), str(self.journey2.id)})
        self.assertNotIn(str(self.other_journey.id), ids)

    def test_csv_contains_expected_fields(self):
        response = self.client.get(reverse("core_api:export-journeys-csv"))
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        row = next(r for r in rows if r["id"] == str(self.journey1.id))
        self.assertEqual(row["transport_mode"], "Cycling")
        self.assertEqual(row["distance_km"], "5.500")
        self.assertEqual(row["carbon_saved_g"], "1056.000")
        self.assertEqual(row["integrity_hash"], "a" * 64)


class JsonExportTests(ExportTestCase):
    def test_requires_authentication(self):
        anon = Client()
        response = anon.get(reverse("core_api:export-journeys-json"))
        self.assertEqual(response.status_code, 401)

    def test_returns_json_with_attachment_header(self):
        response = self.client.get(reverse("core_api:export-journeys-json"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_json_body_scoped_to_owner(self):
        response = self.client.get(reverse("core_api:export-journeys-json"))
        payload = json.loads(response.content)
        self.assertEqual(payload["user"], "exportuser1")
        ids = {j["id"] for j in payload["journeys"]}
        self.assertEqual(ids, {self.journey1.id, self.journey2.id})
        self.assertNotIn(self.other_journey.id, ids)


class PdfExportTests(ExportTestCase):
    def test_requires_authentication(self):
        anon = Client()
        response = anon.get(reverse("core_api:export-journeys-pdf"))
        self.assertEqual(response.status_code, 401)

    def test_returns_valid_pdf(self):
        response = self.client.get(reverse("core_api:export-journeys-pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_pdf_generation_with_zero_journeys(self):
        """Edge case: a user with no journeys still gets a valid (empty) PDF."""
        empty_user = User.objects.create_user(username="noeco", password="testpass123")
        client = Client()
        client.login(username="noeco", password="testpass123")
        response = client.get(reverse("core_api:export-journeys-pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_csv_generation_with_zero_journeys(self):
        empty_user = User.objects.create_user(username="noeco2", password="testpass123")
        client = Client()
        client.login(username="noeco2", password="testpass123")
        response = client.get(reverse("core_api:export-journeys-csv"))
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(rows, [])


class AdminAnalyticsTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(username="regularuser", password="testpass123")

        self.cycling = TransportMode.objects.create(
            code=TransportMode.Code.CYCLING,
            name="Cycling",
            default_emission_factor_g_per_km=Decimal("0.000"),
        )
        self.driving = TransportMode.objects.create(
            code=TransportMode.Code.DRIVING_CAR,
            name="Driving / Car",
            default_emission_factor_g_per_km=Decimal("192.000"),
        )

        Journey.objects.create(
            user=self.regular_user,
            transport_mode=self.cycling,
            status=Journey.Status.COMPLETED,
            carbon_saved_g=Decimal("500.000"),
        )
        Journey.objects.create(
            user=self.regular_user,
            transport_mode=self.cycling,
            status=Journey.Status.COMPLETED,
            carbon_saved_g=Decimal("300.000"),
        )
        Journey.objects.create(user=self.regular_user, transport_mode=self.driving, status=Journey.Status.ACTIVE)

    def test_anonymous_redirected_to_admin_login(self):
        response = Client().get("/admin/analytics/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_non_staff_user_denied(self):
        client = Client()
        client.login(username="regularuser", password="testpass123")
        response = client.get("/admin/analytics/")
        # admin_view() redirects non-staff users to the admin login page
        # rather than rendering the page for them.
        self.assertEqual(response.status_code, 302)

    def test_staff_user_sees_correct_aggregates(self):
        client = Client()
        client.login(username="staffuser", password="testpass123")
        response = client.get("/admin/analytics/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_journeys"], 3)
        self.assertEqual(response.context["active_journeys"], 1)
        self.assertEqual(response.context["completed_journeys"], 2)
        self.assertEqual(response.context["total_carbon_saved_g"], Decimal("800.000"))

        distribution = {row["transport_mode__name"]: row["count"] for row in response.context["mode_distribution"]}
        self.assertEqual(distribution["Cycling"], 2)
        self.assertEqual(distribution["Driving / Car"], 1)

    def test_analytics_page_renders_without_template_errors(self):
        client = Client()
        client.login(username="staffuser", password="testpass123")
        response = client.get("/admin/analytics/")
        self.assertContains(response, "Platform overview")
        self.assertContains(response, "Cycling")

    def test_analytics_with_no_journeys_at_all(self):
        """Edge case: aggregate queries must not crash on an empty dataset."""
        Journey.objects.all().delete()
        client = Client()
        client.login(username="staffuser", password="testpass123")
        response = client.get("/admin/analytics/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_carbon_saved_g"], 0)
        self.assertEqual(response.context["total_journeys"], 0)
