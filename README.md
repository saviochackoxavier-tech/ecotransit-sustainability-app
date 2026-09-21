# EcoTransit

Smart Urban Mobility & Environmental-Impact Platform.

Reference: **EcoTransit Master Technical Specification v2.1.1 — FINAL FREEZE**.

## Status: V1 fully complete

All spec sections made available across this project's development are
implemented and tested, including the points/streak/achievement engine
that was deliberately left open through Phases 3–6 pending an actual
methodology (finally provided in the merge/gamification execution
prompt).

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # edit for your local values
```

Set a real `DJANGO_SECRET_KEY` in `.env` for anything beyond throwaway
local testing. All other `.env` values have safe local defaults.

## Running the project

```bash
python manage.py migrate
python manage.py createsuperuser   # to log in and use the frontend/admin
python manage.py runserver
```

- Frontend: `http://127.0.0.1:8000/` (redirects to `/login/` if not authenticated)
- Admin: `http://127.0.0.1:8000/admin/`
- Admin analytics: `http://127.0.0.1:8000/admin/analytics/` (staff only)
- JSON API: `http://127.0.0.1:8000/api/...`

## Database

- **Local development:** SQLite, used automatically — no setup required.
- **PostgreSQL:** set `DATABASE_URL` in `.env`
  (`postgres://user:password@localhost:5432/ecotransit`); takes
  precedence over SQLite when set. `psycopg2-binary` is installed so
  this path is actually functional, not just parsed.

## Checks & tests

```bash
python manage.py check
python manage.py check --deploy   # under a prod-like env, all warnings clear
python manage.py test
```

**150 tests, all passing, zero regressions:**

| File | Count | Covers |
|---|---|---|
| `core/tests.py` | 33 | Domain models: relationships, validation, `__str__`, cascade/`SET_NULL`/`PROTECT` behavior |
| `core/test_services.py` | 32 | Carbon calculation, OpenRouteService wrapper (mocked HTTP), SHA-256 hashing + tamper detection |
| `core/tests_api.py` | 44 | Journey lifecycle API, auth/ownership enforcement, transport-modes/profile, routes/geocode (mocked), gamification wiring at `/stop/` |
| `core/tests_exports.py` | 16 | CSV/JSON/PDF exports (ownership-scoped), admin analytics aggregates |
| `core/tests_gamification.py` | 25 | Points formula, streak logic, all three achievement milestones, idempotency |

`manage.py check --deploy` was verified under both dev config (warns
correctly about dev-only settings) and a prod-like env
(`DJANGO_DEBUG=False`, a genuinely random `DJANGO_SECRET_KEY`, real
`ALLOWED_HOSTS`) — **zero warnings** in the prod-like case.

## Architecture by module

- **`ecotransit/`** — project settings, root URLconf, WSGI/ASGI.
  Environment-driven config throughout (`django-decouple`): secret key,
  debug, allowed hosts, CSRF trusted origins, security-cookie toggles,
  OpenRouteService credentials. Security settings auto-harden when
  `DEBUG=False` (HSTS, secure cookies, SSL redirect).
- **`core/models.py`** — the six domain models from spec §3:
  `TransportMode`, `UserProfile`, `Journey`, `JourneyPoint`,
  `EmissionFactorSnapshot`, `AchievementLog`. Every field not explicitly
  named in the spec is marked `# ASSUMPTION` inline.
- **`core/services/`** — pure business logic:
  - `carbon.py` — carbon savings vs. the **driving/car baseline**, freezing
    values via `EmissionFactorSnapshot`
  - `distance.py` — haversine great-circle distance from recorded GPS points
  - `integrity.py` — SHA-256 hash over the spec'd fields, with Decimal
    quantization for stability across DB round-trips
  - `openroute.py` — `OpenRouteServiceClient`; every failure mode
    collapses to one `OpenRouteServiceError`
  - **`gamification.py`** (new) — points/streak/achievement engine; see
    below
