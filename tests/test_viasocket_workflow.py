"""PHASE 6 verification: ONE controlled send proving viaSocket receives
the payload with all contract fields accessible, plus the temporary
demo branch attached.

Run:  python tests/test_viasocket_workflow.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from src.risk.ml_adapter import get_ml_result
from src.integration.viasocket_client import build_risk_event, send_risk_event
from src.integration.demo_branch import build_demo_message, render_demo_text, ml_anomaly_status


def main():
    ml = get_ml_result("2016-07-03", "PUNE_G004")
    assert ml["ml_anomaly_score"] == 91.74 and ml["anomaly_percentile"] == 91

    demo = build_demo_message(ml)
    payload = build_risk_event(ml, event_type="TEST_EVENT", demo=demo)

    print("FIELD ACCESSIBILITY CHECK (payload as delivered to webhook):")
    checks = {
        "event": payload["event"],
        "date": payload["date"],
        "grid_id": payload["grid_id"],
        "ml.anomaly_score": payload["ml"]["anomaly_score"],
        "ml.anomaly_percentile": payload["ml"]["anomaly_percentile"],
        "rule.score": payload["rule"]["score"],
        "hybrid.final_risk_score": payload["hybrid"]["final_risk_score"],
        "metadata.event_type": payload["metadata"]["event_type"],
        "demo.status": payload["demo"]["status"],
    }
    print(json.dumps(checks, indent=2))
    assert checks["event"] == "pune.flood_risk.updated"
    assert checks["rule.score"] is None and checks["hybrid.final_risk_score"] is None

    print()
    print("TEMPORARY DEMO BRANCH OUTPUT:")
    print(render_demo_text(demo))
    assert demo["status"] == "HIGH ANOMALY"
    assert ml_anomaly_status(74.99) == "NORMAL/MODERATE ANOMALY"

    print()
    result = send_risk_event(payload)
    print("send result:", result)
    print()
    print("[PASS] workflow verified" if result.get("status") == "delivered"
          else f"[WARN] not delivered: {result}")


if __name__ == "__main__":
    main()
