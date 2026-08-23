# FLOODGUARD AI — MASTER PLAN
### Pune FloodShield · Climate-Resilient City Platform
*Compiled from live repository inspection — every fact verified against actual files, APIs, tests, databases and artifacts (dataset sha256[:16] `9886dee098f11f8f` unchanged).*

---

## 1. EXECUTIVE SUMMARY

FloodGuard AI is a working, five-module flood **decision-support platform** for Pune built entirely on real data: 11 years of IMD gridded rainfall (16,072 zone-days), SRTM terrain, ESA WorldCover land cover, OSM hydrology, CWC river telemetry, and 5 verified historical events.

It does not stop at predicting risk: it converts environmental signals into a transparent vulnerability index, a replayable zone-risk score, explainable prevention recommendations, heat/water exposure indicators, and delivers them through role-gated alerts (PUBLIC vs MUNICIPAL) with ViaSocket notification automation. All ML is honestly labelled; where labels are insufficient (5 events), the system uses disclosed proxies instead of pretending.

**Status: all 5 modules COMPLETE · 55/55 module regression tests PASS · webhook delivery HTTP-200-verified.**

---

## 2. PROBLEM

Pune floods suddenly: steep Ghat catchments, confluence rivers (Mula–Mutha), and concrete-hardened basins compress the rain-to-risk window to minutes. Existing dashboards show maps but not *what to do*, hide *why* a zone is at risk, and treat all users identically.

---

## 3. SOLUTION

```
Environmental + Geospatial Data  (IMD · SRTM · WorldCover · OSM · CWC)
        ↓
Vulnerability            (Module 1)
        ↓
Dynamic Zone Risk        (Module 2)
        ↓
Explainable Prevention   (Module 3)
        ↓
Environmental Exposure   (Module 4)
        ↓
Role-Specific Alerts     (Phase 8 dual system)
        ↓
Notification Delivery    (ViaSocket — webhook verified HTTP 200)
```

**Differentiators vs a conventional flood dashboard:** transparent weights instead of black-box scores · proxy/labelling honesty enforced in code and tests · prevention actions traced to named rules · separate PUBLIC/MUNICIPAL alert stores · replay mode that refuses to masquerade as live · missing data rendered as UNAVAILABLE, never zero.

---

## 4. ARCHITECTURE

```
                    FROZEN DATA FOUNDATION
        data/processed/pune_ml_dataset.csv (16,072 rows = 4,018 dates × 4 cells,
        2015-01-01→2025-12-31, sha256[:16]=9886dee098f11f8f)
                        |
   +----------+---------+-----------+------------+
   |          |                     |            |
   v          v                     v            v
 MODULE 1   MODULE 2             MODULE 4    (flood events /
 Vulnerab.  Live Zone Risk       Heat+Water   citizen reports via M5)
 XGBoost+   IF anomaly(0.45) +   exposure &   5 verified events
 SHAP*      rainfall(0.30) +     deficit      only — never fabricated
 Index      vuln(0.25)           proxies
   |          |                     |
   +----> src/delivery/aggregator.py <----+
                        |
                 FastAPI (20 endpoints, src/delivery/api.py)
                        |
        +---------------+----------------+
        v                                v
   Frontend (plain HTML/CSS/JS,     Dual alert DBs
   js/api.js + pages.js,            data/public_alerts.db
   PUBLIC/MNC/DISASTER views)       data/municipal_alerts.db
        |                                |
        +---------------+----------------+
                         v
                      ViaSocket (existing transport, webhook HTTP 200)
```

\* SHAP gated on legitimate labels; proxy model currently active.

Verified package layout: `src/ml` (3 files) · `src/vulnerability` (12 files) · `src/risk` (11 files) · `src/delivery` (6) · `src/alerts` (3) · `src/integration` (2) · `frontend/js` (5: api.js, pages.js added) · `tests` (14 suites) · `scripts` (3 validation scripts).

---

## 5. MODULE 1 — VULNERABILITY

