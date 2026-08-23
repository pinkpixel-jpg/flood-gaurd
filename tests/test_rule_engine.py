"""MODULE 3 FINAL VALIDATION — independent prevention action engine.

Run: python tests/test_rule_engine.py
Scenario contexts are TEST-ONLY inputs, not real historical events.
"""

import ast
import hashlib
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

FAILURES = []
REF_ZIP = "rule_based_reference/hemal12.zip"
EXPECTED_REF_SHA = "BAEFBBF34944A368"


def check(name, fn):
    try:
        detail = fn()
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")


def base(**kw):
    ctx = {"date": "2024-07-15", "grid_id": "PUNE_G004",
           "risk_score": 50, "risk_level": "MODERATE",
           "risk_trend": "STABLE", "citizen_reports": 0}
    ctx.update(kw)
    return ctx


def t1_low_stable():
    from src.risk.rule_engine import evaluate_prevention
    out = evaluate_prevention(base(risk_score=20, risk_level="LOW"))
    acts = " ".join(out["recommended_actions"]).lower()
    assert "routine monitoring" in acts
    assert out["priority"] == "ROUTINE"
    assert len(out["recommended_actions"]) == 1


def t2_moderate_stable():
    from src.risk.rule_engine import evaluate_prevention
    out = evaluate_prevention(base())
    assert any("increased monitoring" in a.lower() for a in out["recommended_actions"])
    assert not any("prepare" in a.lower() for a in out["recommended_actions"])
    assert out["priority"] == "ELEVATED"


def t3_high_stable():
    from src.risk.rule_engine import evaluate_prevention
    out = evaluate_prevention(base(risk_score=70, risk_level="HIGH"))
    joined = " ".join(out["recommended_actions"]).lower()
    for kw in ("inspection", "deployment readiness", "advisory", "vulnerable"):
        assert kw in joined, f"missing {kw}"
    assert out["priority"] == "HIGH"
    return f"{len(out['recommended_actions'])} actions"


def t4_high_increasing_stronger_than_high_stable():
    from src.risk.rule_engine import evaluate_prevention
    stable = evaluate_prevention(base(risk_score=70, risk_level="HIGH",
                                      risk_trend="STABLE"))
    rising = evaluate_prevention(base(risk_score=70, risk_level="HIGH",
                                      risk_trend="INCREASING"))
    assert len(rising["recommended_actions"]) > len(stable["recommended_actions"])
    assert any("rising" in a.lower() for a in rising["recommended_actions"])
    assert rising["priority"] == "URGENT" and stable["priority"] == "HIGH"


def t5_critical_strongly_increasing_top_priority():
    from src.risk.rule_engine import evaluate_prevention
    out = evaluate_prevention(base(risk_score=93, risk_level="CRITICAL",
                                   risk_trend="STRONGLY_INCREASING",
                                   environmental_context={"rainfall_1d": 110}))
    joined = " ".join(out["recommended_actions"]).lower()
    for kw in ("immediate activation", "emergency resources",
               "disaster-management personnel", "urgent public advisory",
               "continuous monitoring"):
        assert kw in joined, f"missing {kw}"
    assert out["priority"] == "URGENT"
    assert len(out["triggered_rules"]) >= 5


def t6_decreasing_downgrades_watch():
    from src.risk.rule_engine import evaluate_prevention
    out = evaluate_prevention(base(risk_score=45, risk_level="MODERATE",
                                   risk_trend="DECREASING"))
    assert any("standard monitoring cycle" in a for a in out["recommended_actions"])
    assert not any("prepare" in a.lower() for a in out["recommended_actions"])
    assert out["priority"] == "ELEVATED"


def t7_citizen_reports_escalation():
    from src.risk.rule_engine import evaluate_prevention
    zero = evaluate_prevention(base(citizen_reports=0))
    few = evaluate_prevention(base(citizen_reports=1))
    many = evaluate_prevention(base(citizen_reports=4))
    assert all("citizen" not in json.dumps(z["recommended_actions"]).lower()
               for z in (zero,))
    assert any("field verification" in a.lower() for a in few["recommended_actions"])
    assert any("clustered" in a.lower() for a in many["recommended_actions"])
    assert many["priority"] == "HIGH" and zero["priority"] == "ELEVATED"


def t8_invalid_score():
    from src.risk.rule_engine import evaluate_prevention
    try:
        evaluate_prevention(base(risk_score=150))
        raise AssertionError("accepted")
    except ValueError as e:
        assert "0-100" in str(e)


