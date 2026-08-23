# LIVE RISK REPORT — Module 2 (Zone Risk Engine, Historical Replay)

Date: 2026-08-22 · Config: `src/risk/live_risk_config.json` v1

## What this is

A **zone risk score** (0–100) per Pune grid combining real temporal
signals, the frozen ML anomaly layer, and Module-1 vulnerability.
Every output is labelled **"HISTORICAL REPLAY / DEMO"** — no live feed
is connected. It is **NOT** a flood probability and NOT an official
warning. No LSTM/XGBoost was trained; no labels were fabricated.

## Risk methodology

```
risk_score = 0.45 · ml_anomaly        (frozen IsolationForest, frozen CSV)
           + 0.30 · temporal_intensity (rainfall_7d expanding percentile
                                        within the same grid — leak-safe)
           + 0.25 · vulnerability      (Module 1 Transparent Index)
```

Weights are expert-configured, published in `live_risk_config.json`
with per-component rationale — the same transparent pattern as Module 1.
The design follows the fallback documented in `MODULE_2_LIVE_RISK.md`
(temporal risk index + frozen IF baseline), not a new invented scheme.

Levels: LOW <40 ≤ MODERATE <60 ≤ HIGH <80 ≤ CRITICAL (presentation bands).
Warm-up note: first 6 days/grid have incomplete 7-day windows; they are
ranked as zero intensity (24 of 16,072 rows — documented approximation).

## Trend methodology (no future values)

`delta = mean(risk[t−2..t]) − mean(risk[t−5..t−3])` per grid:
≥ +10 → STRONGLY_INCREASING · ≥ +3 → INCREASING · > −3 → STABLE ·
else DECREASING. Undefined until both windows exist (20 rows at series
start — reported as `null`, never back-filled).

## Example results (2024-07-15, monsoon episode)

| Grid | risk | level | trend | anomaly | vulnerability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| G001 | 83.19 | CRITICAL | — see CSV | 90 | 44.7 |
| G002 | 75.63 | HIGH | — | 79 | 41.1 |
| G003 | 92.22 | CRITICAL | — | 97 | 80.6 |
| G004 | 79.22 | HIGH | INCREASING | 85 | 53.8 |

(Spec example `2024-07-15 / PUNE_G004` → score 79.22, HIGH, INCREASING,
river-level honestly marked unavailable for that date.)

## Validation results (`tests/test_live_risk.py`)

10/10 groups PASS covering all 12 required checks: all grids work;
invalid inputs rejected; scores bounded across 16,072 rows; levels/trends
valid; vulnerability matches Module 1 exactly (0 diff); anomaly matches
frozen ML exactly (0 diff); replay deterministic (frame-equal recompute);
CWC absence honest (G002 permanently flagged); dataset sha256 unchanged
(`9886dee098f11f8f`); flood labels never used as input nor fabricated.

## Output artifacts

- `outputs/risk/historical_risk_scores.csv` — full 16,072-row table
- `outputs/risk/latest_zone_risk.json` — latest-day snapshot per zone (replay-labelled)
- `outputs/risk/risk_trend_summary.csv` — latest trend per zone
- Contract: `src/risk/live_risk.py::get_live_risk(date, grid_id)`

## Data limitations

1. No live weather feed → historical replay only (clearly labelled).
2. CWC river levels: ~17% of rows, absent for PUNE_G002 entirely.
3. IMD native resolution ~27 km bounds "zone" granularity.
4. Weights are expert-configured (documented), not calibrated against
   outcomes — impossible with 5 verified events.

## Future LSTM upgrade path

The anomaly component is a swappable slot: any temporal model producing
a 0–100 signal per (date × grid) can replace it via config weights —
without touching Modules 1/3/4/5 or ViaSocket. Candidate: self-supervised
rainfall sequence model (defensible without flood labels), feeding its
forecast-derived signal into this same engine.
