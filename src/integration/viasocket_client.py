"""VIASOCKET CLIENT — automation/transport adapter.

Sends risk-event payloads to a viaSocket webhook.

Rules enforced by design:
- webhook URL comes ONLY from the environment (VIASOCKET_WEBHOOK_URL)
- the URL is never logged and never written to disk
- HTTP errors are handled; a missing configuration is not a failure
- payloads are built from REAL adapter output; nulls stay null

This module performs NO computation: no rule scores, no hybrid
weighting, no ML inference.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

ENV_VAR = "VIASOCKET_WEBHOOK_URL"
DEFAULT_TIMEOUT_S = 10

EVENT_NAME = "pune.flood_risk.updated"
SOURCE_NAME = "Pune FloodShield"
MODEL_NAME = "IsolationForest"
MODEL_VERSION = "v1"


def get_webhook_url():
    """Return configured webhook URL or None if not configured."""
    url = os.environ.get(ENV_VAR, "").strip()
    return url or None


def build_risk_event(ml_result, event_type="RISK_EVENT", demo=None):
    """Build the viaSocket payload contract from an ML adapter result.

    ml_result: dict from src.risk.ml_adapter.get_ml_result()
    demo: optional prototype-only section from src.integration.demo_branch
          (removed once the rule engine is merged).
    Rule and hybrid sections are intentionally null until those engines
    exist. Nulls must never be replaced with invented values.
    """
    payload = {
        "event": EVENT_NAME,
        "date": ml_result["date"],
        "grid_id": ml_result["grid_id"],
        "ml": {
            "anomaly_score": float(ml_result["ml_anomaly_score"]),
            "anomaly_percentile": int(ml_result["anomaly_percentile"]),
        },
        "rule": {
            "score": None,
            "risk_level": None,
            "recommended_actions": [],
        },
        "hybrid": {
            "final_risk_score": None,
            "risk_level": None,
        },
        "metadata": {
            "source": SOURCE_NAME,
            "model": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "event_type": event_type,
        },
    }
    if demo is not None:
        payload["demo"] = demo
    return payload


def send_risk_event(payload, timeout_s=DEFAULT_TIMEOUT_S):
    """Send one payload to the configured viaSocket webhook.

    Returns a status dict; never raises for network/config issues so a
    missing webhook cannot break the pipeline. Logs safely (no secrets).
    """
    safe_desc = f"{payload.get('event')} {payload.get('date')} {payload.get('grid_id')}" \
        if isinstance(payload, dict) else str(type(payload))

    url = get_webhook_url()
    if not url:
        logger.info("viaSocket skipped (%s): %s not configured", safe_desc, ENV_VAR)
        return {"status": "skipped", "reason": "webhook_not_configured"}

    try:
        resp = requests.post(url, json=payload, timeout=timeout_s)
    except requests.Timeout:
        logger.error("viaSocket timeout after %ss (%s)", timeout_s, safe_desc)
        return {"status": "error", "reason": "timeout"}
    except requests.RequestException as e:
        logger.error("viaSocket request failed (%s): %s", safe_desc, type(e).__name__)
        return {"status": "error", "reason": type(e).__name__}

    if 200 <= resp.status_code < 300:
        logger.info("viaSocket delivered (%s) http=%s", safe_desc, resp.status_code)
        return {"status": "delivered", "http_status": resp.status_code}

    logger.error("viaSocket rejected payload (%s) http=%s", safe_desc, resp.status_code)
    return {"status": "error", "http_status": resp.status_code}
