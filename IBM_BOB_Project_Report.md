# IBM BOB Project Report — EcoTransit V1
### 1M1B AI for Sustainability Virtual Internship

---

## 1. Project Overview

**Project Name:** EcoTransit  
**Version:** 1.0 (V1 — Feature Complete)  
**Reference Specification:** EcoTransit Master Technical Specification v2.1.1 — FINAL FREEZE  
**Platform:** Smart Urban Mobility & Environmental-Impact Platform  
**Status:** All spec sections implemented and verified. 150/150 automated tests passing with zero regressions.

EcoTransit is a Django-based web application that tracks real-world transit journeys, calculates carbon savings relative to a private-car baseline, and motivates users toward sustainable transport choices through a gamification engine (points, streaks, and achievement badges). It provides a live GPS tracking interface, a REST-style JSON API layer, data export capabilities (CSV/JSON/PDF), and a staff-facing analytics dashboard.

---

## 2. UN Sustainable Development Goal (SDG) Alignment

EcoTransit directly supports two primary UN SDGs:

### SDG 11 — Sustainable Cities and Communities
> *"Make cities and human settlements inclusive, safe, resilient and sustainable."*

EcoTransit contributes to SDG 11 by promoting a shift from private car use to lower-emission urban transport modes — walking, cycling, public transit, and electric vehicles. The platform quantifies the environmental benefit of each journey against a driving/car baseline, making the impact of individual modal choices visible and measurable. Behavioral incentives (points and streak multipliers) are weighted to reward the most sustainable modes:

| Transport Mode    | Points per km |
|-------------------|---------------|
| Walking / Cycling | 15            |
| Public Transit    | 8             |
| Electric Vehicle  | 3             |
| Driving / Car     | 0             |

### SDG 13 — Climate Action
> *"Take urgent action to combat climate change and its impacts."*

Every completed journey records a carbon saving in grams of CO₂ relative to the private-car baseline, using IPCC-aligned emission factors per transport mode. An `EmissionFactorSnapshot` is frozen at journey completion to preserve an immutable historical audit trail. Cumulative savings are tracked per user and surfaced in the profile dashboard, enabling personal climate accountability at scale.

---

## 3. Django Backend Architecture

EcoTransit is a standard Django 5.2 monolith with a clearly separated service layer. There is intentionally no Django REST Framework — all serializers are hand-written per the technical specification.

### Project Layout

```
ecotransit-v1-final/
├── manage.py
├── requirements.txt
├── .env.example
├── ecotransit/                # Project settings & entry points
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── core/                      # EcoTransit domain application
    ├── models.py              # 6 domain models
    ├── views.py               # HTML frontend views
    ├── admin.py               # Django admin registration
    ├── urls.py
    ├── api/                   # JSON API layer (9 endpoints)
    │   ├── views.py
    │   ├── serializers.py
    │   ├── exports.py
    │   ├── auth.py
    │   └── urls.py
    ├── services/              # Pure business-logic layer
    │   ├── carbon.py
    │   ├── openroute.py
    │   ├── gamification.py
    │   ├── integrity.py
    │   └── distance.py
    ├── templates/
    ├── static/
    └── migrations/
```

### Domain Models (6 Entities)

| Model                    | Purpose                                                                                    |
|--------------------------|--------------------------------------------------------------------------------------------|
| `TransportMode`          | Five fixed transport modes with mode code and `default_emission_factor_g_per_km` (Decimal) |
| `UserProfile`            | Extends Django `User` with gamification state: total points, streak days, last activity date |
| `Journey`                | Journey record: status, start/end labels & coordinates, distance, carbon saved, integrity hash |
| `JourneyPoint`           | Sequential GPS coordinates recorded during an active journey                               |
| `EmissionFactorSnapshot` | Immutable per-journey record of the emission factor used at completion time (audit integrity) |
| `AchievementLog`         | Event log of points earned, streak milestones, and badge unlocks                          |

### API Endpoints (9 Endpoints)

