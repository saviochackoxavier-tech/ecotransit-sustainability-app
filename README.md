# 🌱 EcoTransit — Smart Urban Mobility & Environmental-Impact Platform

<p align="center">
  <img src="https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-dashboard-hero.png" alt="EcoTransit dashboard hero" width="100%">
</p>

<p align="center">
  <strong>A professional full-stack web application prototype for measurable, gamified, and privacy-aware sustainable urban mobility.</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-carbon-methodology">Carbon Methodology</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-testing">Testing</a> •
  <a href="#-presentation--project-story">Presentation</a> •
  <a href="#-quick-start">Quick Start</a>
</p>

<p align="center">
  <a href="https://github.com/saviochackoxavier-tech/ecotransit-sustainability-app">
    <img src="https://img.shields.io/badge/GitHub-EcoTransit-181717?logo=github" alt="GitHub">
  </a>
  <img src="https://img.shields.io/badge/Python-3.x-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Django-Web%20Framework-green?logo=django" alt="Django">
  <img src="https://img.shields.io/badge/Leaflet-Maps-brightgreen?logo=leaflet" alt="Leaflet">
  <img src="https://img.shields.io/badge/Tests-150-success" alt="150 automated tests">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License">
</p>

---

## 📌 Project Snapshot

**EcoTransit** is a Django-based smart urban mobility platform that turns everyday journeys into measurable sustainability records.

It combines:

* 🚌 Sustainable transport tracking
* 📍 Manual and live GPS journey capture
* 🗺️ Leaflet-based maps
* 🧭 OpenRouteService routing and geocoding
* 🌱 Carbon-savings estimation
* 🏆 Green points, achievements, and streaks
* 📊 Journey history and analytics
* 📄 CSV / JSON / PDF exports
* 🔐 Ownership checks, secure configuration, and integrity hashing
* 🧪 Automated unit, integration, API, export, and gamification tests
* 👨‍💼 Staff-facing analytics and emission-factor management

> **Project positioning:** EcoTransit V1 is a **professional full-stack web application prototype** designed for demonstration, internship evaluation, academic/project presentation, and further development.

---

## 🎯 Vision

EcoTransit is built around a simple idea:

> **Make every journey visible, comparable, and actionable.**

A commuter should be able to record a journey, understand its estimated environmental impact, see how sustainable transport contributes to personal progress, and review their journey history over time.

The platform is aligned with:

* **SDG 11 — Sustainable Cities and Communities**
* **SDG 13 — Climate Action**

---

# ✨ Features

| Area              | V1 Capability                                                            |
| ----------------- | ------------------------------------------------------------------------ |
| 🔐 Authentication | User authentication, profiles, ownership controls                        |
| 🚶 Transport      | Walking, cycling, public transit, EV and driving/ICE modes               |
| 🧭 Journeys       | Create, update, complete, view and review journey records                |
| 📍 GPS            | Browser-based live journey tracking and journey points                   |
| 🗺️ Maps          | Leaflet map interface with route/geocoding integration                   |
| 🌱 Carbon         | Baseline-vs-actual estimated CO₂ savings                                 |
| 🏆 Gamification   | Points, achievements and sustainable-day streaks                         |
| 📚 History        | Historical journeys with preserved calculation snapshots                 |
| 📊 Analytics      | Personal dashboard and staff/admin analytics                             |
| 📤 Exports        | CSV, JSON and PDF journey reports                                        |
| 🔏 Integrity      | SHA-256 journey integrity hashes                                         |
| 🧪 Quality        | 150 automated tests                                                      |
| ⚙️ Deployment     | SQLite locally, PostgreSQL through `DATABASE_URL`, Gunicorn + WhiteNoise |
| 🛡️ Security      | Ownership checks, environment secrets, production security settings      |
| 📝 Auditability   | Append-only audit-log design and deterministic calculations              |

---

# 🖼️ Product Screens & Visuals

## Dashboard

![EcoTransit dashboard hero](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-dashboard-hero.png)

The dashboard brings together the user's sustainability metrics, journey activity, progress, and core actions in one place.

---

## Live Tracking & Map

![EcoTransit live tracking map](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-live-tracking-map.png)

The map experience supports journey capture using browser geolocation, route visualization, and the configured routing/geocoding services.

---

## Gamification

![EcoTransit gamification achievements](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-gamification-achievement.png)

