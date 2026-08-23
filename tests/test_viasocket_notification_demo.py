"""PHASE 6 — ONE-SHOT ML-only ViaSocket notification demo.

Uses the REAL frozen historical replay observation:
    2024-07-15 / PUNE_G004 / 79.22 HIGH / INCREASING
Sends exactly ONE POST via the EXISTING transport (viasocket_client).
No retries, no loops, no secrets printed.
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

    # freeze-guard: refuse to run if values drift from the verified replay row
    assert ml["risk_score"] == 79.22 and ml["risk_level"] == "HIGH"
    assert ml["risk_trend"] == "INCREASING" and ml["mode"] == "HISTORICAL_REPLAY"

    payload = {
        "event": "pune.flood_risk.updated",
        "date": ml["date"],
        "grid_id": ml["grid_id"],
        "risk_score": ml["risk_score"],
        "risk_level": ml["risk_level"],
        "risk_trend": ml["risk_trend"],
        "mode": "HISTORICAL_REPLAY",
        "demo": True,
        "message": ("High zone risk detected during historical replay. "
                    "Preventive action recommended."),
        "disclaimer": "HISTORICAL REPLAY / DEMO — NOT A LIVE FLOOD WARNING",
    }

    print("LOCAL PAYLOAD VERIFICATION:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    required = {"event", "date", "grid_id", "risk_score", "risk_level",
                "risk_trend", "mode", "demo", "message", "disclaimer"}
    assert set(payload) == required
    assert payload["demo"] is True
    assert "LIVE FLOOD WARNING" in payload["disclaimer"]
    print("\n[PASS] payload matches Phase-6 contract; demo flags present")

    ts_utc = datetime.now(timezone.utc).isoformat()
    result = send_risk_event(payload)   # exactly ONE POST, no retries

    record = {
        "attempted": result.get("status") != "skipped",
        "http_status": result.get("http_status"),
        "delivery_status": result.get("status"),
        "timestamp_utc": ts_utc,
    }
    print("\nDELIVERY RECORD (secrets excluded by design):")
    print(json.dumps(record, indent=2))
    return record


if __name__ == "__main__":
    main()
