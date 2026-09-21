"""
URL configuration for the HTML frontend (Phase 5). Distinct from
core/api/urls.py, which serves the JSON API.
"""

from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("track/", views.tracking, name="track"),
    path("journeys/", views.journey_history_list, name="journey-history-list"),
    path("journeys/<int:pk>/", views.journey_history_detail, name="journey-history-detail"),
    path("profile/", views.profile_view, name="profile"),
]
