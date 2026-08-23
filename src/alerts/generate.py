"""Build PUBLIC and MUNICIPAL alert payloads from EXISTING module outputs.

No risk recalculation: Module 2 (get_live_risk) + Module 3
(evaluate_prevention) + delivery aggregation are reused verbatim.

Alert strategy:
- PUBLIC: Reassuring tone, action-oriented, no panic-inducing language
- MUNICIPAL: Direct/blunt, exact numbers, operational details

ViaSocket delivery:
- Separate webhooks for public vs municipal channels
- Triggered when risk level >= HIGH or on level change
"""

import logging
import os
import requests

from src.risk.live_risk import get_live_risk
from src.risk.rule_engine import evaluate_prevention
from src.delivery.aggregator import build_zone_response, load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRIDS = ("PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004")

ZONE_NAMES = {
    "PUNE_G001": "West-Central Pune",
    "PUNE_G002": "East Pune",
    "PUNE_G003": "North-West Pune",
    "PUNE_G004": "North-East Pune",
}

# ── PUBLIC ALERT MESSAGES ──────────────────────────────────────────
# Tone: Reassuring, action-oriented, no panic
# Purpose: Inform citizens what to do, not scare them

PUBLIC_MESSAGES = {
    "LOW": {
        "headline": "FloodGuard Update — {zone}",
        "status": "All clear in your area.",
        "what_happening": "Weather conditions are stable. No flood risk detected.",
        "what_to_do": [
            "No action needed right now",
            "Stay updated with local weather forecasts",
        ],
        "tone": "calm",
    },
    "MODERATE": {
        "headline": "FloodGuard Advisory — {zone}",
        "status": "Some activity building up. Stay aware.",
        "what_happening": (
            "We're monitoring some weather patterns that could cause "
            "minor waterlogging in low-lying areas."
        ),
        "what_to_do": [
            "Keep your phone charged for updates",
            "Know your area's drainage spots",
            "Avoid walking through standing water if you see it",
        ],
        "tone": "aware",
    },
    "HIGH": {
        "headline": "FloodGuard Alert — {zone}",
        "status": "Elevated risk today. Please be cautious.",
        "what_happening": (
            "Conditions are building up that could lead to waterlogging "
            "in some parts of your area. We're watching it closely."
        ),
        "what_to_do": [
            "Avoid low-lying areas and underpasses if possible",
            "Keep emergency contacts handy",
            "Move vehicles to higher ground if parked in flood-prone spots",
            "Follow updates from Pune Municipal Corporation",
        ],
        "tone": "cautious",
    },
    "CRITICAL": {
        "headline": "FloodGuard Warning — {zone}",
        "status": "Significant risk. Take precautions now.",
        "what_happening": (
            "Heavy rainfall and conditions suggest a real risk of "
            "waterlogging or flooding in parts of your area."
        ),
        "what_to_do": [
            "Stay away from rivers, drains, and low-lying roads",
            "Move to higher floors if you're in a ground-floor or basement unit",
            "Keep emergency supplies ready (water, flashlight, charger)",
            "Follow official instructions from disaster management authorities",
            "Do not attempt to cross flooded roads on foot or in a vehicle",
        ],
        "tone": "urgent",
    },
}

# ── MUNICIPAL ALERT MESSAGES ───────────────────────────────────────
# Tone: Direct, blunt, operational
# Purpose: Exact situation, numbers, actions needed