| Endpoint                        | Method     | Description                                              |
|---------------------------------|------------|----------------------------------------------------------|
| `/api/journeys/`                | GET        | List caller's journeys                                   |
| `/api/journeys/start/`          | POST       | Start a new journey (requires legal disclaimer acceptance) |
| `/api/journeys/<id>/points/`    | POST       | Append a GPS point to an active journey                  |
| `/api/journeys/<id>/stop/`      | POST       | Finalize journey: compute distance, carbon, hash, points |
| `/api/journeys/<id>/`           | GET        | Retrieve a single owned journey                          |
| `/api/transport-modes/`         | GET        | List active transport modes                              |
| `/api/profile/`                 | GET        | Caller's profile with live points and streak data        |
| `/api/routes/`                  | GET / POST | ORS routing (returns distance_km, duration_seconds)      |
| `/api/geocode/`                 | GET / POST | ORS forward and reverse geocoding                        |

**Export endpoints:** `/api/export/journeys.csv`, `/api/export/journeys.json`, `/api/export/journeys.pdf`

### Environment Configuration

| Variable                        | Default              | Purpose                                      |
|---------------------------------|----------------------|----------------------------------------------|
| `DJANGO_SECRET_KEY`             | dev placeholder      | Must be a random secret in production        |
| `DJANGO_DEBUG`                  | `True`               | Set `False` in production                    |
| `DJANGO_ALLOWED_HOSTS`          | `localhost,127.0.0.1`| Comma-separated allowed domains              |
| `DATABASE_URL`                  | SQLite fallback       | PostgreSQL in production                     |
| `OPENROUTESERVICE_API_KEY`      | (empty)              | ORS key; endpoints return 503 if unset       |

When `DEBUG=False`, Django auto-hardens: HSTS, secure cookies, SSL redirect, and `X-Frame-Options` are all activated.

---

## 4. OpenRouteService Integration

**File:** [`core/services/openroute.py`](core/services/openroute.py)

The `OpenRouteServiceClient` class wraps the ORS v2 API for two capabilities:

1. **Routing** — `get_route(coordinates, profile)` calls `POST /v2/directions/{profile}/geojson` and returns a `RouteResult(distance_km, duration_seconds, raw_response)`.
2. **Geocoding** — `geocode(query)` and `reverse_geocode(lat, lng)` call the ORS `/geocode/search` and `/geocode/reverse` endpoints, returning structured `GeocodeResult` objects.

All network exceptions, timeouts, malformed-JSON responses, and API-level errors are collapsed into a single `OpenRouteServiceError` exception type, preventing leakage of third-party error structures to API consumers. A configurable request timeout (default 10 seconds) guards against hanging. No live HTTP calls are made in the test suite — the client is fully mocked.

---

## 5. Carbon Calculator

**File:** [`core/services/carbon.py`](core/services/carbon.py)

The carbon calculator implements the emissions accounting logic specified in §3 of the Master Technical Specification.

**Core functions:**

- `calculate_emissions_g(distance_km, emission_factor_g_per_km)` — Multiplies distance by the mode's emission factor.
- `calculate_carbon_saved_g(distance_km, actual_factor, baseline_factor)` — Returns the difference relative to the `driving_car` baseline. Negative values (modes more polluting than baseline) are preserved without clamping, maintaining accuracy.
- `finalize_journey_emissions(journey)` — Called on journey stop: creates an `EmissionFactorSnapshot` (freezing the factor in use at that moment), then writes `journey.carbon_saved_g`. Raises `CarbonCalculationError` if distance is unset or a snapshot already exists.

**Design principle:** The snapshot mechanism decouples historical reporting from any future changes to `TransportMode.default_emission_factor_g_per_km`, ensuring that past journeys always reflect the factor that was in effect at the time they were recorded.

---

## 6. Gamification Service Layer

**File:** [`core/services/gamification.py`](core/services/gamification.py)

The gamification engine awards points, tracks daily streaks, and unlocks achievement badges on every completed journey.

### Points Formula

```
points = round(max(carbon_saved_g, 0) / 1000 * 10) + (distance_km × mode_multiplier)
```

Where `mode_multiplier` is 15 for walking/cycling, 8 for public transit, 3 for electric vehicles, and 0 for driving/car.

### Streak Tracking

`check_and_update_streak(user, activity_date)` — Maintains a consecutive-day count based on calendar-day comparison (not a raw 48-hour timer). One qualifying completed journey per calendar day maintains or advances the streak. A gap of one or more full calendar days resets the streak to 1. Multiple journeys on the same day do not double-count.

### Achievement Badges (3 Milestones)

