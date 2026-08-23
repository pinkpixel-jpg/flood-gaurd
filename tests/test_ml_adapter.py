"""Integration test: ML dataset -> ml_adapter -> valid ML result.

Run:  python tests/test_ml_adapter.py
Uses ONLY existing frozen artifacts; no model is retrained.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from src.risk.ml_adapter import get_ml_result
from src.risk import hybrid_risk


def main():
    scores = pd.read_csv("outputs/ml/anomaly_scores.csv", parse_dates=["Date"])
    probe = scores[(scores["Grid_ID"] == "PUNE_G004") &
                   (scores["Date"] == "2016-07-03")]
    assert len(probe) == 1, "probe row missing from anomaly_scores.csv"
    expected = probe.iloc[0]

    res = get_ml_result("2016-07-03", "PUNE_G004")
    print("adapter output:", res)

    assert set(res) == {"date", "grid_id", "ml_anomaly_score", "anomaly_percentile"}
    assert res["date"] == "2016-07-03"
    assert res["grid_id"] == "PUNE_G004"
    assert abs(res["ml_anomaly_score"] - float(expected["ml_anomaly_score_0_100"])) < 1e-9
    assert res["anomaly_percentile"] == int(expected["anomaly_percentile"])
    assert 0.0 <= res["ml_anomaly_score"] <= 100.0
    assert 0 <= res["anomaly_percentile"] <= 100
    assert isinstance(res["anomaly_percentile"], int)
    print("[PASS] adapter returns contract-conformant result matching frozen CSV")

    res2 = get_ml_result(pd.Timestamp("2016-07-03"), "PUNE_G004")
    assert res2 == res
    print("[PASS] timestamp input accepted")

    for bad_call in [lambda: get_ml_result("2016-07-03", "PUNE_G999"),
                     lambda: get_ml_result("not-a-date", "PUNE_G004"),
                     lambda: get_ml_result("2013-01-01", "PUNE_G004")]:
        try:
            bad_call()
            raise AssertionError("expected error not raised")
        except (ValueError, KeyError):
            pass
    print("[PASS] invalid inputs rejected cleanly")

    ml_res = {"date": "2016-07-03", "grid_id": "PUNE_G004",
              "ml_anomaly_score": 91.74, "anomaly_percentile": 91}
    rule_stub = {"rule_score": 70, "risk_level": "HIGH",
                 "recommended_actions": ["sample action"]}
    try:
        hybrid_risk.validate_ml_result(ml_res)
        hybrid_risk.validate_rule_result(rule_stub)
        hybrid_risk.combine(ml_res, rule_stub)
        raise AssertionError("combine should be NotImplementedError")
    except NotImplementedError:
        pass
    print("[PASS] hybrid interface validates inputs and combination stays unimplemented")

    print()
    print("ALL INTEGRATION TESTS PASSED")


if __name__ == "__main__":
    main()
