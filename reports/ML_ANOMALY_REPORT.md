# ML ANOMALY REPORT — Pune FloodShield

Date: 2026-08-22
Claim: **"ML-based anomaly/hazard detection for hyperlocal flood-risk decision support."**
This is NOT a supervised flood-prediction model, NOT a flood probability, and NOT an official warning.

---

## 1. Objective

Build the first ML intelligence layer: an unsupervised Isolation-Forest anomaly/hazard score per (date × grid cell), learnable from normal historical behaviour and usable later by the teammate's rule engine via `docs/RISK_ENGINE_CONTRACT.md`.

## 2. Dataset

`data/processed/pune_ml_dataset.csv` — 16,072 rows (4,018 dates × 4 cells), 2015-01-01..2025-12-31.
Real IMD rainfall, SRTM terrain, WorldCover land cover, OSM waterways/drainage, CWC river levels (partial). Untouched by this phase.

## 3. Features (24 model inputs)

- **Dynamic (10):** rainfall_1d/3d/7d/14d/30d, rainfall_anomaly_mm, monthly_rainfall_to_date, monsoon_rainfall_to_date, river_level_daily_mean_m, river_level_daily_max_m (+ derived indicator `river_level_available`)
- **Static vulnerability (13):** elevation mean/min/max, slope mean/min/max, built_up_pct, vegetation_pct, water_cover_pct, distance_to_nearest_waterway_m, waterway_length_m, distance_to_nearest_drainage_m, drainage_length_m
- **Excluded:** `flood_event_active` (never an input; asserted at runtime), `road_density` (unavailable → UNKNOWN).

## 4. Preprocessing & missing-value policy

No scaling (tree-based model is monotonic-invariant).
| Missing data | Treatment |
| :--- | :--- |
| monsoon_rainfall_to_date in Jan–May | fill 0 — physically true (0 mm monsoon accumulation before Jun 1) |
| CWC river levels absent | availability indicator + **training-period median**; never 0 (0 m is a real gauge reading) |
| rainfall_anomaly & rolling-edge NaNs | training-period median imputation |

## 5. Temporal split (chronology respected)

| Period | Range |
| :--- | :--- |
| Training | 2015-01-01 → 2023-12-31 |
| Fit subset | training minus event-days ±3 days (**140 rows excluded** so verified events were not used in fitting) |
| Evaluation | 2024-01-01 → 2025-12-31 |

All 5 verified flood events lie in 2015–2016; they are used ONLY for qualitative replay, never as labels or fit rows.

## 6–7. Methodology & parameters

`sklearn.ensemble.IsolationForest`: n_estimators=300, contamination=0.01, max_samples=auto, random_state=42, n_jobs=-1.
Score = −decision_function (higher = more anomalous). Direction TESTED: Spearman(score, rainfall_7d) on evaluation period = **+0.702** (per-grid +0.66…+0.90); top-50 anomalies average 200 mm 7-day rain vs 0 mm for bottom-50.
Normalization: global percentile rank across all 16,072 rows → `ml_anomaly_score_0_100` ∈ [0,100].

## 8. Historical event replay (n=5 — descriptive only)

| Date | Grid | score_0_100 | percentile | global rank | in-grid rank | top10%? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2015-06-23 | G004 | 82.9 | 82 | 2,742 / 16,072 | 792 / 4,018 | – |
| 2015-07-20 | G004 | 56.6 | 56 | 6,984 | 1,981 | – |
| 2016-07-01 | G004 | 51.7 | 51 | 7,767 | 2,165 | – |
| 2016-07-02 | G004 | 71.8 | 71 | 4,532 | 1,301 | – |
| 2016-07-03 | G004 | **91.7** | 91 | **1,328** | **373** | ✔ |
Flag counts: top1% = 0/5, top5% = 0/5, top10% = **1/5**.

**Honest interpretation:** with n=5 no accuracy metric is meaningful. The weak replay alignment has a physical explanation: the recorded events are localised urban-waterlogging logs while IMD cells cover ~27 km — the grid barely sees the local cloudbursts (event-day rainfall was only 0.4–22.9 mm/day on 4 of 5 days). This is documented as a resolution limitation, not hidden.

## 9. Rainfall baseline comparison

Baseline = percentile of `rainfall_7d`. IF vs baseline Spearman on event-days = 0.800; full-record correlation 0.744. On the five events the multivariate score beats the pure-rainfall baseline on the two most intense cases (91.7 vs 83.8; 82.9 vs 87.8 mixed) but neither flags low-rain local events strongly. Conclusion: spatial-vulnerability features add *context*, not magic — presented as decision-support signal only. The baseline is NOT a flood model either.

## 10. Per-grid results (hyperlocal evidence)

| Grid | mean | p95 | days in global top1% | most anomalous date |
| :--- | :--- | :--- | :--- | :--- |
| PUNE_G001 | 52.6 | 96.1 | 60 | 2024-07-26 |
| PUNE_G002 | 43.2 | 91.3 | 15 | 2019-09-26 |
| PUNE_G003 | 49.4 | 95.2 | 48 | 2024-07-26 |
| PUNE_G004 | 54.8 | 95.4 | 39 | 2019-07-28 |

Same-day cross-grid spread confirms the concept, e.g. 2019-09-26: G002 scored 99.9 with 89.6 mm/day while G003/G004 scored ≈95–96 with only ~14.8 mm — identical regional weather, differentiated local hazard picture.

## 11. Limitations

1. Only 5 verified event-days → no statistical validation possible.
2. IMD ~27 km cells under-resolve urban waterlogging triggers.
3. Flood-event records lack severity and precise spatial extent.
4. CWC covers Feb-2022→Dec-2024 only; G002 has no station.
5. Road density unavailable city-wide.
6. Unsupervised scores reflect rarity, not causality.

## 12. Future supervised path

When (and only when) real labelled events accumulate (city disaster logs, satellite inundation mapping), a supervised classifier can reuse this exact feature pipeline with chronological validation. Until then anomaly scoring + rule engine is the defensible design.

## 13. Integration contract

Defined in `docs/RISK_ENGINE_CONTRACT.md`. ML side implemented and emitting:
`{date, grid_id, ml_anomaly_score 0-100, anomaly_percentile 0-100}`.
Rule engine, hybrid weighting, ViaSocket: deliberately NOT built yet.

---

### Reproducibility

Run order: `python -m src.ml.evaluate_anomaly` (calls feature_preparation → anomaly_model).
Artifacts: `outputs/ml/anomaly_scores.csv`, `event_replay.csv`, `grid_summary.csv`, `model_metrics.json`, `model_card.json`, `plots/1..5_*.png`, console log `evaluation_console_output.txt`.
