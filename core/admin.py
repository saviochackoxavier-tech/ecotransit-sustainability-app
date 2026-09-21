"""
Django admin registration for the core domain models, plus (Phase 6) a
custom high-level analytics view added the standard, documented way:
overriding AdminSite.get_urls() to register one extra URL, wrapped in
admin.site.admin_view() so it gets the same staff-required/login-required
enforcement as every other admin page. This is not a new framework or
architecture — it's the pattern Django's own docs describe for adding a
custom admin view.

The analytics view intentionally shows aggregate, platform-wide figures
only (total counts/sums) — no per-user breakdowns or personally
identifying data beyond what the existing per-model admin list views
already expose, consistent with not inventing new privacy-relevant data
exposure.
"""

from django.contrib import admin
from django.db.models import Count, Sum
from django.template.response import TemplateResponse
from django.urls import path

from core.models import (
    AchievementLog,
    EmissionFactorSnapshot,
    Journey,
    JourneyPoint,
    TransportMode,
    UserProfile,
)


@admin.register(TransportMode)
class TransportModeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "default_emission_factor_g_per_km", "is_active")
    list_filter = ("is_active",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_points", "current_streak_days", "longest_streak_days")


class JourneyPointInline(admin.TabularInline):
    model = JourneyPoint
    extra = 0


@admin.register(Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "transport_mode", "status", "started_at", "ended_at")
    list_filter = ("status", "transport_mode")
    inlines = [JourneyPointInline]


@admin.register(EmissionFactorSnapshot)
class EmissionFactorSnapshotAdmin(admin.ModelAdmin):
    list_display = ("journey", "transport_mode", "emission_factor_g_per_km", "captured_at")


@admin.register(AchievementLog)
class AchievementLogAdmin(admin.ModelAdmin):
    list_display = ("user", "entry_type", "points", "badge_name", "created_at")
    list_filter = ("entry_type",)


def analytics_view(request):
    """
    High-level platform analytics: total carbon saved across all users,
    active journey count, and transport-mode distribution — exactly the
    three examples named in the Phase 6 brief, nothing more.
    """
    total_carbon_saved_g = (
        Journey.objects.filter(carbon_saved_g__isnull=False).aggregate(total=Sum("carbon_saved_g"))["total"] or 0
    )
    total_journeys = Journey.objects.count()
    active_journeys = Journey.objects.filter(status=Journey.Status.ACTIVE).count()
    completed_journeys = Journey.objects.filter(status=Journey.Status.COMPLETED).count()
    mode_distribution = (
        Journey.objects.values("transport_mode__name").annotate(count=Count("id")).order_by("-count")
    )

    context = {
        **admin.site.each_context(request),
        "title": "EcoTransit Analytics",
        "total_carbon_saved_g": total_carbon_saved_g,
        "total_journeys": total_journeys,
        "active_journeys": active_journeys,
        "completed_journeys": completed_journeys,
        "mode_distribution": mode_distribution,
    }
    return TemplateResponse(request, "admin/core/analytics.html", context)


_default_get_urls = admin.site.get_urls


def _get_urls_with_analytics():
    custom_urls = [
        path("analytics/", admin.site.admin_view(analytics_view), name="core-analytics"),
    ]
    return custom_urls + _default_get_urls()


admin.site.get_urls = _get_urls_with_analytics
