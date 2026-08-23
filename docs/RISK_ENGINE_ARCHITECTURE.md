# RISK ENGINE ARCHITECTURE — Pune FloodShield

Decision of record: the project ships as **TWO INDEPENDENT SYSTEMS**.
Hybrid/merged scoring is OPTIONAL future work and is not required for
the independent systems to function.

## 1. CURRENT ARCHITECTURE (independent systems)

```
                      PUNE DATA
        data/processed/pune_ml_dataset.csv   (frozen, 16,072 rows)
                       |
              +--------+--------+
              |                 |
              v                 v
       ML SYSTEM (ours)   RULE SYSTEM (teammate)
       src/ml/*           src/risk/rule_engine.py
       IsolationForest    explainable thresholds
       frozen: seed 42    (interface stub today)
       300/.01
              |                 |
              v                 v
         ML RESULT          RULE RESULT
         {date,grid_id,     {date,grid_id,
          ml_anomaly_score,  rule_score,
          anomaly_percentile} risk_level,
              |               recommended_actions}
              |                 |
              v                 v
      ViaSocket workflow  ViaSocket workflow
      (ML demo, live)     (separate, future)
```

### Independence guarantees (enforced by tests)

- `src/ml/**` never imports `src/risk/rule_engine.py`.
- `src/risk/rule_engine.py` never imports `src/ml/**` or `ml_adapter`.
- The rule engine can run with ONLY the dataset + its own logic.
- The ML system can run end-to-end without any rule code.
- ViaSocket client is transport-only and serves either system.

## 2. SYSTEM 1 — ML ANOMALY ENGINE (COMPLETE & FROZEN)

| Item | Value |
| :--- | :--- |
| Model | sklearn IsolationForest, n_estimators=300, contamination=0.01, random_state=42 |
| Training / evaluation | 2015–2023 / 2024–2025 (chronological) |
| Features | 24 (rainfall dynamics + static vulnerability + CWC indicator); no flood labels, no road_density |
| Output | `{date, grid_id, ml_anomaly_score 0-100, anomaly_percentile 0-100}` |
| Artifacts | outputs/ml/{anomaly_scores,event_replay,grid_summary}.csv, model_metrics.json, model_card.json |
| Access | `src/risk/ml_adapter.py::get_ml_result(date, grid_id)` |

## 3. SYSTEM 2 — RULE-BASED RISK ENGINE (INTERFACE READY)

Owner: teammate. Current state: interface stub only.

```json
{
  "date": "YYYY-MM-DD",
  "grid_id": "PUNE_G001",
  "rule_score": 0-100,
  "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
  "recommended_actions": ["..."]
}
```

Provided by us (`src/risk/rule_engine.py`): input normalisation/validation
and output-schema validation. NO thresholds, weights or fake scores exist.
The engine must be implementable and runnable entirely without System 1.

## 4. OPTIONAL FUTURE ARCHITECTURE (NOT REQUIRED, NOT BUILT)

```
     ML RESULT  +  RULE RESULT
              |
      OPTIONAL HYBRID LAYER
      src/risk/hybrid_risk.py   (stub; combine() unimplemented;
                                 no weights decided)
              |
           ViaSocket
```

"Hybrid integration is optional future work and is not required for the
independent systems to function."

If attempted later it will require: agreed weighting configuration,
implementation of combine(), payload updates, and a third ViaSocket
workflow. None of that exists today.

## 5. VIASOCKET STRATEGY

Transport stays decision-agnostic:

1. **Live now:** ML result → ViaSocket → ML anomaly-status demo workflow.
2. Later: separate RULE result → ViaSocket → rule demo/workflow.
3. Only if merged: third hybrid workflow.

ViaSocket is never redesigned around a hypothetical hybrid.
