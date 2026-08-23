# FloodGuard AI — Pune Flood Decision Support Platform

A hyperlocal flood intelligence system for Pune city that fuses machine learning, rule-based prevention, environmental monitoring, and real-time alert delivery into a single operational dashboard. Built for the **Smart India Hackathon 2026**.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLOODGUARD AI — PUNE                         │
├─────────────┬──────────────┬──────────────┬─────────────────────┤
│  MODULE 1   │   MODULE 2   │   MODULE 3   │      MODULE 4       │
│ Vulnerability│  Live Risk   │  Prevention  │  Environmental      │
│ (XGBoost+   │ (Isolation   │  (Rule-based │  (Heat + Water      │
│  SHAP)      │  Forest)     │   Engine)    │   Deficit)          │
├─────────────┴──────────────┴──────────────┴─────────────────────┤
│                    MODULE 5 — DELIVERY LAYER                     │
│         FastAPI Backend  ·  Dual Alert System  ·  ViaSocket      │
├─────────────────────────────────────────────────────────────────┤
│                      FRONTEND (HTML/CSS/JS)                      │
│   Live Map  ·  Analyze Risk  ·  Forecast  ·  Alerts  ·  Routes  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Modules

### Module 1 — Vulnerability Index (XGBoost + SHAP)

Computes a transparent, explainable vulnerability score (0–100) for each of Pune's 4 IMD grid cells using geospatial features.

| Component | Detail |
|---|---|
| **Target** | `hydrologic_vulnerability_proxy` — rule: distance-to-drainage ≤ 700m AND elevation < 35th percentile |
| **Model** | XGBoost classifier (tree-based, fast inference) |
| **Explainability** | SHAP (SHapley Additive exPlanations) — per-zone factor contributions |
| **Output** | Vulnerability score, level (LOW/MODERATE/HIGH/CRITICAL), ranked contributing factors |
| **Data** | Drainage distance, elevation, slope, land cover, road density, river proximity |

### Module 2 — Live Risk Assessment (Isolation Forest)

Real-time anomaly-based risk scoring using the frozen Isolation Forest model on verified IMD rainfall data.

| Component | Detail |
|---|---|
| **Model** | Isolation Forest (unsupervised anomaly detection) |
| **Weights** | Anomaly 45% + Temporal Rainfall 30% + Vulnerability 25% |
| **Trend** | 7-day rolling window — RISING / STABLE / FALLING |
| **Levels** | LOW (<30) / MODERATE (30–59) / HIGH (60–79) / CRITICAL (≥80) |
| **Frozen** | Model outputs pre-computed — no runtime retraining |

### Module 3 — Prevention Engine (Rule-Based)

Context-aware action recommendations based on risk level, vulnerability, citizen reports, and environmental conditions.

| Feature | Detail |
|---|---|
| **Rules** | 15+ conditional rules with priority escalation |
| **Inputs** | Risk level, vulnerability score, citizen reports, environmental data |
| **Output** | Priority level, recommended actions, operational checklist, rule trace |
| **Citizen Reports** | Public can submit incident reports that escalate prevention priority |

### Module 4 — Environmental Proxies (Heat + Water Deficit)

Supplementary environmental context using IMD gridded temperature and rainfall data.

| Feature | Detail |
|---|---|
| **Heat Score** | Max temperature percentile (high heat = infrastructure stress) |
| **Water Deficit** | Cumulative rainfall deficit against long-term mean |
| **Data Source** | IMD gridded daily datasets (2015–2025) |
| **Fallback** | UNAVAILABLE when data is missing — never fabricated |

### Module 5 — Delivery Layer

FastAPI backend with role-based access control and dual alert delivery system.

| Feature | Detail |
|---|---|
| **Backend** | FastAPI (Python) — 20+ REST API endpoints |
| **Auth** | PUBLIC (citizen) and MUNICIPAL (disaster management) roles |
| **Alerts** | Dual-channel: Public (reassuring) + Municipal (operational) |
| **ViaSocket** | Webhook integration for email delivery |
| **Storage** | SQLite for citizen reports, public alerts, municipal alerts |

---

## Frontend Pages

