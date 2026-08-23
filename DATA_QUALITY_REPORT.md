# Data Quality Report — Pune ML Dataset

Updated: 2026-08-22. Machine-readable validation also saved to
`reports/ml_dataset_validation.txt`.

## 1. Dataset Identity

- File: `data/processed/pune_ml_dataset.csv`
- Structure: ONE ROW = ONE DATE × ONE GRID CELL
- Shape: **16,072 rows × 44 columns**
- Date range: 2015-01-01 → 2025-12-31 (4,018 distinct dates)
- Spatial cells: 4 × 4,018 rows each (complete grid; **0 missing combos**)

## 2. Integrity Checks — ALL PASSED

| Check | Result |
| :--- | :--- |
| Duplicate Date + Grid_ID | 0 |
| Expected 4018×4 combinations present | 16,072/16,072 ✓ |
| Infinite values | 0 |
| Negative rainfall values | 0 |
| CRS consistency (rasters EPSG:4326, vectors reprojected to EPSG:32643 for metric ops) | ✓ |
| Spatial coverage of rasters vs study bbox | exact ✓ |
| Static features constant per cell across time | ✓ |

## 3. Missing Values (intentional & documented)

| Column(s) | % Missing | Reason |
| :--- | :--- | :--- |
| `road_density` | 100 % | Complete Pune road data unavailable (Overpass outage); central-Pune-only data explicitly NOT used. Policy: NaN, never zero. |
| `river_level_*`, `cwc_stations_in_cell` | 83 % | CWC telemetry exists only Feb-2022 → Dec-2024; G002 has no station at all. |
| `monsoon_rainfall_to_date` | 41.4 % | Defined only from Jun 1 each year. |
| `hist_*_prior_years_mm`, `rainfall_anomaly_mm` | 9.1 % | Leak-safe design: first year (2015) has no prior-year statistics. |
| `rainfall_30d / 14d / 7d / 3d` | 0.7 / 0.3 / 0.1 / 0.05 % | Strict rolling windows at series start. |

## 4. Key Value Ranges (sanity)

- `rainfall_1d`: 0 – 129.7 mm/day (max consistent with IMD extreme events in record)
- `elevation_mean_m`: 585–652 per cell (cell min/max span 502–1,137 m) — matches Deccan plateau + Western Ghats gradient
- `slope_mean_deg`: 3.2–7.4 (max pixel slope 57° in hilly G001 west)
- `built_up_pct`: 7.8–25.6 % per cell; urban core G001 highest
- Waterway lengths: 122–363 km mapped lines per cell (Mula/Pawna/Mutha network)
- Drainage length: 4.6 km (G001), 22.6 km (G002), genuinely 0 mapped drains in northern rural cells G003/G004 (OSM coverage fact, logged during extraction)

## 5. Flood Label Availability

- 5 verified historical events, all mapping to PUNE_G004.
- Within rainfall window: 5 positive date-rows out of 16,072 (**0.031 %**).
- Verdict: **INSUFFICIENT for supervised training.** No severity attributes.
  Suitable only for qualitative validation / case-study replay.

## 6. Known Limitations

1. Road density missing (documented blocker, recoverable later via alternate source).
2. CWC coverage partial in time and absent for G002.
3. Flood labels extremely sparse and spatially clustered → unsupervised/
   physics-informed vulnerability scoring recommended over binary classification.
4. OSM waterway/drainage completeness reflects OSM mapping effort; zero-length
   cells are "no mapped feature", not "no real feature".
5. IMD cell resolution is ~27 km — "hyperlocal" is bounded by the native grid.

## 7. Verdict

Dataset integrity: PASS. Feature provenance: fully traceable.
Ready for **exploratory analysis, climatology work, vulnerability-index
construction, and event-replay demos**.
NOT yet claimable as supervised-ML-ready due to label scarcity (#5).