MUNICIPAL_MESSAGES = {
    "LOW": {
        "headline": "ZONE STATUS: {zone} ({grid_id})",
        "situation": "LOW risk — no immediate action required.",
        "action_required": "Continue routine monitoring.",
    },
    "MODERATE": {
        "headline": "ZONE STATUS: {zone} ({grid_id})",
        "situation": "MODERATE risk — conditions building, monitor closely.",
        "action_required": (
            "Pre-position resources. Alert field teams. "
            "Review drainage capacity in priority wards."
        ),
    },
    "HIGH": {
        "headline": "ZONE ALERT: {zone} ({grid_id})",
        "situation": "HIGH risk — waterlogging probable in low-lying areas.",
        "action_required": (
            "Activate response protocols. Deploy pumps to priority locations. "
            "Alert disaster-management personnel. Prepare shelters if needed."
        ),
    },
    "CRITICAL": {
        "headline": "ZONE EMERGENCY: {zone} ({grid_id})",
        "situation": "CRITICAL risk — flooding possible. Immediate action required.",
        "action_required": (
            "FULL ACTIVATION: Deploy all available resources. "
            "Evacuate vulnerable areas. Activate emergency shelters. "
            "Coordinate with NDRF/SDRF if needed. Issue public warnings."
        ),
    },
}


def _format_public_message(zone_name, risk_level, risk_score, trend):
    """Build a formatted public alert message."""
    tmpl = PUBLIC_MESSAGES.get(risk_level, PUBLIC_MESSAGES["LOW"])
    trend_str = trend.lower() if trend else "stable"

    return {
        "headline": tmpl["headline"].format(zone=zone_name),
        "status": tmpl["status"],
        "what_happening": tmpl["what_happening"],
        "what_to_do": tmpl["what_to_do"],
        "risk_level": risk_level,
        "risk_score": risk_score,
        "trend": trend_str,
        "tone": tmpl["tone"],
        "source": "FloodGuard AI — Pune",
    }


def _format_municipal_message(zone_name, grid_id, risk, prevention, env):
    """Build a formatted municipal alert message with full operational detail."""
    tmpl = MUNICIPAL_MESSAGES.get(risk["level"], MUNICIPAL_MESSAGES["LOW"])
    components = risk["components"]

    return {
        "headline": tmpl["headline"].format(zone=zone_name, grid_id=grid_id),
        "situation": tmpl["situation"],
        "action_required": tmpl["action_required"],
        "risk": {
            "score": risk["score"],
            "level": risk["level"],
            "trend": risk["trend"],
        },
        "components": {
            "anomaly": f"{components['anomaly']:.1f}/100",
            "temporal_rainfall": f"{components['temporal_rainfall']:.1f}/100",
            "vulnerability": f"{components['vulnerability']:.1f}/100",
        },
        "vulnerability": {
            "score": prevention.get("vulnerability_score"),
            "level": prevention.get("vulnerability_level"),
        },
        "prevention": {
            "priority": prevention["priority"],
            "actions": prevention["recommended_actions"],
            "checklist": prevention["checklist"],
        },
        "environment": {
            "heat": f"{env['heat']['score']:.1f}/100 ({env['heat']['level']})",
            "water_deficit": f"{env['water']['score']:.1f}/100 ({env['water']['level']})",
        },
        "source": "FloodGuard AI — Pune MNC Operations",
    }


def public_payload(risk):
    """Build public alert payload with formatted message."""
    zone_name = ZONE_NAMES.get(risk["grid_id"], risk["grid_id"])
    msg = _format_public_message(
        zone_name, risk["risk_level"], risk["risk_score"], risk["risk_trend"]
    )
    return {
        "date": risk["date"],
        "grid_id": risk["grid_id"],
        "zone_name": zone_name,
        "risk_level": risk["risk_level"],
        "risk_score": risk["risk_score"],
        "trend": risk["risk_trend"],
        "message": msg,
        "simple_explanation": msg["what_happening"],
        "safety_recommendation": "\n".join(f"• {a}" for a in msg["what_to_do"]),
        "mode": risk["mode"],
    }


