"""INDEPENDENCE TESTS — prove the two systems cannot depend on each other.

Run:  python tests/test_independence.py
No fake rule scores are created; no live webhook calls are made.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FAILURES = []


def check(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")


def t1_ml_adapter_without_rule_engine():
    from src.risk import ml_adapter
    res = ml_adapter.get_ml_result("2016-07-03", "PUNE_G004")
    assert res["ml_anomaly_score"] == 91.74 and res["anomaly_percentile"] == 91
    assert "rule_engine" not in sys.modules


def t2_rule_interface_imports_without_ml():
    assert "src.ml" not in sys.modules
    assert "src.ml.anomaly_model" not in sys.modules
    from src.risk import rule_engine
    d, g = rule_engine.validate_rule_input("2016-07-03", "PUNE_G004")
    assert (d, g) == ("2016-07-03", "PUNE_G004")
    ok = {"date": "2016-07-03", "grid_id": "PUNE_G004", "rule_score": 70,
          "risk_level": "HIGH", "recommended_actions": []}
    assert rule_engine.validate_rule_output(ok) is True
    bad = dict(ok, risk_level="SEVERE")
    try:
        rule_engine.validate_rule_output(bad)
        raise AssertionError("invalid enum accepted")
    except ValueError:
        pass


def t3_ml_sources_do_not_import_rule_engine():
    import glob
    ml_files = glob.glob(os.path.join(ROOT, "src", "ml", "*.py"))
    assert len(ml_files) >= 3
    for p in ml_files:
        src = open(p, encoding="utf-8").read()
        assert "rule_engine" not in src, f"{p} references rule_engine"
        assert "risk" not in [l.split()[0] for l in src.splitlines()
                              if l.startswith("from src.risk")]


def t4_rule_sources_do_not_import_ml():
    p = os.path.join(ROOT, "src", "risk", "rule_engine.py")
    src = open(p, encoding="utf-8").read()
    for banned in ("anomaly_model", "feature_preparation", "ml_adapter",
                   "sklearn", "IsolationForest"):
        assert banned not in src, f"rule_engine.py references {banned}"


def t5_viasocket_client_independent(monkey_results={}):
    from src.integration import viasocket_client as vc
    payload = {"event": "x", "date": "2016-07-03", "grid_id": "PUNE_G004"}
    saved = os.environ.pop(vc.ENV_VAR, None)
    try:
        out = vc.send_risk_event(payload)
        assert out["status"] == "skipped"
    finally:
        if saved:
            os.environ[vc.ENV_VAR] = saved
    src = open(os.path.join(ROOT, "src", "integration", "viasocket_client.py"),
               encoding="utf-8").read()
    assert "rule_engine" not in src and "anomaly_model" not in src


def t6_existing_via_socket_ml_workflow_functional_no_send():
    from src.risk.ml_adapter import get_ml_result
    from src.integration.viasocket_client import build_risk_event
    from src.integration.demo_branch import build_demo_message, ml_anomaly_status

    ml = get_ml_result("2016-07-03", "PUNE_G004")
    payload = build_risk_event(ml, event_type="TEST_EVENT")
    assert payload["ml"]["anomaly_score"] == 91.74
    assert payload["rule"] == {"score": None, "risk_level": None,
                               "recommended_actions": []}
    demo = build_demo_message(ml)
    assert demo["status"] == "HIGH ANOMALY"
    assert ml_anomaly_status(74.99) == "NORMAL/MODERATE ANOMALY"


if __name__ == "__main__":
    check("1. ML adapter works without rule engine", t1_ml_adapter_without_rule_engine)
    check("2. Rule interface imports & validates without ML", t2_rule_interface_imports_without_ml)
    check("3. ML sources never import rule engine", t3_ml_sources_do_not_import_rule_engine)
    check("4. Rule system never imports ML", t4_rule_sources_do_not_import_ml)
    check("5. ViaSocket client independent (no-send skip path)", t5_viasocket_client_independent)
    check("6. Existing ViaSocket ML workflow functional (no live send)", t6_existing_via_socket_ml_workflow_functional_no_send)

    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)
    print("ALL INDEPENDENCE TESTS PASSED — systems 1 & 2 are fully decoupled.")
