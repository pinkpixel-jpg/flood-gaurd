"""PHASE 6B — ONE-SHOT ViaSocket EMAIL notification test.

Sends exactly ONE event through the EXISTING transport so the already
configured ViaSocket email workflow fires once. No retries, no loops,
no secrets printed. Values asserted against the frozen replay row.
"""

import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from dotenv import load_dotenv

load_dotenv()

from src.risk.live_risk import get_live_risk
from src.integration.viasocket_client import send_risk_event


def main():
    ml = get_live_risk("2024-07-15", "PUNE_G004")
    assert ml["risk_score"] == 79.22
    assert ml["risk_level"] == "HIGH"
    assert ml["risk_trend"] == "INCREASING"
    assert ml["mode"] == "HISTORICAL_REPLAY"

    payload = {
        "event": "pune.flood_risk.updated",
        "date": ml["date"],
        "grid_id": ml["grid_id"],
        "risk_score": ml["risk_score"],
        "risk_level": ml["risk_level"],
        "risk_trend": ml["risk_trend"],
        "mode": "HISTORICAL_REPLAY",
        "demo": True,
        "email_template": {
            "subject": "[DEMO] HIGH FLOOD RISK — PUNE_G004",
            "body": [
                "FLOODGUARD AI — HISTORICAL REPLAY DEMO",
                "",
                "Zone: PUNE_G004",
                "Date: 2024-07-15",
                "",
                "Risk Score: 79.22",
                "Risk Level: HIGH",
                "Risk Trend: INCREASING",
                "",
                "Recommended action:",
                "Preventive action recommended.",
                "",
                "HISTORICAL REPLAY / DEMO",
                "NOT A LIVE FLOOD WARNING",
            ],
        },
        "message": ("High zone risk detected during historical replay. "
                    "Preventive action recommended."),
        "disclaimer": "HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING",
    }

    print("PAYLOAD (local verification):")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    assert payload["demo"] is True
    assert payload["email_template"]["subject"].startswith("[DEMO]")
    print("\n[PASS] contract + [DEMO] labelling verified; sending ONE event")

    ts = datetime.now(timezone.utc).isoformat()
    result = send_risk_event(payload)  # exactly ONE POST

    record = {
        "attempted": result.get("status") != "skipped",
        "http_status": result.get("http_status"),
        "delivery_status": result.get("status"),
        "timestamp_utc": ts,
    }
    print("\nDELIVERY RECORD (secrets excluded):")
    print(json.dumps(record, indent=2))
    return record


if __name__ == "__main__":
    main()