def municipal_payload(date, grid_id, citizen_reports=0):
    """Build municipal alert payload with operational details."""
    z = build_zone_response(date, grid_id, citizen_reports)
    zone_name = ZONE_NAMES.get(grid_id, grid_id)
    msg = _format_municipal_message(
        zone_name, grid_id, z["risk"], z["prevention"], z["environment"]
    )
    return {
        "date": z["date"],
        "grid_id": grid_id,
        "zone_name": zone_name,
        "risk": {
            "score": z["risk"]["score"],
            "level": z["risk"]["level"],
            "trend": z["risk"]["trend"],
            "components": z["risk"]["components"],
        },
        "vulnerability": {"score": z["vulnerability"]["score"],
                          "level": z["vulnerability"]["level"]},
        "prevention": {"priority": z["prevention"]["priority"],
                       "recommended_actions": z["prevention"]["recommended_actions"],
                       "checklist": z["prevention"]["checklist"],
                       "explanations": z["prevention"]["explanations"]},
        "environment": z["environment"],
        "citizen_reports": z["citizen_reports"],
        "message": msg,
        "metadata": z["metadata"],
    }


# ── VIASOCKET DELIVERY ─────────────────────────────────────────────

VIASOCKET_WEBHOOK = "https://flow.sokt.io/func/scriNy02Qedm"


def send_via_viasocket(payload, channel="public"):
    """Send alert payload to ViaSocket webhook.

    channel: 'public' or 'municipal'
    Returns delivery status dict.
    """
    url = VIASOCKET_WEBHOOK
    event_name = f"pune.alert.{channel}"

    body = {
        "event": event_name,
        "source": "FloodGuard AI",
        "channel": channel,
        "payload": payload,
    }

    try:
        resp = requests.post(url, json=body, timeout=10)
        if 200 <= resp.status_code < 300:
            logger.info("viaSocket %s delivered: %s", channel, resp.status_code)
            return {"status": "delivered", "http_status": resp.status_code, "channel": channel}
        else:
            logger.warning("viaSocket %s rejected: %s", channel, resp.status_code)
            return {"status": "error", "http_status": resp.status_code, "channel": channel}
    except requests.Timeout:
        logger.error("viaSocket %s timeout", channel)
        return {"status": "error", "reason": "timeout", "channel": channel}
    except Exception as e:
        logger.error("viaSocket %s failed: %s", channel, type(e).__name__)
        return {"status": "error", "reason": str(e), "channel": channel}


def should_alert(current_level, previous_level=None):
    """Determine if an alert should be sent.

    Triggers:
    - Risk level >= HIGH (always alert)
    - Risk level changed from previous (informational)
    """
    priority = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
    curr = priority.get(current_level, 0)

    # Always alert for HIGH or CRITICAL
    if curr >= 3:
        return True

    # Alert on level change
    if previous_level and previous_level != current_level:
        return True

    return False


def generate_all_for_date(date, citizen_reports=0, channel=None):
    """Generate + persist alerts for all four zones; returns summary.

    channel: None = send both, "public" = public only, "municipal" = municipal only.
    Sends ViaSocket alerts when triggered.
    """
    from src.alerts import store

    out = {"public": [], "municipal": [], "viasocket_results": []}

    for gid in GRIDS:
        risk = get_live_risk(date, gid)
        pub = public_payload(risk)

        store.insert_public_alert(
            pub["date"], gid, pub["risk_level"], pub["risk_score"],
            pub["trend"], pub["simple_explanation"], pub["safety_recommendation"]
        )
        out["public"].append(pub)

        mun = municipal_payload(date, gid, citizen_reports)
        store.insert_municipal_alert(mun["date"], gid, mun)
        out["municipal"].append(mun)

        if should_alert(pub["risk_level"]):
            if channel is None or channel == "public":
                pub_result = send_via_viasocket(pub, channel="public")
                out["viasocket_results"].append(pub_result)

            if channel is None or channel == "municipal":
                mun_result = send_via_viasocket(mun, channel="municipal")
                out["viasocket_results"].append(mun_result)

    logger.info("alerts generated for %s (%d zones) channel=%s", date, len(GRIDS), channel)
    return out


if __name__ == "__main__":
    res = generate_all_for_date("2024-07-15")
    print("Public:", res["public"][0]["message"]["headline"])
    print("Municipal:", res["municipal"][0]["message"]["headline"])
    print("ViaSocket:", res["viasocket_results"])
