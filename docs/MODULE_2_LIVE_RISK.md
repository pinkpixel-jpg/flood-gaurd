# MODULE 2 — LIVE RISK PREDICTION (design, not trained)

Status: **DESIGN PHASE. LSTM NOT trained. No flood-classification claims.**

## Question

"What is the current/near-future flood risk for each zone based on
temporal weather/hydrological conditions?"

## Temporal data audit (real numbers from the frozen dataset)

| Item | Value |
| :--- | :--- |
| Rows | 16,072 = 4,018 dates × 4 grids |
| Date span | 2015-01-01 → 2025-12-31, complete daily grid |
| Sequence length possible | up to 4,018 steps/cell (30–90-day windows trivially available) |
| Rainfall features | rainfall_1d/3d/7d/14d/30d, monthly/monsoon accumulations, anomaly — all real |
| CWC river levels | only 2,739 rows (Feb-2022→Dec-2024 ≈17%); G002 has NO station → unusable as a consistent model input across cells |
| Verified positive events | **5 event-days** |

## Verdict

> **Supervised LSTM flood-risk classification is NOT defensible** with
> 5 positive labels. We will not claim an "LSTM flood prediction model".

## Defensible fallbacks (in priority order)

1. **Self-supervised rainfall sequence model (LSTM/GRU if time allows):**
   predict next-day/next-3-day rainfall per cell from past windows.
   Labels are the observed rainfall itself — no fabrication needed,
   thousands of training windows exist. Output feeds the FROZEN
   Isolation-Forest anomaly layer + vulnerability context to express
   *anticipated* anomaly ("rainfall forecaster + anomaly engine"),
   never a flood probability.
2. **Temporal risk index:** current anomaly score + trend (score delta
   over 24–72 h) + accumulation percentiles — fully transparent.
3. **Scenario simulation / historical replay:** already supported
   (HISTORICAL EVENT REPLAY mode) for demo purposes.

The existing frozen Isolation Forest remains the live anomaly engine;
any sequence model would augment inputs, not replace the baseline.

## Honest labelling

Any deployed output is described as:
"anomaly-based risk signal with optional rainfall forecasting" —
never as "LSTM flood prediction".

---

## FINAL IMPLEMENTATION (2026-08-22) — v1.1

Engine: src/risk/live_risk.py · Config: src/risk/live_risk_config.json

`
risk_score = 0.45 * anomaly_score            (frozen IsolationForest)
           + 0.30 * temporal_rainfall_signal (rainfall_7d expanding
                                              percentile, leak-safe)
           + 0.25 * vulnerability_score      (Module 1 index)
`

Levels: LOW <40 <= MODERATE <60 <= HIGH <80 <= CRITICAL.
Trend: delta = mean(risk[t-2..t]) - mean(risk[t-5..t-3]);
STRONGLY_INCREASING >= +10 > INCREASING >= +3 > STABLE > -3 >= DECREASING.

Output contract (final):
{date, grid_id, risk_score, risk_level, risk_trend,
 components:{anomaly_score, temporal_rainfall_signal, vulnerability_score},
 data_status, mode:"HISTORICAL_REPLAY", key_signals*, data_quality*, disclaimer*}
(* additive UI fields)

Mode is an enum ["HISTORICAL_REPLAY","DEMO"]; without a live feed the
engine cannot emit a live claim. CWC absence appears in data_status
and data_quality as explicitly missing — never zero.

## LSTM — OPTIONAL / NOT BUILT (specification for later)

Required sequence input: per (grid_id), windows of T=30..90 days over
[rainfall_1d, rainfall_7d, temporal signal] (+ river levels only where a
station exists; G002 has none -> model must run without them or exclude G002).

Required output contract: a single 0-100 	emporal_prediction_signal
per (date x grid) that can REPLACE the anomaly component via config
weights — no changes to Modules 1/3/4/5 or ViaSocket.

Why optional: supervised flood classification stays indefensible with 5
verified events; a self-supervised RAINFALL forecaster is the only
defensible variant and adds engineering cost with modest demo value.

What it would additionally require: PyTorch/TF dependency decision,
chronological train/val windows (e.g. train 2015-2022, val 2023-2024,
test 2025), backtesting protocol vs climatology baseline, and review
time. Not scheduled for this hackathon unless time explicitly remains.
