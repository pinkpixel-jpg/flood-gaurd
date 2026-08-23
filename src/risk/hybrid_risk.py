"""HYBRID RISK INTERFACE — OPTIONAL FUTURE WORK, STUB ONLY.

The project runs as TWO INDEPENDENT SYSTEMS:
  SYSTEM 1: ML anomaly engine (src/ml/, src/risk/ml_adapter)
  SYSTEM 2: Rule-based engine (src/risk/rule_engine, teammate)

Merging them is OPTIONAL and NOT required for either system to function.
This stub defines how a future merge WOULD connect; nothing in either
system requires this module.

See docs/RISK_ENGINE_CONTRACT.md and docs/RISK_ENGINE_ARCHITECTURE.md.
"""

from src.risk.rule_engine import validate_rule_output as _validate_rule

ML_RESULT_FIELDS = {"date", "grid_id", "ml_anomaly_score", "anomaly_percentile"}


def validate_ml_result(ml_result):
    missing = ML_RESULT_FIELDS - set(ml_result or {})
    if missing:
        raise ValueError(f"invalid ML result; missing fields: {sorted(missing)}")
    s = ml_result["ml_anomaly_score"]
    if not (0.0 <= float(s) <= 100.0):
        raise ValueError(f"ml_anomaly_score out of range: {s}")


def validate_rule_result(rule_result):
    """Delegate to the rule-engine interface schema (single source of truth)."""
    return _validate_rule(rule_result)


def combine(ml_result, rule_result, weights=None):
    """Future hybrid combination — deliberately UNIMPLEMENTED.

    Will produce:
        {
            "date": ..., "grid_id": ...,
            "ml_anomaly_score": ...,
            "rule_score": ...,
            "final_risk_score": ...,      # TBD after rule engine lands
            "risk_level": ...,            # TBD
            "recommended_actions": [...]  # from rule engine
        }

    `weights` must be supplied by explicit configuration at that time.
    No default weighting exists by design.
    """
    raise NotImplementedError(
        "Hybrid combination is intentionally unimplemented until the "
        "rule engine is merged and a weighting strategy is agreed. "
        "See docs/RISK_ENGINE_CONTRACT.md section 5.")
