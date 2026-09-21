"""
Carbon-saving calculation engine.

Spec (Phase 3 execution prompt): "Calculate emissions based on distance
and transport mode emission factors (g CO2 / passenger-km)... Calculate
carbon savings relative to the baseline mode (driving/car baseline)."

This module also implements the "historical snapshot mechanism" required
by spec §3 ("Emission Factor Snapshot: ... capturing emission factors at
the time of journey completion to ensure historical audit integrity") by
creating an EmissionFactorSnapshot row and freezing the resulting carbon
figure onto the Journey record. It does not touch Journey.status or
Journey.integrity_hash — sequencing a full "stop journey" workflow is a
later phase's responsibility (the master spec assigns that to the
`/api/journeys/<id>/stop/` endpoint).
"""

from __future__ import annotations

from decimal import Decimal

from core.models import EmissionFactorSnapshot, Journey, TransportMode


class CarbonCalculationError(Exception):
    """Raised when a carbon calculation cannot be performed."""


def get_baseline_transport_mode() -> TransportMode:
    """
    Return the baseline TransportMode (Driving/Car) used for all carbon
    savings comparisons, per the spec's explicit "driving/car baseline".
    """
    try:
        return TransportMode.objects.get(code=TransportMode.Code.DRIVING_CAR)
    except TransportMode.DoesNotExist as exc:
        raise CarbonCalculationError(
            "No TransportMode with code 'driving_car' exists; it is required "
            "as the carbon-savings baseline."
        ) from exc


def calculate_emissions_g(distance_km: Decimal, emission_factor_g_per_km: Decimal) -> Decimal:
    """Total emissions (g CO2) for travelling `distance_km` at `emission_factor_g_per_km`."""
    return distance_km * emission_factor_g_per_km


def calculate_carbon_saved_g(
    distance_km: Decimal,
    actual_emission_factor_g_per_km: Decimal,
    baseline_emission_factor_g_per_km: Decimal,
) -> Decimal:
    """
    Carbon saved (g CO2), relative to the driving/car baseline, for a
    journey of `distance_km` taken using a mode with
    `actual_emission_factor_g_per_km`.

    Positive => the journey emitted less than the baseline would have.
    Negative => the journey emitted more than the baseline would have.

    ASSUMPTION: the result is not clamped to zero. A negative "savings"
    figure (e.g. an inefficient driving/car trip vs. the baseline
    driving/car factor, or any future mode with a higher factor than the
    baseline) is preserved as an accurate accounting figure rather than
    hidden. Revisit if the frozen methodology specifies clamping.
    """
    baseline_emissions = calculate_emissions_g(distance_km, baseline_emission_factor_g_per_km)
    actual_emissions = calculate_emissions_g(distance_km, actual_emission_factor_g_per_km)
    return baseline_emissions - actual_emissions


def finalize_journey_emissions(journey: Journey) -> EmissionFactorSnapshot:
    """
    Freeze the journey's transport-mode emission factor into an
    EmissionFactorSnapshot (spec §3's historical snapshot mechanism), and
    populate Journey.carbon_saved_g relative to the driving/car baseline.

    Raises CarbonCalculationError if:
      - journey.distance_km is not set yet, or
      - a snapshot already exists for this journey (snapshots are
        one-per-journey and immutable once created — re-running this
        would silently overwrite the audit record).
    """
    if journey.distance_km is None:
        raise CarbonCalculationError(
            f"Journey #{journey.pk}: distance_km must be set before finalizing emissions."
        )

    if EmissionFactorSnapshot.objects.filter(journey=journey).exists():
        raise CarbonCalculationError(
            f"Journey #{journey.pk} already has an emission factor snapshot; "
            "refusing to overwrite the audit record."
        )

    baseline_mode = get_baseline_transport_mode()

    snapshot = EmissionFactorSnapshot.objects.create(
        journey=journey,
        transport_mode=journey.transport_mode,
        emission_factor_g_per_km=journey.transport_mode.default_emission_factor_g_per_km,
    )

    carbon_saved = calculate_carbon_saved_g(
        distance_km=journey.distance_km,
        actual_emission_factor_g_per_km=snapshot.emission_factor_g_per_km,
        baseline_emission_factor_g_per_km=baseline_mode.default_emission_factor_g_per_km,
    )
    journey.carbon_saved_g = carbon_saved
    journey.save(update_fields=["carbon_saved_g"])

    return snapshot
