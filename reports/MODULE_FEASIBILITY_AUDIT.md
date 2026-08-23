# MODULE FEASIBILITY AUDIT — Pune FloodShield (5-Module Architecture)

Date: 2026-08-22 · Data basis: `data/processed/pune_ml_dataset.csv`
(16,072 rows = 4,018 dates × 4 grids, 2015–2025) + frozen GIS/ML artifacts.

## Headline finding

> **Supervised training is not currently defensible with the available
> verified labels** (5 verified flood event-days, all in PUNE_G004,
> no severity attributes). XGBoost/LSTM *flood classifiers* therefore
> cannot be honestly trained today.

Defensible alternatives exist per module and are specified below.

## Summary Table

| Module | Target Technology | Required Data | Available Data | Feasible? | Label Requirement | Recommended Approach |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 Vulnerability mapping | XGBoost* + SHAP* | Static terrain/land-surface factors + verified damage/flood labels per zone | All static factors ✓; labels: 5 clustered event-days ✗ | **Partial** — index now; XGBoost later | Supervised labels required for XGBoost: NOT met | Transparent weighted Vulnerability Index (explainable); XGBoost+SHAP deferred until real labels exist |
| 2 Live risk prediction | LSTM* | Long continuous multivariate series + event labels for classification | Rainfall dynamics ✓ (16k rows); river levels 17% ✗; labels 5 ✗ | **Partial** — self-supervised rainfall forecasting defensible; flood classification NOT | Flood-classification labels NOT met | LSTM/seq-model on RAINFALL forecasting (self-supervised) → feed predicted rainfall into existing IF anomaly + vulnerability context; or temporal risk index |
| 3 Prevention engine | Rule-based | risk_score, risk_level, trend, vulnerability, conditions | All inputs producible by Modules 1/2 or IF baseline | **Yes** | None (rule-based) | Teammate implements thresholds over defined contract |
| 4 Heat resilience | Formula | Temperature / heatwave records | ✗ NONE (no temperature data anywhere in project) | **Proxy only** — must be labelled as such | None | Urban-Heat-*Exposure Proxy* from built-up %, vegetation %, water % (static, explainable); real heat risk requires IMD/temp data acquisition |
| 4 Water shortage/storage | Formula | Reservoir/storage levels, supply data | ✗ storage: none; rainfall deficit: ✓ | **Proxy only** — meteorological component only | None | Rainfall-deficit / drought-percentile formula from real IMD record; explicitly exclude fake "storage" claims |
| 5 Delivery layer | Dashboard + ViaSocket | Risk outputs + UI + channels | ML results ✓, ViaSocket live ✓, rule engine pending | **Yes** (staged) | None | Interfaces consume contract JSONs; SMS/WhatsApp/safe-route/citizen-reporting are later stages |

\* feasibility not established — see per-module docs.

## Key gaps (real, documented — nothing fabricated)

1. **Flood labels:** 5 event-days, single grid, 2014–2016 vintage, no severity.
2. **Temperature data:** absent → Module 4A limited to exposure proxy.
3. **Water storage/reservoir levels:** absent → Module 4B meteorological-only.
4. **Road network:** central-Pune-only → safe-route feature blocked.
5. **CWC river levels:** only Feb-2022→Dec-2024 and no station in G002.
6. **Live weather feed:** not connected yet (IMD is historical).

## What can honestly be demonstrated at the hackathon

- Vulnerability Index map with transparent factor weights (Module 1 fallback)
- Anomaly-based live/near-real-time risk via frozen Isolation Forest + adapter
- Self-supervised rainfall sequence model (if time) clearly labelled as rainfall forecaster
- Rule-based prevention recommendations driven by defined inputs (Module 3)
- Explainable formulas for heat-exposure & rainfall-deficit proxies (labelled)
- ViaSocket-driven demo notifications across interfaces

## Future work (needs real data)

XGBoost+SHAP vulnerability learning; LSTM flood-risk classification;
true heat risk (temperature); true storage risk (reservoir telemetry);
safe routing (full road network).
