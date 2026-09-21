# 🌱 EcoTransit

### Smart Urban Mobility & Environmental-Impact Platform

<p align="center">
  <strong>Track your journeys • Measure your impact • Build sustainable habits</strong>
</p>

<p align="center">
  A Django-based full-stack web application prototype for journey tracking, environmental-impact estimation, route visualization, sustainable mobility analytics, and gamification.
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![Django](https://img.shields.io/badge/Django-Framework-092E20?style=for-the-badge\&logo=django\&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Local%20DB-003B57?style=for-the-badge\&logo=sqlite\&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Production%20DB-4169E1?style=for-the-badge\&logo=postgresql\&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-Maps-199900?style=for-the-badge\&logo=leaflet\&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-150%20Passing-2EA44F?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-V1-00A86B?style=for-the-badge)

</p>

---

## 🌍 What is EcoTransit?

**EcoTransit** is a professional full-stack web application prototype designed to make everyday mobility more measurable and environmentally understandable.

The platform allows users to record journeys, capture GPS points, calculate estimated environmental impact, visualize routes, review travel history, earn sustainable-mobility points, maintain streaks, unlock achievements, and export their journey records.

At the same time, EcoTransit provides administrative analytics, historical emission-factor snapshots, API ownership controls, journey-integrity hashing, and production-oriented security configuration.

### The core idea

```text
                 YOUR JOURNEY
                      │
                      ▼
              ┌───────────────┐
              │ Transport Mode│
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ GPS / Route   │
              │   Points      │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │   Distance    │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ Carbon Impact │
              └───────┬───────┘
                      │
              ┌───────┴────────┐
              ▼                ▼
       ┌─────────────┐  ┌─────────────┐
       │ Green Points│  │    Streak   │
       └──────┬──────┘  └──────┬──────┘
              │                │
              └───────┬────────┘
                      ▼
              ┌───────────────┐
              │ Achievements  │
              └───────────────┘
```

> **Track. Measure. Understand. Move Sustainably.**

---

# ✨ Why EcoTransit?

Transportation choices have environmental consequences, but those consequences are often difficult to see in everyday life.

EcoTransit connects mobility tracking with understandable environmental metrics and user engagement.

Instead of treating sustainability as an abstract concept, the platform turns a journey into measurable information:

* 📍 Where did the journey happen?
* 🛣️ How far did it travel?
* 🚶 Which transport mode was used?
* 🌱 What was the estimated environmental impact?
* ⭐ How many points were earned?
* 🔥 Is the user's sustainable streak continuing?
* 🏆 Were any achievements unlocked?
* 📊 What does the user's journey history look like?

---

# 🚀 Feature Overview

| Feature                            | Status |
| ---------------------------------- | :----: |
| 🔐 User authentication             |    ✅   |
| 👤 User profiles                   |    ✅   |
| 🚌 Transport modes                 |    ✅   |
| 🗺️ Interactive maps               |    ✅   |
| 📍 GPS journey points              |    ✅   |
| 🧭 Route calculation               |    ✅   |
| 🔎 Forward geocoding               |    ✅   |
| 🔄 Reverse geocoding               |    ✅   |
| 📏 Distance calculation            |    ✅   |
| 🌱 Carbon-impact calculation       |    ✅   |
| 📸 Historical emission snapshots   |    ✅   |
| 🛡️ SHA-256 journey integrity      |    ✅   |
| 📚 Journey history                 |    ✅   |
| 📄 CSV export                      |    ✅   |
| 📋 JSON export                     |    ✅   |
| 📑 PDF export                      |    ✅   |
| ⭐ Green points                     |    ✅   |
| 🔥 Sustainable streaks             |    ✅   |
| 🏆 Achievements                    |    ✅   |
| 📈 Admin analytics                 |    ✅   |
| 🔒 Ownership enforcement           |    ✅   |
| ⚙️ Environment-based configuration |    ✅   |
| 🧪 Automated testing               |    ✅   |
| 🛡️ Production security checks     |    ✅   |

---

# 🧩 Core Features

## 🗺️ 1. Journey Tracking

EcoTransit implements a complete journey lifecycle.

A journey can:

1. Start with a selected transport mode.
2. Record GPS/location points.
3. Calculate the travelled distance.
4. Calculate estimated environmental impact.
5. Finalize the journey.
6. Generate an integrity hash.
7. Award applicable points.
8. Update the user's streak.
9. Evaluate achievement milestones.
10. Become available in journey history.

Journey completion is performed inside a database transaction so that carbon calculation, integrity finalization, and gamification remain consistent.

---

## 📍 2. GPS Point Tracking

Active journeys can receive GPS points.

Each point receives an automatically assigned sequence number.

This allows recorded journey points to be reconstructed in their correct order.

Distance is calculated using the **Haversine great-circle distance formula**.

---

## 🌱 3. Environmental Impact Calculation

EcoTransit calculates estimated carbon savings against the project's defined **driving/car baseline**.

The calculation uses an `EmissionFactorSnapshot` so that the factor used by a completed journey remains historically associated with that journey.

### Why snapshots matter

Consider:

```text
Emission Factor A
       │
       ▼
   Journey #1
       │
       ▼
 Snapshot A
       │
       │
 Factor updated
       │
       ▼
Emission Factor B
       │
       ▼
   Journey #2
       │
       ▼
 Snapshot B
```

Changing the currently active emission factor therefore does not silently rewrite the historical factor associated with Journey #1.

> EcoTransit provides estimated environmental-impact calculations. It does not represent verified carbon offsets or independently certified emissions reductions.

---

# ⭐ 4. Green Points

EcoTransit uses a defined points formula:

```text
points =
round(max(carbon_saved_g, 0) / 1000 * 10)
+
round(distance_km * mode_multiplier)
```

### Transport-mode multipliers

| Transport Mode         | Points / km |
| ---------------------- | ----------: |
| 🚶 Walking             |          15 |
| 🚲 Cycling             |          15 |
| 🚌 Public Transit      |           8 |
| ⚡ Electric Vehicle     |           3 |
| 🚗 Driving / Car (ICE) |           0 |

Negative `carbon_saved_g` values are floored to zero **only for the points formula**.

Therefore, a journey that produces more emissions than the baseline does not subtract points.

---

# 🔥 5. Sustainable Streaks

EcoTransit tracks sustainable journey activity by **calendar day**.

### Streak rules

* One qualifying completed journey per calendar day maintains or grows the streak.
* Multiple journeys on the same day do not double-count.
* A gap of a full calendar day or more resets the streak.
* After a reset, completing a qualifying journey results in a streak of `1`.
* Calendar-day comparison is used instead of a raw 48-hour timer.

### Example

```text
Monday     ✅   Streak: 1
Tuesday    ✅   Streak: 2
Wednesday  ✅   Streak: 3
Thursday   ❌
Friday     ❌
Saturday   ✅   Streak: 1
```

This prevents a completed journey immediately after a missed period from displaying an unintuitive streak of `0`.

---

# 🏆 6. Achievement System

EcoTransit currently provides three achievement milestones.

| Achievement      | Trigger                               | Bonus |
| ---------------- | ------------------------------------- | ----: |
| 🥾 First Steps   | First-ever completed journey          |   +50 |
| ⚔️ Eco Warrior   | Cumulative carbon saved crosses 10 kg |  +200 |
| 🌿 Week of Green | Streak reaches 7 consecutive days     |  +100 |

Achievements are stored as `AchievementLog` records.

Achievement bonuses are added to `UserProfile.total_points` during the same atomic operation as journey completion.

### Achievement reliability

The implementation protects against duplicate awards.

**First Steps** and **Eco Warrior** use existence checks.

**Week of Green** is evaluated through the streak transition and can be earned again after a genuine reset-and-rebuild cycle.

---

# 🛡️ 7. Journey Integrity

EcoTransit includes a SHA-256 integrity mechanism.

The integrity service:

* Creates a SHA-256 hash from the specified journey fields.
* Uses Decimal quantization for stable values across database round-trips.
* Supports tamper detection.
* Finalizes the hash during journey completion.

```text
Journey Data
     │
     ▼
Canonical Values
     │
     ▼
Decimal Quantization
     │
     ▼
SHA-256
     │
     ▼
Integrity Hash
```

> **Important:** Journey records are application records and environmental tracking information. They should not automatically be interpreted as legal proof, certified evidence, or official government records.

---

# 🗺️ 8. Maps, Routing & Geocoding

EcoTransit uses **Leaflet.js** for interactive mapping and **OpenRouteService** for routing and geocoding.

Supported capabilities include:

* 🗺️ Interactive map display
* 🧭 Route calculation
* 🔎 Forward geocoding
* 🔄 Reverse geocoding
* 📍 Journey point visualization

The application handles external routing failures through a dedicated:

```text
OpenRouteServiceError
```

If the OpenRouteService API is not configured:

```text
503 Service Unavailable
```

is returned by the appropriate endpoints.

If the external service fails:

```text
502 Bad Gateway
```

is returned rather than exposing unpredictable failure behavior.

---

# 📚 9. Journey History

EcoTransit provides journey history and journey-detail views.

Users can review their recorded journeys and associated information through the application.

The frontend includes:

* Dashboard
* Live tracking
* Journey history
* Journey detail
* User profile
* Points information
* Streak information
* Achievement information

---

# 📤 10. Journey Exports

Users can export their own journey data in multiple formats:

```text
CSV
JSON
PDF
```

### Export endpoints

```text
/api/export/journeys.csv
/api/export/journeys.json
/api/export/journeys.pdf
```

Exports are ownership-scoped.

A user can export their own journeys without receiving another user's records.

PDF generation is intentionally synchronous in V1.

---

# 🔐 11. Security & Ownership

Security is treated as part of the application architecture rather than an afterthought.

API resources are scoped through the authenticated Django user:

```python
request.user
```

The application does not trust a client-supplied user ID for ownership.

For example, an unauthorized journey lookup returns:

```text
404 Not Found
```

rather than exposing whether another user's resource exists through a permission error.

### Security configuration

When:

```text
DEBUG=False
```

the application automatically enables production-oriented security behavior, including:

* HSTS
* Secure cookies
* SSL redirect
* Allowed-host configuration
* CSRF trusted-origin configuration

Secrets and environment-specific configuration remain outside the source code.

---

# 🏗️ Architecture

```text
EcoTransit/
│
├── ecotransit/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── core/
│   ├── models.py
│   ├── views.py
│   ├── admin.py
│   │
│   ├── api/
│   │   ├── exports.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── carbon.py
│   │   ├── distance.py
│   │   ├── integrity.py
│   │   ├── openroute.py
│   │   └── gamification.py
│   │
│   ├── templates/
│   │   ├── public/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── trips/
│   │   ├── calculator/
│   │   ├── map/
│   │   ├── feedback/
│   │   ├── admin/
│   │   └── errors/
│   │
│   └── static/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   ├── API.md
│   ├── CARBON_METHODOLOGY.md
│   ├── SETUP.md
│   ├── DEPLOYMENT.md
│   ├── TESTING.md
│   └── PROJECT_REPORT.md
│
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

---

# 🧠 Application Architecture

EcoTransit separates presentation, API handling, domain models, and business logic.

```text
┌───────────────────────────────────────────┐
│               Frontend                    │
│ HTML • CSS • JavaScript • Leaflet.js     │
└────────────────────┬──────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────┐
│              Django Views                 │
│       HTML Views + JSON API Views         │
└────────────────────┬──────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────┐
│            Service Layer                  │
│                                           │
│ Carbon • Distance • Integrity             │
│ OpenRouteService • Gamification            │
└────────────────────┬──────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────┐
│              Django ORM                   │
│                                           │
│ TransportMode                             │
│ UserProfile                               │
│ Journey                                   │
│ JourneyPoint                              │
│ EmissionFactorSnapshot                    │
│ AchievementLog                            │
└────────────────────┬──────────────────────┘
                     │
                     ▼
          SQLite / PostgreSQL
```

---

# 🧩 Domain Models

EcoTransit implements six core domain models:

```text
TransportMode
UserProfile
Journey
JourneyPoint
EmissionFactorSnapshot
AchievementLog
```

These represent the core data relationships required by the V1 specification.

Fields that were not explicitly named in the governing specification are marked as assumptions directly in the implementation.

---

# ⚙️ Service Layer

## `carbon.py`

Responsible for:

* Carbon calculations
* Driving/car baseline comparison
* Historical emission-factor snapshots

## `distance.py`

Responsible for:

* Haversine distance calculation
* Distance calculation from recorded GPS points

## `integrity.py`

Responsible for:

* SHA-256 hashing
* Decimal quantization
* Tamper detection

## `openroute.py`

Responsible for:

* OpenRouteService communication
* Routing
* Forward geocoding
* Reverse geocoding
* External-service error handling

## `gamification.py`

Responsible for:

* Points
* Streaks
* Achievement milestones
* Achievement bonuses
* Concurrency protection
* Idempotency

---

# 🔌 API Reference

EcoTransit uses plain Django JSON views rather than Django REST Framework.

## Journey API

| Endpoint                     | Method | Purpose                       |
| ---------------------------- | ------ | ----------------------------- |
| `/api/journeys/`             | GET    | Authenticated user's journeys |
| `/api/journeys/start/`       | POST   | Start a journey               |
| `/api/journeys/<id>/points/` | POST   | Add GPS point                 |
| `/api/journeys/<id>/stop/`   | POST   | Finalize journey              |
| `/api/journeys/<id>/`        | GET    | Retrieve owned journey        |

### Start a journey

```text
POST /api/journeys/start/
```

Required:

```text
transport_mode
legal_disclaimer_accepted: true
```

An already-active journey results in:

```text
409 Conflict
```

### Add a point

```text
POST /api/journeys/<id>/points/
```

The sequence number is assigned automatically.

An inactive journey results in:

```text
409 Conflict
```

### Complete a journey

```text
POST /api/journeys/<id>/stop/
```

The completion pipeline is:

```text
Distance
   ↓
Carbon
   ↓
Integrity Hash
   ↓
Points
   ↓
Streak
   ↓
Achievements
```

All operations are performed atomically.

---

# 🚌 Transport Modes API

```text
GET /api/transport-modes/
```

Returns active transport modes.

---

# 👤 Profile API

```text
GET /api/profile/
```

Returns the authenticated user's `UserProfile`, including current points and streak information.

---

# 🧭 Routing API

```text
GET /api/routes/
POST /api/routes/
```

Uses OpenRouteService.

Possible service responses:

```text
503 — Service not configured
502 — External routing service failure
```

---

# 🔎 Geocoding API

```text
GET /api/geocode/
POST /api/geocode/
```

Supports:

* Forward geocoding
* Reverse geocoding

---

# 🧮 Gamification Transaction Model

One of the important architectural decisions in EcoTransit is that gamification does not operate independently from journey completion.

The completion process is effectively:

```text
BEGIN TRANSACTION
        │
        ▼
Finalize Journey
        │
        ▼
Calculate Distance
        │
        ▼
Calculate Carbon
        │
        ▼
Generate Integrity Hash
        │
        ▼
Lock UserProfile
        │
        ▼
Calculate Points
        │
        ▼
Update Streak
        │
        ▼
Evaluate Achievements
        │
        ▼
COMMIT
```

If an operation fails:

```text
ROLLBACK
```

This prevents partially completed journey states.

---

# 🔒 Concurrency & Idempotency

The user's `UserProfile` is row-locked using:

```python
select_for_update()
```

during the gamification operation.

This protects:

* `total_points`
* streak counters
* achievement awards

against concurrent completion requests.

Cumulative achievements additionally perform existence checks so a milestone cannot accidentally be awarded multiple times.

---

# 🗄️ Database Support

## Local Development

SQLite is used automatically.

No separate database server is required.

## PostgreSQL

Set:

```env
DATABASE_URL=postgres://user:password@localhost:5432/ecotransit
```

PostgreSQL takes precedence over SQLite when `DATABASE_URL` is configured.

The project includes `psycopg2-binary` for PostgreSQL connectivity.

---

# 🛠️ Technology Stack

| Layer               | Technology                      |
| ------------------- | ------------------------------- |
| Language            | Python                          |
| Web Framework       | Django                          |
| Local Database      | SQLite                          |
| Production Database | PostgreSQL                      |
| Frontend            | HTML / CSS / Vanilla JavaScript |
| Mapping             | Leaflet.js                      |
| Routing             | OpenRouteService                |
| Geocoding           | OpenRouteService                |
| API                 | Django JSON Views               |
| Authentication      | Django Authentication           |
| Hashing             | SHA-256                         |
| Configuration       | django-decouple                 |
| Static Files        | Whitenoise                      |
| Production Server   | Gunicorn / Uvicorn              |
| Testing             | Django Test Framework           |

---

# ⚡ Quick Start

## 1. Clone

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ecotransit
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with your repository URL.

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Create environment configuration

### Windows

```bash
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Then edit `.env`.

For anything beyond throwaway local testing, configure a real:

```env
DJANGO_SECRET_KEY=your-secure-secret-key
```

---

## 5. Run migrations

```bash
python manage.py migrate
```

---

## 6. Create an administrator

```bash
python manage.py createsuperuser
```

---

## 7. Start EcoTransit

```bash
python manage.py runserver
```

---

# 🌐 Application URLs

| Interface           | URL                                      |
| ------------------- | ---------------------------------------- |
| 🌱 Main Application | `http://127.0.0.1:8000/`                 |
| 🔐 Admin            | `http://127.0.0.1:8000/admin/`           |
| 📈 Admin Analytics  | `http://127.0.0.1:8000/admin/analytics/` |
| 🔌 API              | `http://127.0.0.1:8000/api/`             |

The main frontend redirects to `/login/` when authentication is required.

---

# 🧪 Testing

EcoTransit includes a comprehensive automated test suite.

## Current status

```text
150 tests
150 passing
0 regressions
```

### Test distribution

| Test File                    | Tests | Coverage                                                                                                    |
| ---------------------------- | ----: | ----------------------------------------------------------------------------------------------------------- |
| `core/tests.py`              |    33 | Domain models, relationships, validation, `__str__`, cascade, `SET_NULL`, `PROTECT`                         |
| `core/test_services.py`      |    32 | Carbon calculation, OpenRouteService wrapper, SHA-256 hashing, tamper detection                             |
| `core/tests_api.py`          |    44 | Journey API lifecycle, authentication, ownership, transport modes, profile, routes, geocoding, gamification |
| `core/tests_exports.py`      |    16 | CSV, JSON, PDF exports, ownership scoping, admin analytics                                                  |
| `core/tests_gamification.py` |    25 | Points, streaks, achievements, idempotency                                                                  |

---

## Run tests

```bash
python manage.py test
```

---

# 🔍 Django System Checks

Run:

```bash
python manage.py check
```

For deployment-oriented checks:

```bash
python manage.py check --deploy
```

The project has been verified under both development and production-like configuration.

The production-like configuration uses:

```text
DJANGO_DEBUG=False
```

along with a genuinely random secret key and real allowed hosts.

The production-like configuration produced:

```text
0 deployment warnings
```

---

# 🌐 Environment Variables

EcoTransit uses environment-driven configuration through `django-decouple`.

Important variables include:

```env
DJANGO_SECRET_KEY=
DJANGO_DEBUG=
DJANGO_ALLOWED_HOSTS=
DJANGO_CSRF_TRUSTED_ORIGINS=
DATABASE_URL=
OPENROUTESERVICE_API_KEY=
```

### Security rule

Never commit real credentials or secrets to GitHub.

Use:

```text
.env.example
```

as the safe configuration template.

---

# 🧭 OpenRouteService Setup

Routing and geocoding require an OpenRouteService API key.

Configure:

```env
OPENROUTESERVICE_API_KEY=your_api_key_here
```

When no key is configured, routing/geocoding endpoints intentionally return a controlled `503` response.

When the external service itself fails, the application returns a controlled `502` response.

---

# 📈 Admin Analytics

EcoTransit provides a staff-only analytics page:

```text
/admin/analytics/
```

The current implementation intentionally exposes **aggregate platform statistics only**.

It does not provide per-user analytics through the admin analytics interface.

---

# 👤 User Management

The current V1 intentionally does not include:

* Public registration/signup
* Password-reset email flow

Users can be created using:

```bash
python manage.py createsuperuser
```

or through Django Admin.

This is an intentional V1 scope decision.

---

# 🧠 Engineering Highlights

EcoTransit is more than a CRUD application.

Several implementation decisions were made specifically to preserve consistency and maintainability.

### Historical data protection

Emission factors are snapshotted when journeys are calculated.

### Atomic journey completion

Carbon, integrity, points, streaks, and achievements are finalized within one transaction.

### Concurrency protection

`select_for_update()` protects user-level gamification state.

### API ownership

Authenticated user ownership is enforced server-side.

### Controlled external APIs

OpenRouteService failures are normalized.

### Stable hashing

Decimal values are quantized before hashing to reduce inconsistencies across database round-trips.

### Explicit assumptions

Non-specified implementation assumptions are identified in the code.

### Focused architecture

V1 avoids unnecessary infrastructure such as Celery, Redis, and DRF.

---

# 🚫 Explicit V1 Scope Boundaries

The following are intentionally **not implemented** in V1:

```text
AI / RAG
Blockchain
Payments
Social features
Celery
Redis
Background workers
Per-user admin analytics
Public registration/signup
Password-reset email flow
```

Exports remain synchronous by design.

These exclusions are deliberate and preserve the defined V1 architecture rather than introducing infrastructure that the current project does not require.

---

# 🏭 Production Deployment Checklist

Before deploying EcoTransit:

### Environment

```text
[ ] DJANGO_DEBUG=False
[ ] Real random DJANGO_SECRET_KEY
[ ] Correct DJANGO_ALLOWED_HOSTS
[ ] Correct CSRF trusted origins
[ ] Real PostgreSQL DATABASE_URL
[ ] Real OpenRouteService API key
```

### Django

```bash
python manage.py migrate
python manage.py collectstatic
python manage.py check --deploy
```

### Infrastructure

```text
[ ] Production WSGI/ASGI server
[ ] Reverse proxy
[ ] TLS/HTTPS
[ ] Proper static-file hosting/CDN
[ ] Production database
```

The application security settings assume a deployment architecture with HTTPS and an appropriate reverse proxy.

---

# 📚 Documentation Structure

The project documentation can be organized as:

```text
docs/
├── ARCHITECTURE.md
├── DATABASE.md
├── API.md
├── CARBON_METHODOLOGY.md
├── SETUP.md
├── DEPLOYMENT.md
├── TESTING.md
└── PROJECT_REPORT.md
```

This README provides the high-level project overview while the documentation directory can contain deeper implementation details.

---

# 📊 V1 Completion Status

## 🟢 V1 COMPLETE

```text
Core domain models          ✅
User profiles              ✅
Transport modes            ✅
Journey lifecycle          ✅
GPS points                 ✅
Distance calculation       ✅
Carbon calculation         ✅
Emission snapshots         ✅
Integrity hashing          ✅
Leaflet maps               ✅
OpenRouteService routing   ✅
Geocoding                  ✅
Journey history            ✅
Journey details            ✅
CSV export                 ✅
JSON export                ✅
PDF export                 ✅
Green points               ✅
Streak tracking            ✅
Achievements               ✅
Admin analytics            ✅
Ownership enforcement      ✅
Security configuration     ✅
Automated testing          ✅
Deployment checks          ✅
```

### 🧪 Test Result

```text
┌─────────────────────────────┐
│      ECOTRANSIT V1          │
│                             │
│     150 TESTS PASSING       │
│        0 REGRESSIONS        │
│                             │
│          STATUS: ✅          │
└─────────────────────────────┘
```

---

# 🔮 Future Evolution

The current V1 is intentionally focused.

Future development should be introduced through deliberate specification changes rather than silently expanding the existing architecture.

Potential future directions may include:

* Expanded transport options
* Additional mobility analytics
* More advanced visualizations
* Additional environmental indicators
* Deeper journey insights
* Additional mobility integrations
* Asynchronous processing if real workload eventually justifies it

These are future possibilities, not current V1 requirements.

---

# 🌱 Project Philosophy

EcoTransit is built around a simple principle:

> **Make sustainable mobility measurable, understandable, and engaging.**

The platform connects:

```text
MOBILITY
   +
LOCATION
   +
DISTANCE
   +
ENVIRONMENTAL IMPACT
   +
GAMIFICATION
   =
VISIBLE SUSTAINABLE PROGRESS
```

A journey becomes more than a start point and destination.

It becomes a measurable record of movement, environmental impact, personal progress, and sustainable behavior.

---

# ⚠️ Important Disclaimer

EcoTransit provides **estimated environmental-impact calculations and digital journey records** based on information available to the application.

EcoTransit does not claim that its journey records are:

* Certified legal evidence
* Official government records
* Verified carbon offsets
* Independently audited emissions reductions
* A substitute for official transport documentation
* A substitute for certified environmental documentation
* A substitute for legal advice or official legal evidence

Where legal, regulatory, environmental, or professional certification is required, users should rely on the appropriate official authorities and certified records.

---

# 📄 License

Add the repository's actual chosen license here.

For example:

```text
MIT License
```

If the project uses a different license, replace the example with the correct license information.

---

# 👨‍💻 Project

**EcoTransit**

### Smart Urban Mobility & Environmental-Impact Platform

```text
Track.
Measure.
Understand.
Move Sustainably.
```

🌱 **Every journey can tell a story about its impact.**

---

<p align="center">
  Built with Python • Django • Leaflet.js • OpenRouteService
</p>

<p align="center">
  <strong>EcoTransit V1 — Complete</strong>
</p>


## 📺 Project Demo & Presentation

Want to see the project in action? Check out the video walkthrough and presentation assets:

* 🎥 **[Watch the Project Demo on Google Drive](https://drive.google.com/file/d/1W1z4iBQhO_GHhJMmgiKvM6NBgVcYGnj3/view?usp=sharing)** *(Make sure your Google Drive link is set to "Anyone with the link can view")*

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for full terms.

Copyright (c) 2026 Savio Chacko Xavier