- **Model:** XGBClassifier · xgboost **2.0.3** (pinned for shap compatibility) · persisted `outputs/vulnerability/xgboost_proxy_model.json`
- **Features (6):** elevation_m, slope_deg, twi_proxy, builtup_frac_local, dist_to_drainage_m, dist_to_waterway_m
- **Target:** `hydrologic_vulnerability_proxy` = (dist_to_drainage ≤ 700 m) ∧ (elevation < study p35 = 588 m)
- **Samples:** 45,472 · positives 518 (1.14 %) / negatives 44,954
- **Evaluation:** stratified 25 % holdout seed 42 → Acc 99.86 % · P 90.07 % · R 98.45 % · F1 94.07 % · ROC-AUC 1.0000 · PR-AUC 0.9974; spatial W→E block → Acc 99.94 % · F1 97.92 %
- **SHAP:** genuine TreeExplainer; distance-to-drainage 7.50 › elevation 3.05 › river-distance 1.18 › built-up 0.81 › slope 0.68 › TWI 0.31 — exactly the two rule variables dominate
- **Artifacts:** proxy model+card, training grid CSV/meta, zone scores/GeoJSON/map PNG, shap_summary.png
- **Fallback also live:** Transparent Vulnerability Index (44.69/41.07/80.62/53.83) — untouched
- ⚠️ These are **proxy-rule classification metrics**, NOT real flood prediction accuracy. Verified-flood-label gate still refuses supervised training on the 5 real events.

---

## 6. MODULE 2 — LIVE ZONE RISK

- **Formula (config-driven):** `risk = 0.45·IF-anomaly + 0.30·temporal rainfall signal (rainfall_7d expanding percentile, leak-safe) + 0.25·vulnerability`
- **Levels:** LOW<40≤MODERATE<60≤HIGH<80≤CRITICAL
- **Trend:** Δ=mean(t−2..t)−mean(t−5..t−3); ≥+10 STRONGLY_INCREASING ≥+3 INCREASING >−3 STABLE else DECREASING (null on 20 warm-up rows)
- **16,072 rows scored**, mode enum `HISTORICAL_REPLAY` (cannot claim live), CWC absence explicit (`G002` has no station)
- Contract: `get_live_risk(date,grid_id)` → components{anomaly, temporal_rainfall, vulnerability}
- Example verified: G004 2024-07-15 = 79.22 HIGH INCREASING
- **LSTM:** optional/future; specification documented, nothing trained

*Why a weighted engine:* prevention-grade transparency requires auditable weights; with only 5 verified events no supervised temporal model is defensible.

---

## 7. MODULE 3 — PREVENTION ENGINE

- Deterministic rules — prevention is a decision problem, not a prediction problem
- **16 production rules** in `rule_config.json`: LOW routine · MODERATE monitoring/prepare-if-rising · HIGH ×4 (drainage inspect, deployment readiness, advisory, vulnerable watch) · CRITICAL ×5 (immediate response, emergency resources, notify disaster-mgmt, urgent advisory, continuous monitoring) · trend escalation/step-down ×2 · citizen-report verify ≥1 / cluster ≥4
- Priority ladder ROUTINE<ELEVATED<HIGH<URGENT (+1 rising trend, +1 reports≥4)
- Output contract: priority/actions/triggered_rules/explanations; every action traces to a rule_id
- Imports exactly {datetime,json,os,pandas} — zero ML dependency

---

## 8. MODULE 4 — ENVIRONMENT

- **Heat Exposure Proxy:** `0.60·minmax(built_up_pct)+0.40·(100−minmax(vegetation_pct))`; temperature telemetry UNAVAILABLE → labelled EXPOSURE_PROXY
- **Water Deficit Proxy:** `clamp(1 − rainfall_30d/(30×prior-years-mean),0,1)×100`; reservoir telemetry UNAVAILABLE → meteorological signal only
- Levels LOW<30(MOD<60)≤HIGH; all-2015 rows null+explained (1,460 rows); deterministic; imports {json,logging,os,numpy,pandas}

---

## 9. BACKEND (MODULE 5 / FastAPI)

**20 endpoints verified by AST scan:**
health · zones · zones/{id} · risk/{id} · vulnerability/{id} · prevention/{id} · environment/{id} · history/events · reports GET/POST · viasocket/event GET · auth public/municipal login · auth/me · alerts public+municipal (+history,+preferences)

- Role handling via `X-Role` header on module payloads + Bearer tokens on alert endpoints; backend enforces 401/403 (tested)
- CORS restricted to localhost:8080/5500 origins, GET/POST
- Citizen reports validated (enum types, grid check) → UUID SUBMITTED records
- Replay-only: date-range enforcement prevents live claims

---

## 10. FRONTEND