Achievements, points, and streaks turn repeated sustainable travel into visible progress.

---

## Journey History

![EcoTransit journey history](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-journey-history.png)

Journey history preserves completed records and their calculation snapshots so later emission-factor changes do not silently rewrite historical results.

---

# 🧩 Core Journey Flow

```text
┌──────────────────┐
│ Start a Journey  │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Capture Route /  │
│ GPS Journey Data │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Determine Mode + │
│ Distance         │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Calculate Actual │
│ Emissions        │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Compare with     │
│ Car Baseline     │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Save Historical  │
│ Snapshots        │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ Award Points +   │
│ Update Streaks   │
└────────┬─────────┘
         ↓
┌──────────────────┐
│ History / Export │
│ / Analytics      │
└──────────────────┘
```

---

# 🌍 Problem & Project Foundation

Urban commuters often lack a simple way to connect daily transport choices with measurable environmental impact.

EcoTransit addresses three practical gaps:

1. **Visibility** — users can see the estimated carbon impact of their journeys.
2. **Engagement** — points, achievements, and streaks make sustainable travel progress visible.
3. **Data** — aggregated staff-facing analytics can help demonstrate mobility patterns within the prototype.

## Target Users

* **Urban commuters** — track everyday travel and environmental impact.
* **Students and campuses** — use gamified milestones to encourage sustainable mobility.
* **Municipal / planning stakeholders** — explore aggregated mobility insights within the prototype.
* **Environmental users / advocates** — inspect transparent calculation rules and journey metrics.

---

# 🌱 SDG Alignment

## SDG 11 — Sustainable Cities and Communities

EcoTransit promotes lower-emission urban transport choices such as:

* Walking
* Cycling
* Public transit
* Electric vehicles

## SDG 13 — Climate Action

EcoTransit quantifies estimated carbon savings for journeys relative to a configured private-car baseline.

> EcoTransit measures **estimated emissions and savings**. It does not issue verified carbon offsets.

---

# 🏗️ Architecture

![EcoTransit architecture and data flow](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-architecture-flow.png)

```text
                         ┌──────────────────────┐
                         │     Web Browser      │
                         │ HTML / CSS / JS      │
                         │ Leaflet.js / GPS     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       Django         │
                         │ Views / Forms / API  │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
        ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
        │ Service Layer  │ │ Domain Models  │ │ API Layer      │
        │ Carbon         │ │ Journeys       │ │ JSON endpoints │
        │ Gamification   │ │ Profiles       │ │ Validation     │
        │ Integrity      │ │ Factors        │ │ Permissions    │
        │ OpenRoute      │ │ Achievements   │ │ Exports        │
        └───────┬────────┘ └───────┬────────┘ └────────────────┘
                │                  │
                └──────────┬───────┘
                           ▼
                 ┌────────────────────┐
                 │ SQLite / PostgreSQL│
                 └────────────────────┘

External integration:
Browser GPS ──► Journey Points
OpenRouteService ──► Routing / Geocoding
```

---

# 🧱 Project Structure

```text
ecotransit/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── LICENSE
│
├── ecotransit/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── ...
│
├── core/
│   ├── models.py
│   ├── views/
│   ├── services/
│   │   ├── carbon.py
│   │   ├── gamification.py
│   │   ├── integrity.py
│   │   └── openroute.py
│   ├── forms/
│   ├── api/
│   ├── management/
│   │   └── commands/
│   │       └── seed_demo.py
│   └── tests/
│
├── templates/
│   ├── public/
│   ├── auth/
│   ├── dashboard/
│   ├── trips/
│   ├── calculator/
│   ├── map/
│   ├── feedback/
│   ├── admin/
│   └── errors/
│
├── assets/
│   ├── ecotransit-dashboard-hero.png
│   ├── ecotransit-live-tracking-map.png
│   ├── ecotransit-gamification-achievement.png
│   ├── ecotransit-journey-history.png
│   ├── ecotransit-architecture-flow.png
│   └── presentation/
│       ├── slide-01.png
│       ├── slide-02.png
│       ├── ...
│       └── slide-11.png
│
└── static/
    └── ...
```

---

# 🗃️ Domain Model

The V1 design separates journey data, user progress, calculation factors, and integrity information.

Core concepts include:

