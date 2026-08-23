# MODULE 2 — FINAL REPORT (Live Zone Risk / Historical Replay)

Date: 2026-08-22 · Version v1.1 · Status: COMPLETE & FROZEN for hackathon

## 1. Methodology

```
risk_score = 0.45 * anomaly_score              (frozen IsolationForest)
           + 0.30 * temporal_rainfall_signal   (rainfall_7d expanding
                                                percentile per grid, leak-safe)
           + 0.25 * vulnerability_score        (Module 1 index)
```

Zone risk score 0–100. NOT a flood probability; every artifact carries
the disclaimer. Mode is a strict enum: `HISTORICAL_REPLAY | DEMO` —
with no live feed the engine cannot claim to be live.

**Weights** (explicit, config-driven, rationale in JSON):
anomaly 0.45 / temporal 0.30 / vulnerability 0.25.
Warm-up note: first 6 days/grid ranked as zero intensity (24 rows).

**Risk-level thresholds**: LOW <40 ≤ MODERATE <60 ≤ HIGH <80 ≤ CRITICAL.

**Trend methodology** (no future data): Δ = mean(risk[t−2..t]) −
mean(risk[t−5..t−3]); STRONGLY_INCREASING ≥ +10 > INCREASING ≥ +3 >
STABLE > −3 ≥ DECREASING; undefined → null on 20 warm-up rows.

## 2. Example outputs (2024-07-15)

| Grid | score | level | trend | components (a/t/v) |
| :--- | :--- | :--- | :--- | :--- |
| PUNE_G001 | 83.19 | CRITICAL | see CSV | 90.4 / 96.6 / 44.69 |
| PUNE_G002 | 75.63 | HIGH | — | 79.1 / 92.9 / 41.07 |
| PUNE_G003 | 92.22 | CRITICAL | — | 97.3 / 95.7 / 80.62 |
| PUNE_G004 | 79.22 | HIGH | INCREASING | 85.31 / 91.25 / 53.83 |

`data_status` example: *"IMD daily rainfall OK; CWC river level
UNAVAILABLE for this cell/date (reported as missing, not zero)"*.

## 3. Historical replay status

All 16,072 (date × grid) rows scored and stored in
`outputs/risk/historical_risk_scores.csv`; snapshots in
`latest_zone_risk.json` + `risk_trend_summary.csv`. Replay is
deterministic (frame-equal recompute) and date-range enforced.

## 4. Validation results

`tests/test_live_risk.py` → **13/13 PASS**, covering all required checks:
independent adapter use ✓ · Module-1 join exact ✓ · leak-safety proven by
past-only recomputation on 6 probes ✓ · bounds/levels/trends across all
rows ✓ · deterministic trend ✓ · replay cannot masquerade as live ✓ · CWC
explicitly missing/null ✓ · invalid inputs rejected ✓ · dataset sha
`9886dee098f11f8f` unchanged ✓ · no label fabrication/use ✓ · Module 1
scores intact ✓.

## 5. Data limitations

No live weather feed (replay only); CWC ~17 % coverage and absent for
G002 entirely; ~27 km IMD resolution; weights expert-configured
(documented), uncalibratable with 5 verified events.

## 6. LSTM status

OPTIONAL / NOT BUILT. Full specification added to
`docs/MODULE_2_LIVE_RISK.md`: sequence input (30–90-day windows per
grid), output contract (single 0–100 temporal signal replacing the
anomaly component via config), why optional (no defensible flood labels;
self-supervised rainfall forecasting is the only honest variant), and
what activation would require (framework dependency, chronological
windows, backtesting protocol). The swap requires no changes to any
other module.
