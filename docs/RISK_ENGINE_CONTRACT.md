# RISK ENGINE CONTRACT — Pune FloodShield

Status: ML side FROZEN & INTEGRATED via adapter. Rule engine NOT merged.
This document is the single source of truth for all interfaces.

## 0. Architecture

```
   data/processed/pune_ml_dataset.csv      (frozen, 16,072 rows)
                 |
          ML ENGINE (FROZEN)
          IsolationForest 300/.01/seed42
                 |
        outputs/ml/anomaly_scores.csv
                 |
        src/risk/ml_adapter.py   get_ml_result(date, grid_id)
                 |
             ML RESULT ----+
                           +--> HYBRID LAYER (stub) --> final risk
             RULE RESULT --+
                   ^
          RULE ENGINE (teammate, future)
```

## 1. ML INPUT

- File: `outputs/ml/anomaly_scores.csv` (frozen artifact of the trained model)
- Keys: `Date` (2015-01-01..2025-12-31) × `Grid_ID` ∈ {PUNE_G001..PUNE_G004}
- Access ONLY through `src/risk/ml_adapter.py::get_ml_result(date, grid_id)`.

## 2. ML OUTPUT (implemented, frozen)

```json
{
  "date": "YYYY-MM-DD",
  "grid_id": "PUNE_G001 | PUNE_G002 | PUNE_G003 | PUNE_G004",
  "ml_anomaly_score": float 0.0–100.0,
  "anomaly_percentile": int 0–100
}
```

Semantics: higher = MORE anomalous vs learned normal behaviour.
An anomaly/hazard indicator — NOT a flood probability, NOT an official warning.

## 3. RULE ENGINE INPUT (teammate consumes)

The exact ML OUTPUT object above per (date × grid_id).
Optional supporting fields available from `data/processed/pune_ml_dataset.csv`:
rainfall_1d/3d/7d, river_level_daily_max_m, built_up_pct, slope_mean_deg,
distance_to_nearest_waterway_m, drainage_length_m.
Road density does NOT exist (UNKNOWN) — rules must not require it.

## 4. RULE ENGINE OUTPUT (teammate implements)

```json
{
  "date": "...",
  "grid_id": "PUNE_G00x",
  "rule_score": 0–100,
  "risk_level": "LOW | MODERATE | HIGH | CRITICAL",
  "recommended_actions": ["...", "..."]
}
```

Rules must be transparent/config-driven and explainable.

## 5. HYBRID LAYER

- Input: one ML OUTPUT + one RULE OUTPUT for the same date/grid.
- Stub: `src/risk/hybrid_risk.py`
  - `validate_ml_result(...)`, `validate_rule_result(...)` implemented.
  - `combine(...)` intentionally raises NotImplementedError.
- NO weights exist yet (no 60/40 or any other split). Weights will be
  explicit configuration decided only after the rule engine lands.

### HYBRID OUTPUT (future shape — unimplemented values)

```json
{
  "date": "...",
  "grid_id": "PUNE_G00x",
  "ml_anomaly_score": ...,
  "rule_score": ...,
  "final_risk_score": ...,       // TBD
  "risk_level": "...",           // TBD
  "recommended_actions": [...]   // passthrough from rule engine
}
```

## 6. Non-Negotiables

1. Road density stays UNKNOWN; never fabricated.
2. Missing values never silently become zero.
3. Scores reproducible: seed 42, params in `outputs/ml/model_card.json`.
4. All outputs labelled decision-support, never official warnings.
