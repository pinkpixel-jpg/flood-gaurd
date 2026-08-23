# MODULE 4 — FINAL REPORT (Heat + Water Environmental Risk)

Date: 2026-08-22 · Status: COMPLETE

## Files created/modified

- Created: `src/risk/heat_water.py`, `src/risk/heat_water_config.json`,
  `tests/test_heat_water.py`, `outputs/risk/environmental_scores.csv`
  (16,072 rows), `docs/MODULE_4_HEAT_WATER.md`, this report.
- Modified: nothing else. Modules 1–3, frozen dataset
  (`9886dee098f11f8f`), ViaSocket and rule_based_reference verified untouched.

## Methodology (transparent proxies — telemetry honesty enforced)

- **Heat Exposure Proxy** (`EXPOSURE_PROXY`, static):
  `0.60·minmax(built_up_pct) + 0.40·(100−minmax(vegetation_pct))`
  from real WorldCover fractions. Relative across the 4 zones.
  Levels LOW<40≤MODERATE<65≤HIGH.
- **Water Deficit Proxy** (`WATER_DEFICIT_PROXY`, temporal):
  `clamp(1 − rainfall_30d/(30×hist_mean_prior_years_mm),0,1)×100`.
  Leak-safe baseline from prior years only; surpluses clamp to 0.
  Levels LOW<30≤MODERATE<60≤HIGH.
- Missing-data policy: 1,460 all-2015 rows → null score + explanation
  (no imputation).

## Real input data used

`built_up_pct`, `vegetation_pct`, `rainfall_30d`,
`hist_mean_prior_years_mm` — nothing else. No temperature, storage,
reservoir or supply values exist in the project and none were invented.

## Example outputs

| Probe | heat | water |
| :--- | :--- | :--- |
| 2024-05-15 / G003 | **96.52 HIGH** | 0.00 LOW (surplus: 49.3 mm vs 42.7 expected) |
| 2024-03-01 / G001 | 44.0 MODERATE* | **99.59 HIGH** (dry-season deficit) |

\*heat is static per zone; date-independent.

## Tests

**12/12 PASS** — formula hand-checks, bounds, level classification,
determinism, null-handling (exactly 1,460 nulls, all 2015), telemetry
status reporting, no fabricated temperature/storage, grid/date handling +
rejections, config validity (weights=1.0, ordered bands), independence
(AST + subprocess runtime scan).
Integrity sweep after implementation: dataset sha unchanged; Module 1
index, Module 2 replay, Module 3 suite all green.

## Limitations

No true temperature model possible without telemetry; meteorological-only
water signal without storage/supply data; relative heat scaling across 4
coarse zones; static exposure repeated per date.

STOP — Module 4 frozen. Not proceeding to Module 5.
