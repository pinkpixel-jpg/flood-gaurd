"""SAFE viaSocket test: builds ONE payload from a REAL frozen ML result.

- Uses the verified observation 2016-07-03 / PUNE_G004 (score 91.74).
- Payload is clearly marked as TEST EVENT in metadata.
- Sends at most ONE request, and ONLY if VIASOCKET_WEBHOOK_URL is set.
- Without configuration it verifies the payload locally and exits OK.

Run:  python tests/test_viasocket_send.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from src.risk.ml_adapter import get_ml_result
from src.integration.viasocket_client import build_risk_event, send_risk_event


def main():
    ml = get_ml_result("2016-07-03", "PUNE_G004")
    assert abs(ml["ml_anomaly_score"] - 91.74) < 1e-9
    assert ml["anomaly_percentile"] == 91

    payload = build_risk_event(ml, event_type="TEST_EVENT")

    print("PAYLOAD (local verification):")
    print(json.dumps(payload, indent=2))

    assert payload["event"] == "pune.flood_risk.updated"
    assert payload["ml"]["anomaly_score"] == 91.74
    assert payload["rule"] == {"score": None, "risk_level": None,
                               "recommended_actions": []}
    assert payload["hybrid"] == {"final_risk_score": None, "risk_level": None}
    assert payload["metadata"]["event_type"] == "TEST_EVENT"
    print()
    print("[PASS] payload conforms to contract; rule/hybrid fields are null")

    result = send_risk_event(payload)
    print("send result:", result)

    if result["status"] == "skipped":
        print()
        print("viaSocket adapter ready; webhook configuration pending.")
    elif result["status"] == "delivered":
        print("[PASS] ONE test event delivered to viaSocket")
    else:
        print("[WARN] send attempted but failed — see log above")


if __name__ == "__main__":
    main()