| Page | Description |
|---|---|
| **Live Map** | Real-time zone risk visualization with SVG map, river gauge telemetry, click-to-detail panels |
| **Analyze Risk** | Full 4-module risk analysis workflow — zone selector, date picker, comprehensive results |
| **Forecast** | 365-day forecast support with pre-computed August 2026 monsoon data |
| **Actions** | Prevention recommendations with rule traces and checklists |
| **Routes** | Safe routing advisory (dataset-dependent, currently UNAVAILABLE) |
| **History** | Verified historical flood events (2014–2026 archive) |
| **Why** | Vulnerability explanation — Module 1 breakdown with SHAP factors |
| **Alerts** | Role-gated: PUBLIC sees alerts, MUNICIPAL sees send controls + internal alerts |

---

## Zone Coverage

Pune is divided into 4 IMD grid cells covering the entire city area:

| Grid ID | Zone Name | Area |
|---|---|---|
| PUNE_G001 | West-Central Pune | Kothrud, Karve Nagar, Warje |
| PUNE_G002 | East Pune | Hadapsar, Kharadi, Wagholi |
| PUNE_G003 | North-West Pune | Baner, Balewadi, Aundh |
| PUNE_G004 | North-East Pune | Yerwada, Kalyani Nagar, Viman Nagar |

---

## Alert System

### Public Alerts (Citizen-Facing)
- **Tone**: Reassuring, action-oriented, no panic-inducing language
- **Trigger**: Risk level ≥ HIGH or level change
- **Delivery**: ViaSocket webhook → Email
- **Example**: "FloodGuard Alert — West-Central Pune. Elevated risk today. Please be cautious."

### Municipal Internal Alerts (Operations)
- **Tone**: Direct, blunt, operational with exact numbers
- **Trigger**: Same as public, sent independently
- **Delivery**: ViaSocket webhook → Email
- **Example**: "ZONE ALERT: West-Central Pune (PUNE_G001). HIGH risk — waterlogging probable."

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, FastAPI, Uvicorn |
| **ML** | XGBoost, Isolation Forest, SHAP, scikit-learn, pandas |
| **Data** | IMD NetCDF rainfall, SRTM elevation, OSM drainage/roads/waterways |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript (no framework) |
| **3D Rendering** | Three.js (terrain/rain background) |
| **Animations** | anime.js, GSAP, ScrollTrigger |
| **Smooth Scroll** | Lenis |
| **Storage** | SQLite (alerts, reports), CSV (frozen ML outputs) |
| **Alerts** | ViaSocket webhook (HTTP POST) |
| **Testing** | Python unittest (55 integration + 13 validation tests) |

---

## Quick Start

### Prerequisites
- Python 3.10+
- pip

### 1. Install Dependencies
```bash
pip install fastapi uvicorn pandas numpy xgboost scikit-learn shap requests
```

### 2. Start the System
```bash
# Double-click FloodGuard.bat (Windows)
# OR manually:

# Backend (port 8000)
python -m uvicorn src.delivery.api:app --host 127.0.0.1 --port 8000

# Frontend (port 8080)
cd frontend
python -m http.server 8080
```

### 3. Open in Browser
```
http://localhost:8080
```

### Demo Login
| Role | Username | Password |
|---|---|---|
| PUBLIC | `citizen` | `citizen-demo` |
| MUNICIPAL | `municipal` | `municipal-demo` |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Backend health check |
| GET | `/api/zones?date=` | All 4 zone summaries |
| GET | `/api/zones/{grid_id}?date=&citizen_reports=` | Single zone detail |
| GET | `/api/risk/{grid_id}?date=` | Live risk assessment |
| GET | `/api/vulnerability/{grid_id}` | Vulnerability index |
| GET | `/api/prevention/{grid_id}?date=&citizen_reports=` | Prevention recommendations |
| GET | `/api/environment/{grid_id}?date=` | Environmental scores |
| POST | `/api/risk/analyze` | Full 4-module analysis |
| POST | `/api/reports` | Submit citizen report |
| GET | `/api/reports?grid_id=` | List citizen reports |
| POST | `/api/alerts/generate` | Generate + deliver alerts via ViaSocket |
| GET | `/api/alerts/public?date=` | Public alerts for date |
| GET | `/api/alerts/municipal?date=` | Municipal alerts for date |
| POST | `/api/auth/public/login` | PUBLIC login |
| POST | `/api/auth/municipal/login` | MUNICIPAL login |