- **`core/api/`** — the JSON API (spec §26's endpoint table), plain
  Django views (no DRF), a hand-written serializer layer, and
  `core/api/exports.py` for CSV/JSON/PDF downloads. Every endpoint
  enforces ownership via `request.user` — never a client-supplied ID.
- **`core/views.py`, `core/templates/`, `core/static/`** — the HTML
  frontend: dashboard, live tracking (Leaflet + vanilla JS), journey
  history/detail, profile (now shows live points/streaks and explains
  how they're earned).
- **`core/admin.py`** — plain `ModelAdmin` registration for every model,
  plus `/admin/analytics/` (aggregate platform stats only) via
  `AdminSite.get_urls()`.

## Gamification engine (`core/services/gamification.py`)

Implemented exactly to the rules given in the final merge execution
prompt. Wired into `POST /api/journeys/<id>/stop/`, inside the same
database transaction as carbon/hash finalization, so points/streaks/
achievements are computed atomically with the rest of journey
completion — a failure anywhere rolls the whole thing back.

**Points formula:** `points = round(max(carbon_saved_g, 0) / 1000 * 10) + round(distance_km * mode_multiplier)`

| Mode | Points / km |
|---|---|
| Walking, Cycling | 15 |
| Public Transit | 8 |
| Electric Vehicle | 3 |
| Driving / Car (ICE) | 0 |

**Streak tracking** (`check_and_update_streak(user, activity_date)` —
named and signatured exactly as the prompt specified): one qualifying
completed journey per calendar day maintains/grows the streak; multiple
journeys the same day don't double-count; a gap of a full calendar day
or more resets the streak.

**Achievements**, each logged as an `AchievementLog` row and added to
`UserProfile.total_points` in the same atomic operation:

| Badge | Trigger | Bonus |
|---|---|---|
| First Steps | User's first-ever completed journey | +50 |
| Eco Warrior | Cumulative carbon saved crosses 10kg | +200 |
| Week of Green | Streak reaches 7 consecutive days | +100 |

**Concurrency/idempotency:** `UserProfile` is row-locked
(`select_for_update`) for the duration of the whole operation, so
concurrent journey completions for the same user can't race on points/
streak counters or double-award a milestone. Eco Warrior and First
Steps are additionally guarded by existence-checks (has this user
already earned this badge?), so they fire exactly once even if a single
journey's numbers jump straight past a threshold.

### Ambiguities resolved (flagged in code, summarized here)

- **"Reset the streak to 0"** after a missed day is applied as
  reset-then-recount: since the journey being evaluated is itself a
  qualifying journey completed *today*, the persisted result is 1, not
  0 — matching how every mainstream streak product behaves, and
  avoiding a user seeing "streak: 0" right after finishing a journey.
- **The "48 hours" vs. calendar-day wording**: implemented as calendar-day
  comparison (the more precise definition given), not a raw timer.
- **Week of Green re-earnability**: treated as re-earnable after a
  genuine reset-and-rebuild cycle, not a once-ever badge — the prompt's
  idempotency requirement is read as "no duplicate awards for the same
  trigger event," which existence-checked achievements (First Steps,
  Eco Warrior) and streak-transition-checked achievements (Week of
  Green) both satisfy, just via different mechanisms appropriate to
  each badge's nature (cumulative vs. cyclical).
- **Negative `carbon_saved_g`** (not clamped to zero elsewhere, by
  design) is floored to 0 specifically for the points formula, so a
  journey that technically emitted more than the baseline never
  subtracts points.

## API endpoints

| Endpoint | Method | Notes |
|---|---|---|
| `/api/journeys/` | GET | Only the authenticated user's journeys |
| `/api/journeys/start/` | POST | Requires `transport_mode` + `legal_disclaimer_accepted: true`; 409 if already active |
| `/api/journeys/<id>/points/` | POST | Adds a GPS point; sequence auto-assigned; 409 if not active |
| `/api/journeys/<id>/stop/` | POST | Finalizes distance/carbon/hash **and now points/streak/achievements**, atomically |
| `/api/journeys/<id>/` | GET | Owner only — 404 (not 403) if not owned |
| `/api/transport-modes/` | GET | Active modes only |
| `/api/profile/` | GET | Caller's `UserProfile`, now with live points/streak data |
| `/api/routes/` | GET/POST | ORS routing; 503 if unconfigured, 502 on ORS failure |
| `/api/geocode/` | GET/POST | ORS forward/reverse geocoding |
| `/api/export/journeys.csv` / `.json` / `.pdf` | GET | Owner's journeys only |

## Other assumptions made along the way (all flagged inline in code)

- **"Location consent"** for `/start/` maps onto `Journey.legal_disclaimer_accepted`.
- **Distance calculation** uses the haversine great-circle formula.
- **Carbon savings aren't clamped to zero** in `carbon.py` (but are
  floored to zero specifically inside the points formula — see above).
- **Export format/columns** mirror what's already stored on `Journey`
  and already exposed by the API serializer.
- **No Django REST Framework** — not named in the spec's tech stack.

## What is explicitly NOT implemented (out of V1 scope per the governing instruction)

- AI/RAG, blockchain, payments, social features
- Background workers (Celery/Redis) — exports run synchronously by design
- Any per-user breakdown in admin analytics beyond aggregate platform figures
- Registration/signup flow or password-reset email flow (users are created via `createsuperuser` or `/admin/`)

## Production deployment recommendations

- Set `DJANGO_SECRET_KEY` to a genuinely random value (never the
  `django-insecure-...` default) and `DJANGO_DEBUG=False`.
- Set `DJANGO_ALLOWED_HOSTS` to your real domain(s); set
  `DJANGO_CSRF_TRUSTED_ORIGINS` if serving behind a proxy/CDN over HTTPS.
- Point `DATABASE_URL` at a real PostgreSQL instance rather than SQLite.
- Run `python manage.py check --deploy` in CI against a prod-like env
  before every deploy — it should report zero issues.
- Serve static files via `collectstatic` + a real static file
  host/CDN, not Django's dev server.
- Put a real WSGI/ASGI server (gunicorn/uvicorn) behind a reverse proxy
  terminating TLS; the security settings here (HSTS, secure cookies,
  SSL redirect) assume that setup.
- Set a real `OPENROUTESERVICE_API_KEY` before relying on `/api/routes/`
  or `/api/geocode/` in production — without it those endpoints return
  503 by design rather than failing unpredictably.
- Consider moving PDF export generation to a background task only if
  export volume/latency becomes a real problem — it's synchronous by
  design for V1, per explicit instruction.

## 📺 Project Demo & Presentation

Want to see the project in action? Check out the video walkthrough and presentation assets:

* 🎥 **[Watch the Project Demo on Google Drive](https://drive.google.com/file/d/1W1z4iBQhO_GHhJMmgiKvM6NBgVcYGnj3/view?usp=sharing)** *(Make sure your Google Drive link is set to "Anyone with the link can view")*

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for full terms.

Copyright (c) 2026 Savio Chacko Xavier