# MODULE 4 — HEAT + WATER ENVIRONMENTAL RISK (FINAL)

Status: **COMPLETE** · Lightweight, transparent, deterministic ·
`src/risk/heat_water.py` + `heat_water_config.json`

## Data honesty (enforced by tests)

| Telemetry | Status |
| :--- | :--- |
| Temperature | **UNAVAILABLE** — no fabricated readings anywhere |
| Reservoir / storage / supply | **UNAVAILABLE** — no fabricated levels anywhere |

Both statuses are embedded in every output via `data_status` and asserted
by tests. The module therefore produces **proxies**, explicitly labelled.

## A. Heat Exposure Proxy (`type = EXPOSURE_PROXY`)

Static per grid, from real ESA WorldCover fractions in the frozen dataset.

```
score = 0.60 · minmax(built_up_pct) + 0.40 · (100 − minmax(vegetation_pct))
levels: LOW <40 ≤ MODERATE <65 ≤ HIGH        (weights sum = 1.0)
```

Direction: more built-up → hotter surface exposure; less vegetation →
hotter. Why a proxy: without temperature observations this measures
*urban surface exposure*, never measured heat. Values are relative
across the four zones (min–max).

## B. Water Deficit Proxy (`type = WATER_DEFICIT_PROXY`)

Temporal per date × grid, from real IMD-derived features only:

```
expected_30d      = 30 × hist_mean_prior_years_mm   (leak-safe baseline)
deficit_ratio     = clamp(1 − rainfall_30d / expected_30d, 0, 1)
water_score       = deficit_ratio × 100
levels: LOW <30 ≤ MODERATE <60 ≤ HIGH
```

HIGH = strong meteorological dry-spell vs the zone's own climatology —
NOT empty reservoirs. Surpluses clamp to 0.

Missing data: all-2015 rows lack a prior-year baseline and early rows
lack complete 30-day windows → score/level returned as **null with an
explanation** (1,460 rows). Never imputed, never zero-filled.

## Example outputs

2024-05-15 / PUNE_G003:
```json
{"heat": {"score": 96.52, "level": "HIGH", "type": "EXPOSURE_PROXY"},
 "water": {"score": 0.0, "level": "LOW", "type": "WATER_DEFICIT_PROXY",
           "explanations": ["rainfall_30d=49.3 mm vs expected 42.7 mm",
                            "at or above climatology (surplus)"]},
 "data_status": {"temperature_telemetry": "UNAVAILABLE",
                 "reservoir_storage_telemetry": "UNAVAILABLE"},
 "mode": "HISTORICAL_REPLAY"}
```
2024-03-01 / PUNE_G001 (dry season): water score **99.59** — severe
meteorological deficit, exactly as the formula predicts.

## Independence

Imports exactly `{json, logging, os, numpy, pandas}`; AST + subprocess
runtime checks confirm no Module 1–3, ML, or ViaSocket code is loaded.
Reads ONLY the frozen dataset.

## Limitations

1. Heat proxy ignores humidity/albedo/land-surface temperature — a true
   heat-risk model needs temperature telemetry.
2. Water proxy is meteorological only — reservoir levels, supply data and
   demand are absent from the project.
3. Relative (min–max) heat scores across just 4 zones.
4. Static heat score repeats across dates (exposure does not vary daily).

## Tests

`tests/test_heat_water.py` → **12/12 PASS** (formula hand-checks, bounds,
levels, determinism, null-handling, telemetry honesty, no-fabrication,
grid/date handling, config validity, independence).