* **User / Profile**
* **TransportMode**
* **Journey**
* **JourneyPoint**
* **EmissionFactor**
* **EmissionFactorSnapshot**
* **Achievement**
* **UserAchievement**
* **Feedback**
* **AuditLog**

### Historical calculation principle

A completed journey stores the factor used for its calculation.

```text
Current Factor
     │
     ├── Journey A → snapshot A
     │
     └── Factor changes
              │
              └── Journey B → snapshot B
```

Therefore, changing the active baseline does not retroactively rewrite Journey A.

---

# 🌱 Carbon Methodology

EcoTransit uses a deterministic baseline comparison.

The V1 baseline is based on a configured standard fuel-car factor, initially:

```text
0.12 kg CO₂ / km
```

Estimated savings are calculated as:

```text
estimated_savings =
    max(baseline_emissions - actual_emissions, 0)
```

The system preserves the baseline factor used for each journey.

### Important implementation rules

* Decimal fields are preferred for environmental quantities.
* Calculation timestamps are stored.
* The active baseline is controlled so only one baseline is active.
* Historical snapshots preserve past calculations.
* No verified carbon offsets are issued.
* Carbon values represent **estimates**, not independently audited emissions reductions.

---

# 🏆 Gamification Engine

The gamification service separates trip-earned points from achievement bonuses.

## Journey points

```text
points =
    round(max(carbon_saved_g, 0) / 1000 * 10)
    +
    round(distance_km * mode_multiplier)
```

### Transport multipliers

| Mode           | Multiplier |
| -------------- | ---------: |
| Walking        |  15 pts/km |
| Cycling        |  15 pts/km |
| Public Transit |   8 pts/km |
| EV             |   3 pts/km |
| Driving / ICE  |   0 pts/km |

## Achievements

| Achievement   | Trigger                               | Bonus |
| ------------- | ------------------------------------- | ----: |
| First Steps   | First completed journey               |   +50 |
| Eco Warrior   | Cumulative carbon saved crosses 10 kg |  +200 |
| Week of Green | 7-day sustainable streak              |  +100 |

### Streak rule

A streak is based on **consecutive calendar days with at least one qualifying sustainable trip**.

### Concurrency protection

Gamification updates use database transactions and `select_for_update()` to reduce race-condition risk.

Achievement existence/idempotency checks prevent duplicate milestone rewards.

---

# 🧭 Journey Records & Integrity

A completed journey can contain:

* Start and end information
* Transport mode
* Distance
* Duration / timestamps
* Carbon calculation
* Baseline factor used
* Journey points
* GPS journey points where applicable
* Integrity hash
* Historical calculation snapshot

## SHA-256 integrity

Journey records use SHA-256 hashing as an integrity mechanism.

The integrity service helps detect changes to the signed journey representation.

> The integrity hash is a tamper-detection mechanism; it does **not** make a journey record an official government or legal record.

---

# 📍 Maps, GPS & Routing

EcoTransit uses:

* **Leaflet.js** for map rendering
* Browser geolocation for live journey capture
* **OpenRouteService** for routing and geocoding
* Configurable external-service settings rather than hard-wiring a public geocoding endpoint

The platform is designed around foreground/manual user-controlled journey capture. V1 does not introduce background tracking.

---

# 🔌 API Reference

## Journeys

```text
GET  /api/journeys/
POST /api/journeys/start/
GET  /api/journeys/<id>/
POST /api/journeys/<id>/points/
POST /api/journeys/<id>/stop/
```

## Supporting endpoints

```text
GET /api/transport-modes/
GET /api/profile/
GET /api/routes/
GET /api/geocode/
```

## Exports

```text
GET /api/export/journeys.csv
GET /api/export/journeys.json
GET /api/export/journeys.pdf
```

## External-service failure handling

The API distinguishes configuration and upstream failures, including:

```text
503 → routing/geocoding service not configured
502 → configured external service failed
```

Authentication, CSRF protection, ownership validation, and request validation remain part of the API design.

---

# 📤 Data Export

Users can export journey information in:

* CSV
* JSON
* PDF

PDF generation uses ReportLab.

Exports are intentionally synchronous in V1. No Celery, Redis, or background worker infrastructure is introduced.

---

# 🔐 Security & Privacy

EcoTransit applies several security principles.

### Ownership

Journey access is tied to `request.user`.

Unauthorized access to another user's journey should resolve without exposing that journey's existence.

### Production configuration