Plain HTML/CSS/JS preserved (no rebuild): 8 pages connected through single helper `js/api.js` + binder `js/pages.js`. Verified:
- fabricated feed/gauges/stats removed (source scans clean)
- loading/offline/empty states on every page
- HISTORICAL REPLAY badges wherever Module 2 data appears
- routing shows UNAVAILABLE honestly
- secret scan NONE
- served :8080, all resources 200, node --check clean

Flow: page → js/api.js fetch → FastAPI → frozen modules → JSON → existing UI fills.

---

## 11. DUAL ALERT SYSTEM

```
                 SAME DASHBOARD (alerts.html role-aware)
                       |
             +---------+---------+
          PUBLIC               MUNICIPAL
      login citizen/*         login municipal/*
      public_alerts.db       municipal_alerts.db
      (4 alerts, prefs)       (4 alerts, prefs)
             |                   |
             +---------+---------+
                       |
                    ViaSocket
```

PUBLIC payload: level/score/trend/simple explanation/safety recommendation.
MUNICIPAL payload: components/vulnerability/priority/actions/checklist/environment/citizen counts.
Generation reuses frozen Modules verbatim — idempotent per date.

---

## 12. AUTHENTICATION & SECURITY (actual implementation)

PBKDF2-HMAC-SHA256 (120k iters, salted) passwords · opaque bearer tokens stored hashed, 24 h expiry · backend 401 (missing/expired) and 403 (wrong role) enforced by tests · physically separated alert DBs · frontend holds no credentials (scan clean) · ViaSocket URL env-var only, never logged.

Not implemented (stated honestly): rate-limiting, refresh tokens, TLS termination config, production user administration.

---

## 13. VIASOCKET

Existing transport reused (`src/integration/viasocket_client.py`, env-var URL). Verified: two controlled single POSTs → **HTTP 200 delivered** (notification demo + email-template test, timestamps recorded). Email/SMS/WhatsApp execution happens inside the ViaSocket workflow → reported **NOT CONFIRMED RECEIVED / NOT TESTED**; no success claimed beyond webhook acceptance.

---

## 14. TESTING & VALIDATION

| Suite | Result |
|---|---|
| Module 2 live-risk | 13/13 |
| Module 3 rule engine | 15/15 |
| Module 4 heat/water | 12/12 |
| Module 5 integration | 15/15 |
| **Total automated** | **55/55 PASS** |

Plus: Module-1 final suite ✅, dual-alerts 13/13 ✅, independence 6/6 ✅, XGBoost-pipeline 8/8 ✅, read-only ML validation reproduces holdout metrics exactly (ROC-AUC 1.00, PR-AUC 0.9974).

**SYSTEM TEST PASS RATE ≠ MODEL ACCURACY.**

---

## 15. DATA INTEGRITY

Frozen dataset sha `9886dee098f11f8f` unchanged across every phase ✓
Reference zip hash `BAEFBBF34944A368` unchanged ✓
No model retrained since freeze ✓
DB state: users 2 / sessions 37 / 4+4 alerts / 1+1 prefs ✓

---

## 16. CURRENT STATUS

| Component | Status | Evidence | Remaining Work |
|---|---|---|---|
| Data foundation | ✅ COMPLETE | sha-locked dataset, provenance docs | ward-level data later |
| Module 1 | ✅ COMPLETE | index+XGB/SHAP artifacts, 12/12 tests | real labels → true supervised |
| Module 2 | ✅ COMPLETE | 13/13, replay engine | optional LSTM |
| Module 3 | 🟡 COMPLETE (engine) | 15/15; 16 rules live | teammate refines wording |
| Module 4 | 🟡 COMPLETE (proxies) | 12/12; formulas published | temperature/reservoir telemetry |
| Backend | ✅ COMPLETE | 20 endpoints, 15/15 | deploy hardening |
| Frontend | ✅ INTEGRATED | all pages API-fed, scans clean | browser click-through |
| Auth | ✅ COMPLETE | PBKDF2+tokens, 401/403 tested | production user admin |
| Public alerts | ✅ COMPLETE | db+API+UI | notification connectors |
| Municipal alerts | ✅ COMPLETE | db+API+UI | same |
| Alert databases | ✅ COMPLETE | separation test | backups |
| ViaSocket | 🟡 WEBHOOK VERIFIED | HTTP 200 ×2 | email receipt confirmation; SMS/WA |
| Testing | ✅ 55/55 + extras | suites listed | CI wiring |
| Documentation | ✅ COMPLETE | docs/ + reports/ | — |

