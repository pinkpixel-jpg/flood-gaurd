# FINAL SYSTEM ARCHITECTURE — PUNE FLOODSHIELD

Climate-Resilient City Platform · 5 modules · honest-labelling policy.

```
                        PUNE FLOODSHIELD
                              |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
 MODULE 1              MODULE 2              MODULE 4
 Vulnerability         Live Risk             Heat + Water
 Mapping               Prediction            Resilience
 XGBoost* + SHAP*      LSTM*                 transparent formulas
        |                     |                     |
        +---------------------+---------------------+
                              |
                              v
                  MODULE 3 Prevention Engine
                       (rule-based, teammate)
                              |
                              v
                      MODULE 5 Delivery Layer
        +---------------------+---------------------+
        |                     |                     |
       MNC                 PUBLIC            DISASTER MGMT
        +---------------------+---------------------+
                              |
                          ViaSocket                    (live ✓)
                              |
                Alerts / Actions / Logging / SMS-WhatsApp*

   * = feasibility gated on data; see reports/MODULE_FEASIBILITY_AUDIT.md
```

## Status legend (honest)

| Component | Status |
| :--- | :--- |
| Data foundation (16,072-row real dataset) | **DONE, frozen** |
| Unsupervised anomaly baseline (Isolation Forest) | **DONE, frozen, live via adapter** |
| ViaSocket transport | **WORKING** (HTTP 200 verified) |
| Module 1 XGBoost+SHAP | \* blocked by labels → Vulnerability Index fallback designed |
| Module 2 LSTM flood classification | \* not defensible (5 events) → self-supervised rainfall forecasting fallback designed |
| Module 3 rules | contract ready; teammate implements |
| Module 4 heat | temperature data missing → exposure proxy only |
| Module 4 water storage | storage data missing → meteorological deficit only |
| Safe route | blocked: no full road network |
| Citizen reporting | schema designed; build pending |

## Guiding principle

Every number shown in the product is either REAL measured data or a
REPRODUCIBLE derivation with a published formula/model card.
Where data is missing we say so — we never fabricate.
