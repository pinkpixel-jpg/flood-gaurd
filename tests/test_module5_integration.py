"""MODULE 5 FINAL VALIDATION — backend integration / delivery contract.

Run: python tests/test_module5_integration.py
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from fastapi.testclient import TestClient

FAILURES = []
DATASET = "data/processed/pune_ml_dataset.csv"
REPORT_STORE = "data/reports/citizen_reports.csv"


def check(name, fn):
    try:
        detail = fn()
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    except Exception as e:
        FAILURES.append(name)
        print(f"[FAIL] {name}: {e}")


def _client():
    from src.delivery.api import app
    return TestClient(app)


def t1_all_modules_queryable():
    c = _client()
    for ep in ("/api/vulnerability/PUNE_G004", "/api/risk/PUNE_G004",
               "/api/prevention/PUNE_G004", "/api/environment/PUNE_G004"):
        r = c.get(ep)
        assert r.status_code == 200, f"{ep} -> {r.status_code}"
    return "vulnerability / risk / prevention / environment OK"


def t2_normalized_contract():
    c = _client()
    z = c.get("/api/zones/PUNE_G004?date=2024-07-15",
              headers={"X-Role": "MNC"}).json()
    need = {"date", "grid_id", "zone_name", "vulnerability", "risk",
            "prevention", "environment", "citizen_reports", "routing",
            "metadata"}
    assert need <= set(z), f"missing {need - set(z)}"
    assert set(z["risk"]["components"]) == {"anomaly", "temporal_rainfall",
                                            "vulnerability"}
    return f"zone_name={z['zone_name']}"


def t3_bounds():
    c = _client()
    z = c.get("/api/zones/PUNE_G001?date=2024-07-15",
              headers={"X-Role": "MNC"}).json()
    assert 0 <= z["risk"]["score"] <= 100
    assert 0 <= z["vulnerability"]["score"] <= 100
    for sec in ("heat", "water"):
        s = z["environment"][sec]["score"]
        assert s is None or 0 <= s <= 100


def t4_missing_stays_null():
    c = _client()
    z = c.get("/api/zones/PUNE_G002?date=2024-07-15",
              headers={"X-Role": "MNC"}).json()
    # G002 has no CWC station and zero flagged proxy area is possible;
    # routing must be UNAVAILABLE; heat/water present or null — never invented.
    assert z["routing"]["status"] == "UNAVAILABLE"
    for sec in ("heat", "water"):
        v = z["environment"][sec]
        assert v["score"] is None or isinstance(v["score"], (int, float))
    assert z["risk"]["mode"] == "HISTORICAL_REPLAY"


def t5_module1_unchanged():
    sys.path.insert(0, ".")
    from src.vulnerability.vulnerability_index import get_vulnerability_result
    expected = {"PUNE_G001": 44.69, "PUNE_G002": 41.07,
                "PUNE_G003": 80.62, "PUNE_G004": 53.83}
    for g, s in expected.items():
        assert abs(get_vulnerability_result(g)["vulnerability_score"] - s) < 0.01


def t6_module2_unchanged():
    from src.risk.live_risk import get_live_risk
    r = get_live_risk("2024-07-15", "PUNE_G004")
    assert r["risk_score"] == 79.22 and r["mode"] == "HISTORICAL_REPLAY"


def t7_module3_unchanged():
    out = subprocess_rule_engine()
    assert "ALL MODULE 3 FINAL TESTS PASSED" in out


def t8_module4_unchanged():
    out = subprocess_heat_water()
    assert "ALL MODULE 4 TESTS PASSED" in out


def subprocess_rule_engine():
    out = os.popen("python tests/test_rule_engine.py").read()
    return out


def subprocess_heat_water():
    out = os.popen("python tests/test_heat_water.py").read()
    return out


def t9_public_hides_operational_fields():
    c = _client()
    pub = c.get("/api/zones/PUNE_G004").json()
    blob = json.dumps(pub).lower()
    for banned in ("shap", "triggered_rules", "priority",
                   "xgboost", "hydrologic_vulnerability_proxy"):
        assert banned not in blob, f"public leaks {banned}"
    assert "public_alert" in pub


def t10_mnc_contains_detail():
    c = _client()
    z = c.get("/api/zones/PUNE_G004?date=2024-07-15",
              headers={"X-Role": "DISASTER"}).json()
    assert len(z["prevention"]["recommended_actions"]) >= 1
    assert z["prevention"]["checklist"]
    assert z["vulnerability"]["explanations"]
    assert z["citizen_reports"]["count"] == 0
    assert set(z["environment"]["heat"]) >= {"score", "level", "type"}


def t11_citizen_report_validation():
    c = _client()
    ok = c.post("/api/reports", json={
        "grid_id": "PUNE_G003", "report_type": "BLOCKED_DRAIN",
        "description": "integration test drain blockage"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["status"] == "SUBMITTED" and body["report_id"].startswith("CR-")
    bad = c.post("/api/reports", json={
        "grid_id": "PUNE_G999", "report_type": "FLOODING", "description": "x"})
    assert bad.status_code == 400
    lst = c.get("/api/reports?grid_id=PUNE_G003").json()["reports"]
    assert any(r["report_id"] == body["report_id"] for r in lst)
    return body["report_id"]


def t12_route_unavailable():
    c = _client()
    r = c.get("/api/zones/PUNE_G001").json()["routing"]
    assert r["status"] == "UNAVAILABLE" and "road network unavailable" in r["reason"]


def t13_viasocket_payload():
    c = _client()
    ev = c.get("/api/viasocket/event?grid_id=PUNE_G002&date=2024-07-15").json()
    assert ev["event"] == "pune.flood_risk.updated"
    assert set(ev) == {"event", "date", "grid_id", "risk",
                       "prevention", "metadata"}
    assert set(ev["risk"]) == {"score", "level", "trend"}
    assert set(ev["prevention"]) == {"priority", "recommended_actions"}
    assert ev["metadata"]["source"] == "Pune FloodShield"


def t14_no_secrets_exposed():
    c = _client()
    for path in ("/api/health", "/api/zones", "/api/zones/PUNE_G004",
                 "/api/viasocket/event?grid_id=PUNE_G001"):
        blob = json.dumps(c.get(path, ).json()).lower()
        assert "webhook" not in blob and "viassocket_webhook_url" not in blob
        assert "http" not in blob.replace("http://testserver", "")


def t15_deterministic_replay():
    c = _client()
    url = "/api/zones/PUNE_G004?date=2024-07-15"
    a = json.dumps(c.get(url, headers={"X-Role": "MNC"}).json(), sort_keys=True)
    b = json.dumps(c.get(url, headers={"X-Role": "MNC"}).json(), sort_keys=True)
    assert a == b


if __name__ == "__main__":
    check("1. all four modules queryable via API", t1_all_modules_queryable)
    check("2. normalized zone contract valid", t2_normalized_contract)
    check("3. values within bounds", t3_bounds)
    check("4. missing data stays null/UNAVAILABLE", t4_missing_stays_null)
    check("5. Module 1 unchanged", t5_module1_unchanged)
    check("6. Module 2 unchanged", t6_module2_unchanged)
    check("7. Module 3 unchanged (full suite re-run)", t7_module3_unchanged)
    check("8. Module 4 unchanged (full suite re-run)", t8_module4_unchanged)
    check("9. PUBLIC view hides operational fields", t9_public_hides_operational_fields)
    check("10. MNC/DISASTER view contains detailed fields", t10_mnc_contains_detail)
    check("11. citizen report validation + storage + listing", t11_citizen_report_validation)
    check("12. safe-route correctly UNAVAILABLE", t12_route_unavailable)
    check("13. ViaSocket payload contract valid", t13_viasocket_payload)
    check("14. no secrets exposed in responses", t14_no_secrets_exposed)
    check("15. deterministic historical replay", t15_deterministic_replay)

    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)

    h = hashlib.sha256(open(DATASET, "rb").read()).hexdigest()[:16]
    assert h == "9886dee098f11f8f", h
    print("dataset sha256[:16]:", h, "(unchanged)")
    print("ALL MODULE 5 INTEGRATION TESTS PASSED")
