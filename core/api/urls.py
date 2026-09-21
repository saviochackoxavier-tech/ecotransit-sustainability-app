"""
URL configuration for the core JSON API. Included at /api/ by
ecotransit/urls.py. Endpoint paths match spec §26's table exactly.
"""

from django.urls import path

from core.api import exports, views

app_name = "core_api"

urlpatterns = [
    path("journeys/", views.journey_list, name="journey-list"),
    path("journeys/start/", views.journey_start, name="journey-start"),
    path("journeys/<int:journey_id>/points/", views.journey_add_point, name="journey-add-point"),
    path("journeys/<int:journey_id>/stop/", views.journey_stop, name="journey-stop"),
    path("journeys/<int:journey_id>/", views.journey_detail, name="journey-detail"),
    path("transport-modes/", views.transport_mode_list, name="transport-mode-list"),
    path("profile/", views.profile_detail, name="profile-detail"),
    path("routes/", views.routes_view, name="routes"),
    path("geocode/", views.geocode_view, name="geocode"),
    path("export/journeys.csv", exports.export_journeys_csv, name="export-journeys-csv"),
    path("export/journeys.json", exports.export_journeys_json, name="export-journeys-json"),
    path("export/journeys.pdf", exports.export_journeys_pdf, name="export-journeys-pdf"),
]