---

## 17. REMAINING WORK

**P0 (demo-blocking):**
- Confirm demo-email receipt in inbox (ViaSocket-side configuration)
- Human browser click-through of all 8 pages

**P1 (important):**
- Production credentials replacing demo seeds
- Forecast endpoint decision (honest UNAVAILABLE today)
- CI job running the five suites automatically

**P2 (optional/future):**
- Ward-level spatial units
- Road-network acquisition → safe routes
- Citizen-report verification queue → future real labels
- Temperature/reservoir feeds → true heat/storage risk
- Self-supervised rainfall sequence model

---

## 18. DEMO FLOW (4 minutes)

1. Open dashboard (:8080) — real stats load from API
2. Live Map — four zones colour-bound to real risk levels
3. Forecast/Zone-Risk — select PUNE_G004 → 79.22 HIGH INCREASING + components + replay badge
4. Why page — vulnerability factors + proxy disclosure
5. Actions — URGENT priority, 5 recommendations, rule trace expanded
6. Alerts → sign in PUBLIC (citizen/citizen-demo) → simple safety alerts → sign out
7. Sign in MUNICIPAL (municipal/municipal-demo) → SAME dashboard, operational panel
8. Terminal: `python scripts/check_overall_system.py` → READY + 55/55
9. Optional: run Phase-6B script once → webhook 200; explain email pending connector

---

## 19. MENTOR Q&A

- **What problem are you solving?** Converting environmental risk into explainable, role-correct action for Pune.
- **What is unique?** Honest proxies + traceable rules + role-separated delivery, fully reproducible.
- **Why XGBoost?** Small tabular geodata, explainable via SHAP.
- **Why not LSTM?** Only 5 verified events → indefensible as classifier; spec exists if labels grow.
- **Why SHAP?** Tree-model factor attribution; currently gated until legitimate labels exist.
- **Why rule-based prevention?** Actions must be auditable and instantly editable by city staff.
- **Actual ML target?** Disclosed hydrologic rule proxy (dist-drain ≤700 m ∧ elev<p35).
- **What does the accuracy mean?** Agreement with that disclosed rule on held-out pixels.
- **Why so high?** Target is deterministic over included features (rule distillation).
- **Limitations?** 27 km cells, 5 events, no roads/temp/storage telemetry, relative 4-zone scaling.
- **Different from existing systems?** Explainable chain from data→action plus role separation, not just a map.
- **Public vs municipal alerting?** Same dashboard/risk engine; separate DBs and payloads per role.
- **Why two databases?** Clean separation of citizen-facing vs operational records.
- **How does ViaSocket work?** Backend posts signed-off event JSON to configured webhook; channels execute there.
- **Is the system live?** No — replay-only by design until a weather feed exists.
- **Telemetry unavailable?** UI shows UNAVAILABLE/null; never estimated.
- **Unauthorized access?** PBKDF2 passwords, hashed bearer sessions, backend role gates (tested).
- **Future improvements?** Listed in §17 P1/P2.

---

## 20. FINAL PROJECT STORY

**30 seconds:** “FloodGuard AI gives every part of Pune an honest number: how structurally vulnerable it is, what today’s risk is, what to do about it — and explains why. Built entirely on verified data, validated 55/55, delivered role-by-role.”

**1 minute:** add the five-module walkthrough and the refusal-to-fabricate principle: missing roads say UNAVAILABLE, missing temperature says UNAVAILABLE, five flood events stay five.

**3 minutes (technical):** data foundation (16k rows) → Transparent Index + proxy-distilled XGBoost whose SHAP dominance matches the disclosed rule → leak-safe weighted risk engine over the frozen Isolation-Forest anomaly → 16 traceable prevention rules → exposure/deficit proxies → FastAPI with 20 endpoints, PBKDF2 roles, dual SQLite alert stores → plain-JS frontend bound to real APIs → ViaSocket automation verified at HTTP 200.

> **Central story:** “FloodGuard does not stop at predicting risk. It converts risk into explainable action and delivers the right information to the right stakeholder.”

---

## 21. FUTURE SCOPE

Real-label supervised learning (citizen reports as ground truth) · ward-level mapping · LSTM rainfall forecaster · true heat/storage modules · safe routing · municipal SOP integration · multi-city replication using the same contracts.

---

*End of Master Plan — compiled from repository inspection; no code, data or artifacts were modified.*
