## 0. DEBUG: "stuck on Loading" root cause & fix

**Symptom:** analyze page stayed on "Loading…" after clicking ANALYZE RISK.

**Diagnosis (read-only first):**
1. Direct `POST /api/risk/analyze` → HTTP 200 with correct JSON ⇒ backend OK.
2. Browser-exact sequence re-tested (OPTIONS preflight + POST from origin
   `http://localhost:8080`) → preflight 200, POST 200 ⇒ CORS OK.
3. Field-by-field contract check in node against the real response found:
   `environment.data_status` was **missing** from the payload.

**Root cause 1:** `renderAnalysis()` accessed
`env.data_status.temperature_telemetry`; since the aggregator's
`environment` block had no `data_status` key, this threw a TypeError that
escaped the fetch-only try/catch → unhandled rejection → innerHTML never
set → permanent loading state.

**Fixes applied (1):**
1. Backend (`aggregator.py`): environment block now always includes
   `data_status` sourced from Module 4's config (with safe fallback).
2. Frontend (`pages.js runAnalysis`): rendering wrapped in its own
   try/catch; any render failure now renders a visible
   **"RISK ANALYSIS FAILED"** card with the error message and logs to
   console — loading can never stick permanently.

## 0b. DEBUG round 2: ReferenceError "r is not defined"

**Symptom after fix 1:** page showed "RISK ANALYSIS FAILED … rendering
failed: r is not defined" (visible error state working as designed).

**Root cause (exact):** inside `renderAnalysis()` in
`frontend/js/pages.js`, the DYNAMIC RISK card's Trend row referenced
`r.risk.trend` — `r` was a leftover variable name from the fetch call in
an earlier draft; it does not exist in this function's scope.
Exact line fixed: the Trend row of the Dynamic Risk card →

```
- esc(r.risk.trend || "Insufficient history for trend (warm-up period)")
+ esc(j.risk.trend || "Insufficient history for trend (warm-up period)")
```

(`j` is renderAnalysis' own parameter holding the POST /api/risk/analyze
response.)

Full function audit performed afterwards: every remaining reference uses
`j.*`, plus locally scoped `prev` / `env` / `ds` objects. No other stray
short identifiers exist.

**Verification (executed, not inspected):**
1. `node scripts/render_smoke_test.js` — extracts the REAL
   `renderAnalysis()` source and runs it in a sandbox against LIVE backend
   responses: PUNE_G004 + PUNE_G001 × PUBLIC/MUNICIPAL roles → **4/4 PASS,
   all sections present, zero exceptions**.
2. Error cases re-run → **5/5 PASS**.
3. Full regression → **55/55 core + dual-alerts 13/13 + independence +
   XGBoost gate ALL PASS**.

---

## 1. New / modified endpoints

| Endpoint | Change |
|---|---|
| `POST /api/risk/analyze` | **NEW** — central workflow: `{grid_id, date, time?}` → combined Module 1–4 result. Validates zone (400), date format (400), time HH:MM (400); out-of-range dates return HTTP 200 `{status:"UNAVAILABLE", reason, data_range}` per contract. Time is echoed but does not change computation (dataset is daily — documented in response). |
| aggregator prevention payload | additive `triggered_rules[]` (rule_id/condition/action/explanation) for on-screen traceability |

No other backend changes. No retraining, no new ML, no fabricated data.

## 2–7. Frontend pages modified & module outputs

- **NEW `analyze.html`** + `pageAnalyze()` in pages.js:
  - Inputs: zone select (populated from `GET /zones` via loadGrids),
    date picker (min 2015-01-01 / max 2025-12-31, default 2024-07-15),
    time input (default 14:00).
  - Buttons: `ANALYZE RISK` (POST /api/risk/analyze) and
    `LOAD DEMO SCENARIO` (fills G004/2024-07-15/14:00 then submits — still
    calls the API; nothing hardcoded in results).
  - Renders, in order: RISK ASSESSMENT summary card → VULNERABILITY
    (score/level/model/target/disclosure + ranked factors) → DYNAMIC RISK
    (score/level/trend + weighted component bars 45/30/25) → WHY IS THE
    RISK HIGH? (server-composed from actual values) → RECOMMENDED ACTIONS
    (priority/actions/checklist/rule trace) → ENVIRONMENTAL CONDITIONS
    (heat/water + telemetry UNAVAILABLE lines) → public simplified block.
- **index.html**: prominent `CHECK RISK` button on hero → analyze.html.
- **live-map.html**: zone dots now clickable → detail panel gains
  `ANALYZE THIS ZONE` button → jumps to analyze.html preloaded with that
  zone/date via localStorage handoff.
- **history.html**: each verified event has `Open in Zone Risk`.
- All nav bars gained an "Analyze Risk" link.

## 8–9. Public vs Municipal

Same underlying analysis (`POST /analyze`); rendering differs:
- PUBLIC/guest: simplified "WHAT THIS MEANS FOR YOU" block with the
  level-based advisory and a pointer to sign in for operations.
- MUNICIPAL: full operational view — components breakdown, vulnerability,
  priority, actions/checklist, environment, citizen-report counts,
  metadata. Backend remains source of truth; frontend renders only.

## 10–12. Map interaction / citizen reports / ViaSocket

Map click → details incl. ANALYZE THIS ZONE ✓ · Reports feed Module 3's
citizen escalation (count passed to `/prevention`) ✓ · ViaSocket event
endpoint unchanged and verified ✓ (no frontend ViaSocket access).

## 13. Tests

Regression after implementation: Module 1 ✅ · Module 2 13/13 ✅ ·
Module 3 15/15 ✅ · Module 4 12/12 ✅ · Module 5 15/15 ✅ · Dual-alerts
13/13 ✅ · XGBoost-pipeline gate ✅ → **55/55 core + extras PASS**.
API checks: known example returns exactly 79.22/HIGH/INCREASING;
bad zone → 400; time 99:99 → 400; missing time → defaults 14:00;
date 2030 → status UNAVAILABLE with covered range.

## 14. Remaining limitations

Dataset is daily (time recorded, not computable) · replay-only until a
weather feed exists · heat/water remain proxies pending telemetry · safe
routes pending road network · email receipt confirmation still requires
the recipient inbox check.

## Files

New: `frontend/analyze.html`. Modified: `js/api.js` (analyzeRisk +
FG_DATASET/loadGrids), `js/pages.js` (pageAnalyze, dynamic grids, date
pickers, weighted bars, null-trend text, env panel, map analyze jump),
8 HTML nav bars, index hero button, live-map detail panel,
`src/delivery/aggregator.py` (triggered_rules), `src/delivery/api.py`
(analyze endpoint). Docs updated:
`docs/FRONTEND_BACKEND_INTEGRATION.md`.

## 13b. DEBUG-phase error-case results (live backend)

| Case | Result |
|---|---|
| invalid zone PUNE_G999 | HTTP 400 ✓ |
| date 2030-01-01 | HTTP 200 + status UNAVAILABLE + reason ✓ |
| time 99:99 | HTTP 400 ✓ |
| missing time | defaults to 14:00 ✓ |
| unparseable date | HTTP 400 ✓ |
| backend stopped (simulated earlier) | frontend shows BACKEND OFFLINE / offline panel; never stuck on loading ✓ |

E2E render contract script: scripts/e2e_analyze_check.js (10/10 PASS).
Error cases: scripts/e2e_analyze_errors.js (5/5 PASS).