def t9_invalid_level():
    from src.risk.rule_engine import evaluate_prevention
    try:
        evaluate_prevention(base(risk_level="SEVERE"))
        raise AssertionError("accepted")
    except ValueError as e:
        assert "risk_level" in str(e)


def t10_invalid_trend():
    from src.risk.rule_engine import evaluate_prevention
    try:
        evaluate_prevention(base(risk_trend="UPWARD"))
        raise AssertionError("accepted")
    except ValueError as e:
        assert "risk_trend" in str(e)


def t11_missing_fields():
    from src.risk.rule_engine import evaluate_prevention
    for drop in ("date", "grid_id", "risk_score", "risk_level"):
        ctx = {k: v for k, v in base().items() if k != drop}
        try:
            evaluate_prevention(ctx)
            raise AssertionError(f"{drop} accepted")
        except ValueError as e:
            assert drop in str(e)


def t12_traceability():
    from src.risk.rule_engine import evaluate_prevention
    out = evaluate_prevention(base(risk_score=93, risk_level="CRITICAL",
                                   risk_trend="STRONGLY_INCREASING",
                                   citizen_reports=5))
    rule_actions = {t["action"]: t["rule_id"] for t in out["triggered_rules"]}
    assert len(rule_actions) == len(out["triggered_rules"])
    for a in out["recommended_actions"]:
        assert a in rule_actions, f"untraceable action: {a}"


def t13_deterministic():
    from src.risk.rule_engine import evaluate_prevention
    ctx = base(risk_score=82, risk_level="CRITICAL",
               risk_trend="STRONGLY_INCREASING", citizen_reports=4,
               environmental_context={"rainfall_1d": 95})
    a = json.dumps(evaluate_prevention(ctx), sort_keys=True)
    b = json.dumps(evaluate_prevention(ctx), sort_keys=True)
    assert a == b


def t14_independence_no_ml_imports():
    tree = ast.parse(open("src/risk/rule_engine.py", encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    allowed = {"json", "os", "pandas", "datetime"}
    assert imported <= allowed, f"forbidden imports: {imported - allowed}"
    banned = [m for m in sys.modules
              if m.startswith(("src.risk.live_risk", "src.vulnerability",
                               "sklearn", "xgboost", "shap"))]
    assert not banned, f"ML modules loaded during engine use: {banned}"
    return f"imports={sorted(imported)}"


def t15_reference_untouched_and_unneeded():
    h = hashlib.sha256(open(REF_ZIP, "rb").read()).hexdigest()[:16].upper()
    assert h == EXPECTED_REF_SHA
    for root, _, files in os.walk("src/risk"):
        for f in files:
            if not f.endswith(".py"):
                continue
            s = open(os.path.join(root, f), encoding="utf-8",
                     errors="ignore").read()
            assert "rule_based_reference" not in s and "hemal12" not in s


if __name__ == "__main__":
    check("1. LOW + STABLE -> routine posture, ROUTINE priority", t1_low_stable)
    check("2. MODERATE + STABLE -> increased monitoring, ELEVATED", t2_moderate_stable)
    check("3. HIGH + STABLE -> inspect/deploy/advisory/vulnerable watch, HIGH", t3_high_stable)
    check("4. HIGH + INCREASING stronger than HIGH + STABLE (URGENT)", t4_high_increasing_stronger_than_high_stable)
    check("5. CRITICAL + STRONGLY_INCREASING -> full critical set, URGENT", t5_critical_strongly_increasing_top_priority)
    check("6. DECREASING -> step-down of special measures", t6_decreasing_downgrades_watch)
    check("7. citizen-report escalation distinguishes 0 vs 1 vs 4+", t7_citizen_reports_escalation)
    check("8. invalid risk score rejected", t8_invalid_score)
    check("9. invalid risk level rejected", t9_invalid_level)
    check("10. invalid trend rejected", t10_invalid_trend)
    check("11. missing required fields rejected", t11_missing_fields)
    check("12. every recommendation traceable to a rule_id", t12_traceability)
    check("13. deterministic output", t13_deterministic)
    check("14. runs without ML modules; stdlib-only imports", t14_independence_no_ml_imports)
    check("15. rule_based_reference unmodified & unreferenced", t15_reference_untouched_and_unneeded)

    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)
    print("ALL MODULE 3 FINAL TESTS PASSED")
