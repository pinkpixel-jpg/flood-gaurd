# FRONTEND ↔ BACKEND INTEGRATION

Status: **WORKING** · Plain HTML/CSS/JS frontend (unchanged UI) ·
FastAPI backend · No secrets in frontend.

## Architecture

```
frontend/  (existing HTML/CSS/JS — design preserved)
   │  fetch()  →  js/api.js  (single API_BASE)
   ▼
http://localhost:8000/api   (FastAPI, CORS: localhost:8080/5500 only)
   ▼
Modules 1–4 (frozen) ──► ViaSocket event builder (backend-only)
```

## Page → API mapping

| Page | Data needed | Backend call |
| :--- | :--- | :--- |
| index.html | zones count, replay date, highest zone risk | `GET /api/zones` |
| live-map.html | per-zone risk feed, river-telemetry status, map dot levels | `GET /api/zones` |
| forecast.html | risk score/level/trend + components per zone | `GET /api/risk/{grid}` |
| actions.html | priority, recommended actions, checklist, rule trace | `GET /api/prevention/{grid}` |
| alerts.html | current level + public advisory | `GET /api/risk` + `/api/zones/{grid}` |
| routes.html | routing status | via zone payload (`UNAVAILABLE`) |
| why.html | vulnerability score/level/factors/proxy | `GET /api/vulnerability/{grid}` |
| history.html | the 5 verified flood events | `GET /api/history/events` (added) |
| any | citizen reporting | `POST /api/reports`, `GET /api/reports` |

## Files modified / created

- **Created**: `frontend/js/api.js` (API_BASE + getHealth/getZones/getZone/
  getRisk/getVulnerability/getPrevention/getEnvironment/submitReport/
  getReports/getHistoryEvents), `frontend/js/pages.js` (per-page binding
  keyed off `body[data-page]`, loading/offline/empty states).
- **Modified**: all 8 HTML pages (script tags + honest footers),
  `live-map.html` (static fabricated feed rows removed), `js/main.js`
  (fabricated `initFeed()` deleted), `src/delivery/api.py` (CORS for
  localhost:8080/5500 + GET /api/history/events).

## Fabricated data removed

- `initFeed()` fake sensor/advisory messages (main.js) — deleted.
- Static fake feed rows in live-map.html ("Rain cell tracked SW of
  Katraj", "Kharadi underpass sensor flagged ponding") — deleted.
- Fake gauges (Khadakwasla release stage etc.) replaced by real CWC
  availability per zone.
- index.html simulated stats replaced by real backend stats.
- Footer "Data simulated" → "FloodGuard AI backend · HISTORICAL REPLAY demo".

Every page now shows: *Loading …* → real data, or *"Unable to connect to
FloodGuard backend."*, or *"No data available."* — never a silent mock.

## Replay disclosure

Wherever Module-2 data is shown, a badge reads:
**HISTORICAL REPLAY / DEMO — not a live flood warning**.
Vulnerability sections use the term **Hydrologic Vulnerability Proxy**
for the XGBoost score; never "flood probability".

## Testing performed

- Backend: health/CORS/preflight verified with curl-style requests
  (`Access-Control-Allow-Origin: http://localhost:8080`, POST preflight OK).
- Frontend served via `python -m http.server 8080 --directory frontend`
  — all pages/scripts return 200; `node --check` passes on api.js,
  pages.js, main.js.
- Full regression after integration: **Module 1 ✅ Module 2 13/13 ✅
  Module 3 15/15 ✅ Module 4 12/12 ✅ Module 5 15/15 ✅ = 55/55**.
- Secret scan of html/js/css: no webhook URLs, keys, tokens or passwords.

## Remaining issues

1. Browser-level click-through must be done by a human (no headless
   browser in this environment); all underlying calls are tested via API.
2. Forecast page's old 7-day-outlook chart is marked UNAVAILABLE — the
   backend has no forecast endpoint (by design this phase).
3. Safe-route stays UNAVAILABLE pending road-network data.

---

## INPUT → PREDICTION → OUTPUT WIRING (final pass)

Shared frontend config: FG_DATASET (DATE_MIN 2015-01-01, DATE_MAX 2025-12-31,
DEFAULT_DATE 2024-07-15) + loadGrids() fetching zone list from GET /zones
(static fallback only if backend unreachable).

| Page | Inputs | Wired calls | Output behaviour |
| :--- | :--- | :--- | :--- |
| index | none | /zones | stat cards: total zones, high/critical counts, avg risk, active alerts, replay date |
| live-map | click dots | /zones + /zones/{id} | real-level dots, per-zone detail panel (risk/vuln/heat/water), CWC availability gauges |
| forecast (Zone Risk) | zone select + DATE PICKER (min/max enforced) | /risk/{id} + /zones/{id} + /prevention/{id}?citizen_reports=N + /environment/{id}?date | gauge bars for weighted components, trend-null text ("Insufficient history…"), G002 CWC UNAVAILABLE note, prevention panel with rule trace, environment cards incl. telemetry-UNAVAILABLE rows |
| why | zone select | /vulnerability/{id} | index score/factors + proxy score + visible disclosure (rule ≤700 m ∧ elev<p35; not flood probability) |
| actions | zone select + DATE PICKER | /reports?grid_id then /prevention/{id}?citizen_reports=count | citizen-count chaining makes ≥1/≥4 escalation rules visibly fire |
| history | event buttons | /history/events → handoff | "Open in Zone Risk" jumps to forecast page preloaded with that date+zone |
| alerts | login forms | auth/* + alerts/* | genuinely separate PUBLIC vs MUNICIPAL renders |

Backend change: aggregator now also returns 	riggered_rules inside
prevention payload (additive; enables on-screen rule traceability).
Verified via API: PUNE_G004/2024-07-15 → risk 79.22 HIGH INCREASING;
citizen_reports=5 triggers CITIZEN_REPORTS_CLUSTER_ESCALATE + URGENT.

---

## LIVE MAP v2 (demo polish)

- Exactly 4 zone markers (one per IMD cell), enlarged halos/cores,
  tagged with data-grid for JS binding; decorative extra dots removed.
- Labels show PLACE NAMES (West-Central / East / North-West / North-East)
  instead of grid IDs. River names (Mula/Mutha/Indrayani) kept as
  geographic context.
- Click a dot -> structured detail panel rendered directly BELOW the map:
  dynamic risk (score/level/trend), vulnerability index + factors,
  environment heat/water, CWC river level, prevention priority/actions,
  and an [ANALYZE THIS ZONE] jump into the analysis workflow.
- River & street gauges panel now shows REAL per-zone CWC telemetry
  (level mean/max in metres, station count) via the additive iver
  object in the zone payload. G002 has no station -> UNAVAILABLE;
  pre-Feb-2022 dates also unavailable. Never estimated.
- Sensor feed restructured: place name + level pill + score/trend/vuln +
  replay date, with an explicit no-live-sensors note.
