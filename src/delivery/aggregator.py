"""MODULE 5 — Delivery/aggregation layer (backend contracts).

Combines the FROZEN outputs of Modules 1-4 into one normalized zone
response, plus role views, citizen-report intake, safe-route status and
a ViaSocket event builder.

Aggregation ONLY: no new science, no model calls, no fabricated values.
Missing information is emitted as null / UNAVAILABLE.
"""

import json
import logging
import os

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(_DIR, "delivery_config.json")
VULN_CSV = "outputs/vulnerability/vulnerability_scores.csv"
XGB_SCORES_CSV = "outputs/vulnerability/xgboost_vulnerability_scores.csv"

_RIVER_CACHE = {}


def river_status(grid_id, date):
    """REAL CWC river-level reading for a zone/date from the frozen dataset.

    Returns {'available', 'level_mean_m', 'level_max_m', 'stations'}.
    Missing telemetry -> available=False with nulls (never zero/estimated).
    """
    key = (grid_id, str(date))
    if "df" not in _RIVER_CACHE:
        df = pd.read_csv(
            "data/processed/pune_ml_dataset.csv",
            usecols=["Date", "Grid_ID", "river_level_daily_mean_m",
                     "river_level_daily_max_m", "cwc_stations_in_cell"],
            parse_dates=["Date"])
        _RIVER_CACHE["df"] = df
    row = _RIVER_CACHE["df"][
        (_RIVER_CACHE["df"].Grid_ID == grid_id) &
        (_RIVER_CACHE["df"].Date == pd.Timestamp(date))]
    if row.empty:
        return {"available": False, "level_mean_m": None,
                "level_max_m": None, "stations": None}
    r = row.iloc[0]
    if pd.isna(r["river_level_daily_mean_m"]):
        return {"available": False, "level_mean_m": None,
                "level_max_m": None, "stations": None}
    return {
        "available": True,
        "level_mean_m": round(float(r["river_level_daily_mean_m"]), 2),
        "level_max_m": round(float(r["river_level_daily_max_m"]), 2),
        "stations": int(r["cwc_stations_in_cell"]),
    }


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _vulnerability(grid_id):
    df = pd.read_csv(VULN_CSV)
    row = df[df.Grid_ID == grid_id]
    if row.empty:
        return {"score": None, "level": None,
                "explanations": [], "xgboost_proxy_score": None}
    r = row.iloc[0]
    xgb = pd.read_csv(XGB_SCORES_CSV)
    xrow = xgb[xgb.Grid_ID == grid_id]
    xg = float(xrow["vulnerability_score"].iloc[0]) if len(xrow) else None
    return {
        "score": float(r["vulnerability_score"]),
        "level": r["vulnerability_level"],
        "explanations": [t for t in str(r["top_contributors"]).split("; ")],
        "target_type": "transparent_vulnerability_index",
        "xgboost_proxy": {
            "score": xg,
            "target_type": "hydrologic_vulnerability_proxy",
            "note": "rule-distilled exposure estimate; NOT flood probability",
        },
    }


