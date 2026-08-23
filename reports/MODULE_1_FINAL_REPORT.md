# MODULE 1 — FINAL REPORT (XGBoost + SHAP vulnerability mapping)

Date: 2026-08-22 · Status: COMPLETE · Target type: `hydrologic_vulnerability_proxy`

## 1. What was built

A complete, honest XGBoost + SHAP pipeline that distills a **documented
hydrologic vulnerability rule** from real geodata, plus per-zone
explanations and a colour-coded map. The Transparent Vulnerability Index
remains untouched as the label-free fallback.

```
real rasters + OSM lines (OUR verified assets)
   → systematic pixel sampling (stride 8 px ≈ 232 m)
   → features: elevation, slope, TWI(slope-derived), local built-up frac,
               dist_to_drainage_m, dist_to_waterway_m
   → target = hydrologic_vulnerability_proxy:
        (dist_to_drainage ≤ 700 m) AND (elevation < study p35 = 588.0 m)
   → XGBoost 200/4/0.1/0.9/0.9 rs42 (aucpr, scale_pos_weight=86.2,
      hist, n_jobs=1 → deterministic)
   → evaluation: stratified pixel holdout + west/east spatial block
   → SHAP TreeExplainer (global + per-zone)
   → zone score = min-max(flagged-area share across 4 zones) ×100
```

## 2. Data & class distribution (honest)

- Samples: **45,472** (45,675 candidates − 203 nodata drops; 203 raster-
  margin rows outside official bbox excluded at zoning)
- Positives: **518 (1.14 %)** · Negatives: 44,954 — heavily imbalanced;
  metrics reflect agreement with the proxy RULE, not flooding skill.
- Per-zone true proxy-positive shares: G001 0.974 %, G002 2.292 %,
  G003 0.071 %, G004 0.000 %

## 3. Evaluation (two splits, both labelled)

| Split | Accuracy | F1 | Precision | Recall | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| A: stratified random pixel holdout 25 % | 0.9988 | 0.9407 | 0.8987* | 0.9873* | optimistic — spatial autocorrelation between neighbouring pixels |
| B: west-train / east-test spatial block | 0.9994 | 0.9792 | 0.9821* | 0.9763* | harder spatial-generalization check |

\*(values from model card). These numbers measure how well the model
reproduces the DISCLOSED RULE on unseen real geodata. They are NOT flood
prediction accuracy; no such claim is made anywhere.

High scores are expected: the target is a deterministic function of the
same six features (rule distillation), not an independent natural
phenomenon.

## 4. SHAP (genuine TreeExplainer)

Global mean|SHAP|: distance to drainage 7.498 · elevation 3.050 ·
dist to river/stream 1.180 · built-up 0.808 · slope 0.678 · TWI 0.305 —
exactly the two rule variables dominate, confirming faithful distillation.
Per-zone top factors computed for all four grids (`xgboost_zone_explanations.json`).
Summary plot: `outputs/vulnerability/shap_summary.png`.

## 5. Zone results (relative cross-zone index)

| Grid | flagged share % | Score 0–100 | Level |
| :--- | :--- | :--- | :--- |
| PUNE_G001 | 1.008 | **43.60** | MODERATE |
| PUNE_G002 | 2.312 | **100.00** | HIGH |
| PUNE_G003 | 0.086 | **3.72** | LOW |
| PUNE_G004 | 0.000 | **0.00** | LOW |

Score = min–max rescale of flagged-area share across zones (documented);
raw share kept alongside. Model-flagged share matches true rule-positive
share within ~0.05 pp in every zone.

## 6. Artifacts

`xgboost_proxy_model.json` (+card) · `proxy_training_grid.csv(+meta)` ·
`xgboost_vulnerability_scores.csv` · `xgboost_vulnerability_zones.geojson` ·
`xgboost_vulnerability_map.png` · `shap_summary.png` ·
`xgboost_zone_explanations.json`

## 7. Integrity & independence

- Frozen dataset sha256[:16] `9886dee098f11f8f` unchanged ✓
- 5 real historical events untouched ✓
- Reference zip sha256[:16] `BAEFBBF34944A368` unchanged; zero runtime
  dependency (AST/source scans) ✓
- No imports of Module 2/3/ViaSocket ✓
- Flood-label gate still refuses supervised training on 5 events ✓
- Tests: **12/12 PASS** (`tests/test_module1_final.py`) ✓

## 8. Limitations

1. Proxy target = hydrologic rule, NOT real flood outcomes; all metrics
   measure rule reproduction.
2. Pixel autocorrelation inflates Split-A; Split-B partially mitigates.
3. Drainage/waterway distances depend on OSM mapping completeness.
4. Zone scores are RELATIVE across only 4 coarse (~27 km) units.
5. TWI is slope-derived (no flow-accumulation layer).
6. xgboost pinned to 2.0.3 (shap compatibility).

## 9. Upgrade path to true supervised learning

Register genuine labelled inundation records → pass the existing
flood-label gate → retrain with identical scaffolding → SHAP then
explains a REAL-outcome model; proxy model demotes to comparison baseline.
