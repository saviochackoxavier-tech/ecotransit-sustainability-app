"""
Journey data export utilities and views (CSV / JSON / PDF).

Spec (Phase 6 execution prompt): "Implement data export utilities
allowing users to download their journey history and carbon savings
reports in standard formats (CSV / PDF / JSON as specified in the master
spec)."

ASSUMPTION: no dedicated "export format" section of the master spec was
provided at implementation time — no exact column set or report layout
is defined anywhere in the spec text available. The fields below mirror
exactly what's already stored on Journey (spec §3) and already exposed
by the JSON API's serialize_journey (Phase 4); no new data is invented.

Security rule (spec §26, applied here too): every export is scoped to
`user=request.user` — nothing here ever includes another user's data,
and there is no parameter that could widen that scope.

PDF generation runs synchronously (reportlab, no external service calls)
per this phase's explicit preference for synchronous file generation
over background workers.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone as dt_timezone

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from core.api.auth import login_required_json
from core.models import Journey

EXPORT_FIELDS = [
    "id",
    "transport_mode",
    "status",
    "start_label",
    "end_label",
    "distance_km",
    "carbon_saved_g",
    "integrity_hash",
    "legal_disclaimer_accepted",
    "started_at",
    "ended_at",
]


def _journeys_for_export(user):
    return Journey.objects.filter(user=user).select_related("transport_mode").order_by("-started_at")


def _row_for_journey(journey: Journey) -> dict:
    return {
        "id": journey.id,
        "transport_mode": journey.transport_mode.name,
        "status": journey.status,
        "start_label": journey.start_label,
        "end_label": journey.end_label,
        "distance_km": str(journey.distance_km) if journey.distance_km is not None else "",
        "carbon_saved_g": str(journey.carbon_saved_g) if journey.carbon_saved_g is not None else "",
        "integrity_hash": journey.integrity_hash,
        "legal_disclaimer_accepted": journey.legal_disclaimer_accepted,
        "started_at": journey.started_at.isoformat() if journey.started_at else "",
        "ended_at": journey.ended_at.isoformat() if journey.ended_at else "",
    }


def build_csv_response(user) -> HttpResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    for journey in _journeys_for_export(user):
        writer.writerow(_row_for_journey(journey))

    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="ecotransit_journeys_{user.username}.csv"'
    return response


def build_json_response(user) -> HttpResponse:
    rows = [_row_for_journey(j) for j in _journeys_for_export(user)]
    payload = {
        "user": user.username,
        "generated_at": datetime.now(dt_timezone.utc).isoformat(),
        "journeys": rows,
    }
    response = HttpResponse(json.dumps(payload, indent=2), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="ecotransit_journeys_{user.username}.json"'
    return response


def build_pdf_response(user) -> HttpResponse:
    # Imported lazily so importing this module doesn't require reportlab
    # unless a PDF is actually requested.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    journeys = list(_journeys_for_export(user))
    total_distance = sum((j.distance_km for j in journeys if j.distance_km is not None), start=0)
    total_carbon = sum((j.carbon_saved_g for j in journeys if j.carbon_saved_g is not None), start=0)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("EcoTransit — Journey &amp; Carbon Savings Report", styles["Title"]),
        Paragraph(f"User: {user.username}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.now(dt_timezone.utc).isoformat()}", styles["Normal"]),
        Spacer(1, 0.2 * inch),
        Paragraph(f"Total journeys: {len(journeys)}", styles["Normal"]),
        Paragraph(f"Total distance: {total_distance} km", styles["Normal"]),
        Paragraph(f"Total carbon saved: {total_carbon} g CO2", styles["Normal"]),
        Spacer(1, 0.3 * inch),
    ]

    table_data = [["Mode", "Status", "Distance (km)", "Carbon saved (g)", "Started"]]
    for j in journeys:
        table_data.append(
            [
                j.transport_mode.name,
                j.status,
                str(j.distance_km) if j.distance_km is not None else "-",
                str(j.carbon_saved_g) if j.carbon_saved_g is not None else "-",
                j.started_at.strftime("%Y-%m-%d %H:%M") if j.started_at else "-",
            ]
        )

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3D2E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF2EF")]),
            ]
        )
    )
    elements.append(table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="ecotransit_journeys_{user.username}.pdf"'
    return response


@login_required_json
@require_http_methods(["GET"])
def export_journeys_csv(request):
    return build_csv_response(request.user)


@login_required_json
@require_http_methods(["GET"])
def export_journeys_json(request):
    return build_json_response(request.user)


@login_required_json
@require_http_methods(["GET"])
def export_journeys_pdf(request):
    return build_pdf_response(request.user)