def build_zone_response(date, grid_id, citizen_reports=0):
    """Normalized MNC/DISASTER view. All values from frozen module outputs."""
    cfg = load_config()
    if grid_id not in cfg["zone_display_names"]:
        raise ValueError(f"unknown grid_id {grid_id!r}")

    from src.risk.live_risk import get_live_risk
    risk = get_live_risk(date, grid_id)

    vuln = _vulnerability(grid_id)

    context = {
        "date": risk["date"],
        "grid_id": grid_id,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "risk_trend": risk["risk_trend"] or "STABLE",
        "citizen_reports": int(citizen_reports),
    }
    from src.risk.rule_engine import evaluate_prevention
    prevention = evaluate_prevention(context)
    checklist = cfg.get("checklist_by_priority", {}).get(
        prevention["priority"], [])

    env_date_ok = True
    try:
        from src.risk.heat_water import get_environmental_risk
        env = get_environmental_risk(risk["date"], grid_id)
    except ValueError:
        env_date_ok = False

    # telemetry honesty block (source of truth: Module 4 config)
    try:
        with open(os.path.join(os.path.dirname(__file__),
                               "heat_water_config.json")) as f:
            telemetry_status = json.load(f)["telemetry_status"]
    except Exception:
        telemetry_status = {"temperature_telemetry": "UNAVAILABLE",
                            "reservoir_storage_telemetry": "UNAVAILABLE"}

    environment = {
        "heat": {"score": None, "level": None, "type": "EXPOSURE_PROXY"},
        "water": {"score": None, "level": None, "type": "WATER_DEFICIT_PROXY"},
        "data_status": telemetry_status,
    }
    if not env_date_ok:
        environment["status"] = "UNAVAILABLE_FOR_DATE"
        environment["reason"] = ("requested date outside environmental table "
                                 "(nulls, not invented values)")
    else:
        environment["heat"] = {"score": env["heat"]["score"],
                               "level": env["heat"]["level"],
                               "type": env["heat"]["type"]}
        environment["water"] = {"score": env["water"]["score"],
                                "level": env["water"]["level"],
                                "type": env["water"]["type"]}

    return {
        "date": risk["date"],
        "grid_id": grid_id,
        "zone_name": cfg["zone_display_names"][grid_id],
        "vulnerability": vuln,
        "risk": {
            "score": risk["risk_score"],
            "level": risk["risk_level"],
            "trend": risk["risk_trend"],
            "mode": risk["mode"],
            "components": {
                "anomaly": risk["components"]["anomaly_score"],
                "temporal_rainfall": risk["components"]["temporal_rainfall_signal"],
                "vulnerability": risk["components"]["vulnerability_score"],
            },
            "disclaimer": risk["disclaimer"],
        },
        "prevention": {
            "priority": prevention["priority"],
            "recommended_actions": prevention["recommended_actions"],
            "checklist": checklist,
            "explanations": prevention["explanations"],
            "triggered_rules": [
                {"rule_id": t["rule_id"], "condition": t["condition"],
                 "action": t["action"], "explanation": t["explanation"]}
                for t in prevention["triggered_rules"]
            ],
        },
        "environment": environment,
        "citizen_reports": {"count": int(citizen_reports)},
        "river": river_status(grid_id, risk["date"]),
        "routing": dict(cfg["routing"]),
        "metadata": {
            "system": cfg["system"],
            "mode": cfg["mode"],
            "data_status": risk["data_status"],
        },
    }


def public_view(zone_response):
    """PUBLIC access level: no operational/vulnerability detail."""
    cfg = load_config()
    z = zone_response
    level = z["risk"]["level"]
    return {
        "date": z["date"],
        "grid_id": z["grid_id"],
        "zone_name": z["zone_name"],
        "risk": {"score": z["risk"]["score"], "level": level,
                 "trend": z["risk"]["trend"]},
        "public_alert": cfg["public_advisories_by_level"].get(level),
        "citizen_reporting": {"enabled": cfg["citizen_reporting"]["enabled"]},
        "routing": {"status": z["routing"]["status"],
                    "reason": z["routing"].get("reason")},
        "metadata": {"system": z["metadata"]["system"],
                     "mode": z["metadata"]["mode"]},
    }


ROLE_VIEWS = {
    "PUBLIC": lambda payload: public_view(payload),
    "MNC": lambda payload: payload,
    "DISASTER": lambda payload: payload,
}


def render_for_role(payload, role):
    view = ROLE_VIEWS.get(role)
    if view is None:
        raise ValueError(f"unknown role {role!r}; expected one of "
                         f"{sorted(ROLE_VIEWS)}")
    return view(payload)


def build_viasocket_event(zone_response):
    """Clean automation event per docs/VIA_SOCKET_INTEGRATION.md."""
    z = zone_response
    return {
        "event": "pune.flood_risk.updated",
        "date": z["date"],
        "grid_id": z["grid_id"],
        "risk": {"score": z["risk"]["score"], "level": z["risk"]["level"],
                 "trend": z["risk"]["trend"]},
        "prevention": {"priority": z["prevention"]["priority"],
                       "recommended_actions": z["prevention"]["recommended_actions"]},
        "metadata": {"source": z["metadata"]["system"]},
    }
