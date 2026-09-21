"""
HTML page views for the EcoTransit frontend (Phase 5).

These render templates and use Django's standard @login_required, which
redirects an unauthenticated browser to the login page — unlike
core/api/views.py's JSON 401 behavior, which is correct for an API
client rather than a browser.

No data is written here beyond what get_or_create already does elsewhere
(UserProfile bootstrapping, matching core/api/views.py's profile_detail).
All journey/points/stop actions happen client-side against the Phase 4
JSON API — these views only render the pages and their initial state.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from core.models import Journey, TransportMode, UserProfile


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    recent_journeys = Journey.objects.filter(user=request.user).order_by("-started_at")[:5]
    active_journey = Journey.objects.filter(user=request.user, status=Journey.Status.ACTIVE).first()
    total_journeys = Journey.objects.filter(user=request.user).count()
    total_carbon_saved_g = sum(
        (j.carbon_saved_g for j in Journey.objects.filter(user=request.user) if j.carbon_saved_g is not None),
        start=Decimal("0"),
    )

    context = {
        "profile": profile,
        "recent_journeys": recent_journeys,
        "active_journey": active_journey,
        "total_journeys": total_journeys,
        "total_carbon_saved_g": total_carbon_saved_g,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def tracking(request):
    active_journey = Journey.objects.filter(user=request.user, status=Journey.Status.ACTIVE).first()
    transport_modes = TransportMode.objects.filter(is_active=True).order_by("name")
    context = {
        "active_journey": active_journey,
        "transport_modes": transport_modes,
    }
    return render(request, "core/tracking.html", context)


@login_required
def journey_history_list(request):
    journeys = Journey.objects.filter(user=request.user).order_by("-started_at")
    return render(request, "core/journey_list.html", {"journeys": journeys})


@login_required
def journey_history_detail(request, pk):
    # Ownership enforced the same way as the JSON API: get_object_or_404
    # with user=request.user, so a non-owner gets a plain 404 page rather
    # than any indication the journey ID exists.
    journey = get_object_or_404(Journey, pk=pk, user=request.user)
    points = journey.points.order_by("sequence")
    return render(request, "core/journey_detail.html", {"journey": journey, "points": points})


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, "core/profile.html", {"profile": profile})