| Badge            | Trigger                                    | Bonus Points | Idempotency                          |
|------------------|--------------------------------------------|:------------:|--------------------------------------|
| **First Steps**  | User's first-ever completed journey        | +50          | Fires exactly once (existence check) |
| **Eco Warrior**  | Cumulative carbon saved ≥ 10 kg            | +200         | Fires once; handles jumps (e.g., 6 kg → 15 kg in one journey) |
| **Week of Green**| Streak reaches 7 consecutive days          | +100         | Re-earnable after a reset-rebuild cycle |

### Concurrency & Atomicity

The entire gamification finalization (carbon calculation + SHA-256 hash + points + streak + achievement checks) is wrapped in a single `transaction.atomic()` block. The `UserProfile` row is locked with `select_for_update()` for the duration, eliminating race conditions when concurrent requests arrive for the same user.

---

## 7. Test Coverage

| Test File                    | Tests | Scope                                                                       |
|------------------------------|:-----:|-----------------------------------------------------------------------------|
| `core/tests.py`              | 33    | Model validation, relationships, `__str__`, cascade / SET_NULL / PROTECT    |
| `core/test_services.py`      | 32    | Carbon calculation, ORS (mocked), SHA-256 hashing, tamper detection         |
| `core/tests_api.py`          | 44    | Journey lifecycle, auth/ownership enforcement, routes/geocode (mocked)      |
| `core/tests_exports.py`      | 16    | CSV / JSON / PDF exports (ownership-scoped), admin analytics aggregates     |
| `core/tests_gamification.py` | 25    | Points formula, streak logic, all 3 badges, idempotency, concurrency safety |
| **Total**                    | **150** | **100 % passing — 0 errors, 0 failures**                                  |

---

## 8. IBM BOB Integration & Debugging Log

```
====================================================================
                IBM BOB AI INTEGRATION & DEBUGGING LOG
====================================================================
1. Session Initialization: 
   - Dragged project workspace into IBM BOB environment for architectural review.
   - Verified alignment with Master Technical Specification v2.1.1.

2. Architecture & Service Integration via IBM BOB:
   - Configured core/services/carbon.py for precise emissions metrics.
   - Integrated OpenRouteService API connectors in core/services/openroute.py.
   - Implemented cryptographic data hashing in core/services/integrity.py.

3. Gamification & Streak Logic Implementation (Debugging & Patching):
   - Prompted IBM BOB to write core/services/gamification.py handling points calculation, 
     consecutive day streak validation, and automated achievement logging.
   - Resolved concurrency race conditions by wrapping milestone checks in atomic 
     database transactions (select_for_update).

4. Automated Test Verification & Quality Control:
   - Executed full test suite via IBM BOB terminal interface:
     Command: python manage.py test
     Result: 150/150 automated unit and integration tests passed with 0 errors.
   - Executed Django system checks (python manage.py check --deploy) to verify 
     production security settings and cryptographic secret keys.
====================================================================
```

---

## 9. Key Dependencies

| Package           | Version  | Role                                    |
|-------------------|----------|-----------------------------------------|
| Django            | 5.2.17   | Web framework                           |
| psycopg2-binary   | 2.9.10   | PostgreSQL adapter                      |
| python-decouple   | 3.8      | Environment variable management         |
| dj-database-url   | 3.1.2    | Database URL parsing                    |
| requests          | 2.33.1   | HTTP client for OpenRouteService        |
| reportlab         | 4.4.10   | PDF generation for data exports         |

---

## 10. Architecture Decisions & V1 Scope

**Key architectural decisions:**

- **No Django REST Framework** — hand-written serializers keep the dependency footprint minimal and maintain full spec alignment.
- **Pure service layer** — `carbon.py`, `openroute.py`, `gamification.py`, and `integrity.py` are stateless; only explicit `finalize_*` functions write to the database.
- **Snapshot immutability** — `EmissionFactorSnapshot` is write-once per journey, protecting the audit trail from retroactive changes.
- **Row-level locking** — `select_for_update()` on `UserProfile` prevents gamification race conditions without requiring a task queue.

**Phase 1 scope boundaries (intentionally excluded):**  
User registration / signup flow, password-reset emails, background workers (Celery/Redis), AI / RAG features, blockchain, payments, social features, and per-user admin analytics breakdowns.

---

*Report prepared as part of the 1M1B AI for Sustainability Virtual Internship — EcoTransit V1, IBM BOB AI-assisted development.*

---

## 11. License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for full terms.

Copyright (c) 2026 Savio Chacko Xavier