---

## Data Provenance

- **Rainfall**: IMD 0.25° daily gridded (2015–2025) — 11 years, 4 grid cells
- **Elevation**: SRTM 30m GeoTIFF
- **Drainage**: OpenStreetMap via Overpass API
- **Waterways**: OpenStreetMap via Overpass API
- **Roads**: OpenStreetMap via OSMnx
- **Land Cover**: MODIS Terra + Aqua (2015–2025)

### Frozen Dataset
`data/processed/pune_ml_dataset.csv` — 16,072 rows, 4 grid cells × 4,018 days. This dataset is immutable during the hackathon.

---

## Running Tests

```bash
# Module 5 integration (55 tests)
python tests/test_module5_integration.py

# Module 2 live risk validation (13 tests)
python tests/test_live_risk.py

# Module 3 rule engine
python tests/test_rule_engine.py

# Module 4 heat + water
python tests/test_heat_water.py

# Module 1 vulnerability
python tests/test_vulnerability.py
```

---

## Project Structure

```
flood-gaurd/
├── frontend/                  # HTML/CSS/JS frontend
│   ├── index.html             # Entry point → redirects to login
│   ├── login.html             # Auth page (PUBLIC/MUNICIPAL)
│   ├── live-map.html          # Real-time zone risk map
│   ├── analyze.html           # Full risk analysis workflow
│   ├── forecast.html          # 365-day forecast
│   ├── actions.html           # Prevention recommendations
│   ├── history.html           # Historical flood events
│   ├── why.html               # Vulnerability explanation
│   ├── routes.html            # Safe routing
│   ├── alerts.html            # Alert management (role-gated)
│   ├── css/style.css          # Global styles
│   └── js/
│       ├── api.js             # API client + auth storage
│       ├── pages.js           # Page data binding + routing
│       ├── main.js            # Curtain transitions + reveals
│       ├── background.js      # Three.js 3D terrain
│       └── hero.js            # Intro animation
├── src/
│   ├── delivery/
│   │   ├── api.py             # FastAPI application (20+ endpoints)
│   │   ├── aggregator.py      # Response formatting + role views
│   │   └── citizen_reports.py # Citizen report CRUD
│   ├── alerts/
│   │   ├── generate.py        # Alert generation + ViaSocket delivery
│   │   ├── store.py           # SQLite alert storage
│   │   └── auth.py            # Role-based authentication
│   ├── risk/
│   │   ├── live_risk.py       # Isolation Forest risk scoring
│   │   ├── rule_engine.py     # Prevention rule engine
│   │   └── heat_water.py      # Environmental proxies
│   ├── vulnerability/
│   │   ├── vulnerability_index.py  # XGBoost vulnerability
│   │   ├── shap_explainer.py       # SHAP explanations
│   │   └── xgboost_predict.py      # Model inference
│   ├── ml/
│   │   ├── anomaly_model.py   # Isolation Forest training
│   │   └── feature_preparation.py
│   └── integration/
│       └── viasocket_client.py # ViaSocket HTTP client
├── data/
│   ├── processed/             # Cleaned datasets
│   ├── raw/                   # IMD NetCDF, SRTM elevation
│   └── config/                # Pipeline configuration
├── outputs/
│   ├── vulnerability/         # XGBoost model + SHAP plots
│   ├── ml/                    # Anomaly scores + metrics
│   ├── risk/                  # Risk scores
│   └── forecast/              # Pre-computed forecasts
├── tests/                     # 68 test cases
├── docs/                      # Module documentation
├── reports/                   # Validation reports
└── FloodGuard.bat             # One-click launcher (Windows)
```

---

## Key Design Decisions

1. **No fabrication**: Missing data is displayed as `UNAVAILABLE` — never zero or invented
2. **Frozen ML**: Isolation Forest outputs are pre-computed; no runtime retraining
3. **Transparency**: Every vulnerability score comes with SHAP explanations
4. **Dual alerts**: Public citizens get reassuring messages; MUNICIPAL gets blunt operational data
5. **Role-based access**: PUBLIC sees simplified views; MUNICIPAL gets full operational dashboard
6. **Plain frontend**: No React/Vue/Angular — vanilla HTML/CSS/JS for zero build step

---

## License

Built for Smart India Hackathon 2026. Internal use only.