When `DEBUG=False`, production-oriented settings can enable:

* HSTS
* Secure cookies
* SSL redirect
* Allowed hosts
* CSRF trusted origins

### Secrets

Secrets and deployment configuration belong in environment variables rather than source control.

### Privacy

The application avoids introducing unnecessary background tracking and keeps journey ownership explicit.

---

# 🧪 Testing

## V1 Test Status

```text
150 automated tests
0 regressions
```

| Test Area                    |   Tests |
| ---------------------------- | ------: |
| `core/tests.py`              |      33 |
| `core/test_services.py`      |      32 |
| `core/tests_api.py`          |      44 |
| `core/tests_exports.py`      |      16 |
| `core/tests_gamification.py` |      25 |
| **Total**                    | **150** |

### Validation commands

```bash
python manage.py check
python manage.py check --deploy
python manage.py test
```

The production-like deployment configuration was validated with zero deployment warnings in the documented V1 verification.

---

# 📊 Presentation & Project Story

The accompanying **EcoTransit V1 presentation** presents the project as an AI-for-sustainability internship prototype and covers the foundation, problem, target users, solution, architecture, workflow, testing, responsible design, expected impact, and conclusion.

## 📥 Presentation

**[Download / View EcoTransit V1 Presentation (PPTX)](https://github.com/saviochackoxavier-tech/ecotransit-sustainability-app/raw/main/assets/EcoTransit-V1-Presentation.pptx)**

---

## 🎥 Project Demo

**[▶️ Watch the EcoTransit Project Demo on Google Drive](https://drive.google.com/file/d/1W1z4iBQhO_GHhJMmgiKvM6NBgVcYGnj3/view?usp=sharing)**

> Make sure the Google Drive file is configured as **“Anyone with the link can view”** if you want public GitHub visitors to access the demo.

---

# 🧠 Service Layer

The service-oriented implementation keeps important business rules outside presentation code.

```text
core/services/
├── carbon.py
├── gamification.py
├── integrity.py
└── openroute.py
```

### `carbon.py`

Responsible for deterministic emission and savings calculations.

### `gamification.py`

Responsible for:

* journey points
* mode multipliers
* achievements
* streak validation
* transaction safety

### `integrity.py`

Responsible for deterministic journey hashing and integrity verification.

### `openroute.py`

Responsible for routing/geocoding integration and external-service error handling.

---

# ⚙️ Database & Deployment

## Local development

```text
SQLite
```

## Production-capable database configuration

```text
PostgreSQL via DATABASE_URL
```

## Application serving

```text
Gunicorn + WhiteNoise
```

## Configuration

```text
.env.example
```

Sensitive values should be supplied through environment variables.

---

# 🚀 Quick Start

## 1. Clone

```bash
git clone https://github.com/saviochackoxavier-tech/ecotransit-sustainability-app.git
cd ecotransit-sustainability-app
```

## 2. Create a virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment

### Windows

```bash
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Configure required values such as:

```text
SECRET_KEY
DEBUG
ALLOWED_HOSTS
DATABASE_URL
OPENROUTESERVICE_API_KEY
```

## 5. Apply migrations

```bash
python manage.py migrate
```

## 6. Create an administrator

```bash
python manage.py createsuperuser
```

## 7. Optional demo data

```bash
python manage.py seed_demo
```

## 8. Run the development server

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

---

# 🌐 Main Application Areas

Typical V1 areas include:

```text
/
├── /about/
├── /methodology/
├── /privacy/
├── /terms/
│
├── /dashboard/
├── /profile/
│
├── /trips/
├── /calculator/
├── /map/
├── /feedback/
│
└── /admin/
```

Exact routes should follow the repository's current URL configuration.

---

# 📚 Documentation

Recommended project documentation:

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

The V1 presentation and visual assets are maintained in the repository's `assets/` directory.

---

# 🚫 V1 Scope Boundaries

The following are intentionally outside V1:

* ❌ AI / RAG
* ❌ Blockchain
* ❌ Payments
* ❌ Social features
* ❌ Celery
* ❌ Redis
* ❌ Background workers
* ❌ Per-user admin analytics
* ❌ Public registration/signup
* ❌ Password-reset email workflow
* ❌ Background GPS tracking
* ❌ Verified carbon offsets

These exclusions keep the V1 implementation focused on the frozen project specification.

---

# 🔮 Future Evolution

Potential future versions may explore:

* richer route intelligence
* larger-scale aggregated mobility analytics
* improved accessibility
* additional transport modes
* configurable regional emission datasets
* stronger deployment observability
* optional AI-assisted insights

Future work should be introduced deliberately without silently changing the V1 data model or calculation rules.

---

# 🧭 Project Philosophy

EcoTransit is designed around five principles:

### 1. Measure

Turn journeys into structured data.

### 2. Compare

Use a transparent baseline methodology.

### 3. Reward

Make sustainable behavior visible through points and achievements.

### 4. Preserve

Keep historical calculation snapshots stable.

### 5. Explain

Prefer deterministic, auditable rules over opaque behavior.

---

# ⚠️ Important Disclaimer

EcoTransit journey records are **not**:

* certified legal evidence
* official government records
* verified carbon offsets
* independently audited emissions reductions
* a substitute for official documentation
* a substitute for legal advice

Journey records and environmental calculations are provided for personal tracking, demonstration, analytics, and sustainability-awareness purposes.

---

# 📈 V1 Completion Snapshot

```text
Core Django Application       ✅
Authentication / Profiles     ✅
Journey Management            ✅
GPS Journey Capture           ✅
Leaflet Maps                  ✅
Routing / Geocoding           ✅
Carbon Calculations           ✅
Historical Snapshots          ✅
Gamification                  ✅
Achievements                  ✅
Streaks                       ✅
Journey Integrity Hashing     ✅
CSV / JSON / PDF Exports      ✅
Feedback                      ✅
Staff/Admin Analytics         ✅
Emission Factor Management    ✅
Automated Tests               ✅
Production Checks             ✅
Documentation                 ✅
Presentation                  ✅
```

---

# 🛠️ Technology Stack

| Layer               | Technology                    |
| ------------------- | ----------------------------- |
| Language            | Python                        |
| Backend             | Django                        |
| Frontend            | HTML, CSS, Vanilla JavaScript |
| Maps                | Leaflet.js                    |
| Routing / Geocoding | OpenRouteService              |
| Local Database      | SQLite                        |
| Production Database | PostgreSQL                    |
| Application Serving | Gunicorn                      |
| Static Files        | WhiteNoise                    |
| PDF Export          | ReportLab                     |
| Integrity           | SHA-256                       |
| Testing             | Django / Python test suite    |

---

# 📄 License

This project is licensed under the **MIT License**.

See the [`LICENSE`](LICENSE) file for the complete license terms.

```text
MIT License

Copyright (c) 2026 Savio Chacko Xavier
```

---

# 🌱 Final Note

> **One journey at a time. One measurable choice at a time.**

EcoTransit V1 demonstrates how a full-stack web application can connect mobility tracking, transparent carbon estimation, gamification, historical data, and responsible software design into one coherent sustainability platform.

---

## 🔗 Project Resources

| Resource                 | Link                                                                                                                                                                  |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🌐 GitHub Repository     | [EcoTransit on GitHub](https://github.com/saviochackoxavier-tech/ecotransit-sustainability-app)                                                                       |
| 🎥 Project Demo          | [Watch on Google Drive](https://drive.google.com/file/d/1W1z4iBQhO_GHhJMmgiKvM6NBgVcYGnj3/view?usp=sharing)                                                           |
| 📊 Presentation          | [Download / View EcoTransit V1 Presentation](https://github.com/saviochackoxavier-tech/ecotransit-sustainability-app/raw/main/assets/EcoTransit-V1-Presentation.pptx) |
| 🖼️ Dashboard Image      | [View PNG](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-dashboard-hero.png)                          |
| 🗺️ Live Tracking Image  | [View PNG](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-live-tracking-map.png)                       |
| 🏆 Gamification Image    | [View PNG](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-gamification-achievement.png)                |
| 📚 Journey History Image | [View PNG](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-journey-history.png)                         |
| 🏗️ Architecture Image   | [View PNG](https://raw.githubusercontent.com/saviochackoxavier-tech/ecotransit-sustainability-app/main/assets/ecotransit-architecture-flow.png)                       |

---

<p align="center">
  <strong>🌱 EcoTransit — Smart Mobility. Measurable Impact. Sustainable Cities.</strong>
</p>

<p align="center">
  Built by <strong>Savio Chacko Xavier</strong> · 2026
</p>


