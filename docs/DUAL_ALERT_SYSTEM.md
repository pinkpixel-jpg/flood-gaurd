# DUAL ALERT SYSTEM — PUBLIC & MUNICIPAL

Status: **COMPLETE** · Same dashboard, same risk engine, two separate
alert stores and role-gated views.

## Architecture

```
Login (POST /api/auth/public|munical/login)   ← see note: /municipal/login
        ↓  Bearer token (24 h, hashed-at-rest)
PUBLIC or MUNICIPAL role
        ↓
SAME EXISTING DASHBOARD (alerts.html becomes role-aware)
        ↓
Role-specific ALERTS ONLY
   ├─ data/public_alerts.db     (citizen-friendly payloads)
   └─ data/municipal_alerts.db  (operational payloads)
```

## Authentication (`src/alerts/auth.py`)

- PBKDF2-HMAC-SHA256, 120 000 iterations, per-user salt.
- Opaque bearer tokens; only SHA-256 hashes stored server-side; 24 h expiry.
- Roles enforced **backend-side** (`Authorization: Bearer`) — frontend
  hiding is cosmetic only.
- DEMO seed accounts (auto-created): `citizen/citizen-demo` (PUBLIC),
  `municipal/municipal-demo` (MUNICIPAL). Replace before any real use.

## Endpoints

| Method | Path | Auth |
| :--- | :--- | :--- |
| POST | `/api/auth/public/login` | none |
| POST | `/api/auth/municipal/login` | none |
| GET | `/api/auth/me` | bearer |
| GET | `/api/alerts/public?date&grid_id` | any authenticated user |
| GET | `/api/alerts/public/history` | any authenticated user |
| POST | `/api/alerts/public/preferences` | PUBLIC (+MUNICIPAL) |
| GET/POST | `/api/alerts/municipal(/history\|preferences)` | **MUNICIPAL only (403 otherwise)** |

## Payload shapes

PUBLIC:
```json
{"date","grid_id","risk_level","risk_score","trend",
 "simple_explanation","safety_recommendation","mode",
 "disclaimer":"HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING"}
```

MUNICIPAL:
```json
{"date","grid_id",
 "risk":{"score","level","trend","components":{anomaly,temporal_rainfall,vulnerability}},
 "vulnerability":{"score","level"},
 "prevention":{"priority","recommended_actions","checklist","explanations"},
 "environment":{...Module 4...},
 "citizen_reports":{"count":N},
 "metadata":{...}}
```

(Storage rows are flat for SQLite simplicity; the API returns the nested
shapes above via `generate.py`.)

## Generation rule

Alerts are generated from the FROZEN Module 2 output
(`get_live_risk`) + Module 3 (`evaluate_prevention`) + delivery
aggregation. No new risk calculation exists anywhere in this package.
Generation is idempotent per date (skipped if the date already has rows).

## Frontend behaviour (`alerts.html`)

- No session → login card (role picker + demo credentials shown).
- PUBLIC session → simple citizen alert list.
- MUNICIPAL session → operational list incl. components, vulnerability,
  priority, actions, checklist, citizen counts.
- Sign-out link; history count toast; every panel carries the
  HISTORICAL REPLAY badge.

## Tests

`tests/test_dual_alerts.py` → **13/13 PASS** plus automatic re-run of all
five module suites → **55/55 backend tests PASS**.
