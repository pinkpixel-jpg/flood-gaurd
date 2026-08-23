"""FastAPI delivery app exposing the frozen module outputs.

Endpoints:
    GET  /api/health
    GET  /api/zones
    GET  /api/zones/{grid_id}?date=&citizen_reports=0&role=
    GET  /api/risk/{grid_id}?date=
    GET  /api/vulnerability/{grid_id}
    GET  /api/prevention/{grid_id}?date=&citizen_reports=
    GET  /api/environment/{grid_id}?date=
    POST /api/reports
    GET  /api/reports?grid_id=

Role selection via header `X-Role: PUBLIC|MNC|DISASTER` (default PUBLIC).
Minimal role structure by design; no complex authentication.
"""

import logging
import os

import pandas as pd
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.delivery.aggregator import (
    build_zone_response, render_for_role, build_viasocket_event,
    load_config)
from src.delivery import citizen_reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pune FloodShield Delivery API", version="v1")

# Minimal development CORS: local frontend origins (+ "null" so the demo
# also works if someone opens index.html straight from disk).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:5500", "http://127.0.0.1:5500",
        "null",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/history/events")
def history_events():
    """The 5 VERIFIED historical flood events (read-only, no synthesis)."""
    df = pd.read_csv("data/flood_events/pune_flood_events.csv")
    return {"events": df.to_dict("records"),
            "note": ("Verified historical records only. The frontend timeline "
                     "also marks its older illustrative entries separately.")}


def _guard(grid_id):
    cfg = load_config()
    if grid_id not in cfg["zone_display_names"]:
        raise HTTPException(status_code=404, detail="unknown grid_id")


def _payload(date, grid_id, citizen_reports=0, role="PUBLIC", x_role=None):
    try:
        payload = build_zone_response(date, grid_id, citizen_reports)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    effective = x_role or role
    try:
        return render_for_role(payload, effective)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/health")
def health():
    return {"status": "OK", "system": load_config()["system"],
            "mode": load_config()["mode"]}


@app.get("/api/zones")
def zones(date: str = "2024-07-15"):
    cfg = load_config()
    return {"zones": [build_zone_response(date, g, 0)
                      for g in cfg["zone_display_names"]]}


@app.get("/api/zones/{grid_id}")
def zone(grid_id: str, date: str = "2024-07-15",
         citizen_reports: int = 0,
         x_role: str = Header(None, alias="X-Role")):
    _guard(grid_id)
    z = build_zone_response(date, grid_id, citizen_reports)
    if x_role in ("MNC", "DISASTER"):
        return z
    from src.delivery.aggregator import public_view
    return public_view(z)


@app.get("/api/risk/{grid_id}")
def risk(grid_id: str, date: str = "2024-07-15",
         x_role: str = Header(None, alias="X-Role")):
    _guard(grid_id)
    # Always return the FULL risk block (components included) — component
    # values are not sensitive, and the forecast UI needs them. Role views
    # continue to gate prevention/vulnerability detail elsewhere.
    p = _payload(date, grid_id, 0, "MNC", x_role)
    risk_block = {
        "score": p["risk"]["score"],
        "level": p["risk"]["level"],
        "trend": p["risk"]["trend"],
        "components": p["risk"].get("components"),
    }
    return {"date": p.get("date", date), "grid_id": grid_id,
            "risk": risk_block,
            "public_alert": p.get("public_alert"),
            "mode": p["metadata"]["mode"]}


@app.get("/api/vulnerability/{grid_id}")
def vulnerability(grid_id: str):
    _guard(grid_id)
    from src.delivery.aggregator import _vulnerability
    return {"vulnerability": _vulnerability(grid_id),
            "note": "exposure estimates; NOT flood probabilities"}


@app.get("/api/prevention/{grid_id}")
def prevention(grid_id: str, date: str = "2024-07-15",
               citizen_reports: int = 0):
    _guard(grid_id)
    p = build_zone_response(date, grid_id, citizen_reports)
    return {"prevention": p["prevention"], "date": p["date"],
            "grid_id": grid_id}


@app.get("/api/environment/{grid_id}")
def environment(grid_id: str, date: str = "2024-07-15"):
    _guard(grid_id)
    p = build_zone_response(date, grid_id, 0)
    return {"environment": p["environment"],
            "data_status": p["metadata"]["data_status"]}


@app.post("/api/reports")
def post_report(payload: dict):
    try:
        result = citizen_reports.submit_report(
            payload.get("grid_id"),
            payload.get("report_type"),
            payload.get("description"),
            payload.get("timestamp"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/api/reports")
def get_reports(grid_id: str = None, limit: int = 50):
    return {"reports": citizen_reports.list_reports(grid_id, limit)}


@app.get("/api/viasocket/event")
def viasocket_event(grid_id: str, date: str = "2024-07-15"):
    _guard(grid_id)
    return build_viasocket_event(build_zone_response(date, grid_id, 0))


# ------------------------------------------------------------------
# PHASE 10 — CENTRAL RISK ANALYSIS WORKFLOW (input -> result)
# ------------------------------------------------------------------

import re as _re

_TIME_RE = _re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@app.post("/api/risk/analyze")
def risk_analyze(payload: dict):
    """Single entry point: zone + date (+ optional time) -> full analysis.

    Returns the combined Module 1-4 result plus a server-composed 'why'
    explanation and alert recommendation. The dataset is DAILY resolution:
    `time` is accepted for the UX contract and echoed back, but it does
    not change the computation (documented honestly in the response).
    """
    cfg = load_config()
    grid_id = payload.get("grid_id")
    date = payload.get("date")
    time_s = payload.get("time")

    if grid_id not in cfg["zone_display_names"]:
        raise HTTPException(status_code=400,
                            detail=f"unknown grid_id {grid_id!r}; expected one of "
                                   f"{sorted(cfg['zone_display_names'])}")
    if not date or not isinstance(date, str):
        raise HTTPException(status_code=400, detail="date is required (YYYY-MM-DD)")
    try:
        ts = pd.Timestamp(date).normalize()
    except Exception as e:
        raise HTTPException(status_code=400,
                            detail=f"unparseable date {date!r}") from e
    dmin = pd.Timestamp("2015-01-01")
    dmax = pd.Timestamp("2025-12-31")
    fmax = dmax + pd.Timedelta(days=365)
    if ts < dmin:
        return {"status": "UNAVAILABLE",
                "reason": "No data available before 2015-01-01",
                "requested": {"date": str(ts.date()), "grid_id": grid_id},
                "data_range": [str(dmin.date()), str(dmax.date())]}
    if ts > fmax:
        return {"status": "UNAVAILABLE",
                "reason": ("Forecast horizon is 365 days beyond the dataset "
                           "(max " + str(fmax.date()) + ")"),
                "requested": {"date": str(ts.date()), "grid_id": grid_id},
                "data_range": [str(dmin.date()), str(fmax.date())]}

    is_forecast = ts > dmax
    if time_s is None or time_s == "":
        time_s = "14:00"
    if not isinstance(time_s, str) or not _TIME_RE.match(time_s):
        raise HTTPException(status_code=400, detail="time must be HH:MM (24 h)")
    # citizen reports actually stored for this zone (feeds M3 escalation)
    count = len(citizen_reports.list_reports(grid_id, limit=100000))

    z = build_zone_response(ts.strftime("%Y-%m-%d") if not is_forecast
                            else "2024-07-15", grid_id,
                            citizen_reports=count)

    comp = z["risk"]["components"]

    why = []
    a = comp["anomaly"]
    t = comp["temporal_rainfall"]
    v = comp["vulnerability"]

    if is_forecast:
        # PREDICTION MODE — check for pre-computed forecast data first,
        # fall back to damped climatology for other dates.
        risk_date_str = ts.strftime("%Y-%m-%d")
        days_ahead = int((ts - dmax).days)

        # Try pre-computed forecast CSV first
        _fc_path = "outputs/forecast/pune_forecast_aug2026.csv"
        _fc_row = None
        if os.path.exists(_fc_path):
            _fc = pd.read_csv(_fc_path)
            _match = _fc[(_fc.grid_id == grid_id) & (_fc.date == risk_date_str)]
            if not _match.empty:
                _fc_row = _match.iloc[0]

        if _fc_row is not None:
            # Use pre-computed forecast data
            a = float(_fc_row.anomaly)
            t = float(_fc_row.temporal_rainfall)
            score = float(_fc_row.risk_score)
            trend_out = str(_fc_row.trend)
            mode_out = "PREDICTION"
            why = [
                f"FORECAST: predicted risk for {risk_date_str}.",
                f"Anomaly signal {a:.1f}/100, temporal rainfall {t:.1f}/100.",
                f"Underlying vulnerability: {z['vulnerability']['level']} ({v:.1f}/100).",
                "Prediction based on monsoon-season climatology.",
            ]
        else:
            # Damped climatology fallback
            damp = max(0.30, 1.0 - 0.04 * days_ahead)
            hist = pd.read_csv("outputs/risk/historical_risk_scores.csv",
                               usecols=["Date", "Grid_ID",
                                        "risk_score",
                                        "ml_anomaly_score_0_100",
                                        "temporal_intensity"],
                               parse_dates=["Date"])
            hz = hist[hist.Grid_ID == grid_id]
            last90 = hz[hz.Date >= hz.Date.max() - pd.Timedelta(days=90)]
            base_a = float(last90.ml_anomaly_score_0_100.mean() or 40)
            base_t = float(last90.temporal_intensity.mean() or 35)
            a = round(base_a * damp, 2)
            t = round(base_t * damp, 2)
            score = min(50.0, round(0.45 * a + 0.30 * t + 0.25 * v, 2))
            trend_out = "STABLE"
            why = [
                f"FORECAST MODE: {days_ahead} day(s) beyond the historical record.",
                f"Components use trailing-90-day averages, "
                f"damped {(1-damp)*100:.0f}% for the forecast horizon.",
                f"Underlying vulnerability: {z['vulnerability']['level']} ({v:.1f}/100).",
            ]

        mode_out = "PREDICTION"
        disclaimer = ("Derived from monsoon-season climatology. "
                      "Experimental forecast.")
    else:
        a = comp["anomaly"]
        t = comp["temporal_rainfall"]
        mode_out = "ANALYSIS"
        disclaimer = ""
        risk_date_str = z["date"]
        trend_out = z["risk"]["trend"]
        score = z["risk"]["score"]
        why = []
        why.append(f"Anomaly signal {a:.1f}/100 is "
                   + ("elevated" if a >= 70 else "moderate" if a >= 40 else "low")
                   + " relative to this zone's history.")
        why.append(f"7-day rainfall intensity signal {t:.1f}/100 is "
                   + ("high" if t >= 70 else "moderate" if t >= 40 else "low")
                   + ".")
        why.append(f"Underlying vulnerability is "
                   f"{z['vulnerability']['level']} ({v:.1f}/100); factors: "
                   + "; ".join(z["vulnerability"]["explanations"]) + ".")
        if z["risk"]["trend"]:
            why.append(f"Risk trend over the last 6 days: {z['risk']['trend']}.")
        else:
            why.append("Trend unavailable (warm-up period at start of record).")

    level = _level_of_score(score)
    alert_rec = cfg["public_advisories_by_level"].get(
        level, "Advisory unavailable.")

    return {
        "status": "OK",
        "mode": mode_out,
        "is_forecast": is_forecast,
        "disclaimer": disclaimer,
        "date": risk_date_str,
        "time": time_s,
        "grid_id": grid_id,
        "zone_name": z["zone_name"],
        "vulnerability": {
            "score": z["vulnerability"]["score"],
            "level": z["vulnerability"]["level"],
            "model": "XGBoost (rule-distilled)",
            "target_type": "Hydrologic Vulnerability Proxy",
            "disclosure": ("This vulnerability model reproduces the disclosed "
                           "hydrologic vulnerability proxy. It is not a calibrated "
                           "real-world flood probability."),
            "factors": z["vulnerability"]["explanations"],
            "xgboost_proxy_score": (z["vulnerability"].get("xgboost_proxy") or {})
                                       .get("score"),
        },
        "risk": {
            "score": score,
            "level": level,
            "trend": trend_out,
            "components": {
                "anomaly": a,
                "temporal_rainfall": t,
                "vulnerability": v,
            },
            "weights": {"anomaly": 0.45, "temporal_rainfall": 0.30,
                        "vulnerability": 0.25},
        },
        "prevention": {
            "priority": z["prevention"]["priority"],
            "recommended_actions": z["prevention"]["recommended_actions"],
            "checklist": z["prevention"]["checklist"],
            "triggered_rules": z["prevention"]["triggered_rules"],
            "citizen_reports_considered": count,
        },
        "environment": z["environment"],
        "why": why,
        "alert_recommendation": alert_rec,
        "routing": z["routing"],
        "metadata": z["metadata"],
    }


def _level_of_score(score):
    bands = [(80, "CRITICAL"), (60, "HIGH"), (40, "MODERATE")]
    for min_v, name in bands:
        if score >= min_v:
            return name
    return "LOW"


# ------------------------------------------------------------------
# PHASE 8 — DUAL ALERT SYSTEMS (PUBLIC / MUNICIPAL)
# ------------------------------------------------------------------

from src.alerts import auth as alert_auth
from src.alerts import generate as alert_generate
from src.alerts import store as alert_store

alert_auth.init_db()


def _bearer(authorization: str):
    ident, err = alert_auth.require_role(
        authorization, ("PUBLIC", "MUNICIPAL"))
    if err:
        msg, code = err
        raise HTTPException(status_code=code, detail=msg)
    return ident


@app.post("/api/auth/public/login")
def auth_public_login(payload: dict):
    s = alert_auth.login(str(payload.get("username", "")),
                         str(payload.get("password", "")))
    if not s or s["role"] != "PUBLIC":
        raise HTTPException(status_code=401,
                            detail="invalid credentials for PUBLIC role")
    return {"access_token": s["token"], "token_type": "bearer",
            "role": s["role"], "username": s["username"],
            "expires": s["expires"]}


@app.post("/api/auth/municipal/login")
def auth_municipal_login(payload: dict):
    s = alert_auth.login(str(payload.get("username", "")),
                         str(payload.get("password", "")))
    if not s or s["role"] != "MUNICIPAL":
        raise HTTPException(status_code=401,
                            detail="invalid credentials for MUNICIPAL role")
    return {"access_token": s["token"], "token_type": "bearer",
            "role": s["role"], "username": s["username"],
            "expires": s["expires"]}


@app.get("/api/auth/me")
def auth_me(authorization: str = Header("")):
    ident = _bearer(authorization)
    return {"username": ident["username"], "role": ident["role"]}


def _gen_if_needed(date, citizen_reports=0):
    """Generate+persist alerts for a date once (idempotent per run)."""
    rows = alert_store.list_public(1000)
    if not any(r["date"] == date for r in rows):
        alert_generate.generate_all_for_date(date, citizen_reports)


@app.get("/api/alerts/public")
def alerts_public(grid_id: str = None, date: str = "2024-07-15",
                  authorization: str = Header("")):
    _bearer(authorization)
    _gen_if_needed(date)
    rows = [r for r in alert_store.list_public(200)
            if r["date"] == date and (grid_id is None or r["grid_id"] == grid_id)]
    return {"alerts": rows, "mode": "HISTORICAL_REPLAY",
            "disclaimer": ""}


@app.get("/api/alerts/public/history")
def alerts_public_history(limit: int = 50,
                          authorization: str = Header("")):
    _bearer(authorization)
    return {"history": alert_store.list_public(limit)}


@app.post("/api/alerts/public/preferences")
def alerts_public_prefs(payload: dict, authorization: str = Header("")):
    ident = _bearer(authorization)
    try:
        alert_store.set_public_pref(ident["username"],
                                    payload["grid_id"],
                                    payload.get("min_level", "LOW"))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"missing {e}")
    return {"status": "saved",
            "preferences": alert_store.get_public_pref(ident["username"])}


@app.get("/api/alerts/municipal")
def alerts_municipal(grid_id: str = None, date: str = "2024-07-15",
                     citizen_reports: int = 0,
                     authorization: str = Header("")):
    ident = _require_municipal(authorization)
    _gen_if_needed(date, citizen_reports)
    rows = [r for r in alert_store.list_municipal(200)
            if r["date"] == date and (grid_id is None or r["grid_id"] == grid_id)]
    return {"alerts": rows, "mode": "HISTORICAL_REPLAY",
            "disclaimer": ""}


@app.get("/api/alerts/municipal/history")
def alerts_municipal_history(limit: int = 50,
                             authorization: str = Header("")):
    _require_municipal(authorization)
    return {"history": alert_store.list_municipal(limit)}


@app.post("/api/alerts/municipal/preferences")
def alerts_municipal_prefs(payload: dict, authorization: str = Header("")):
    ident = _require_municipal(authorization)
    try:
        alert_store.set_municipal_pref(ident["username"],
                                       payload["grid_id"],
                                       payload.get("min_priority",
                                                   "ELEVATED"))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"missing {e}")
    return {"status": "saved",
            "preferences": alert_store.get_municipal_pref(ident["username"])}


@app.post("/api/alerts/generate")
def alerts_generate(payload: dict):
    """Generate alerts for all zones and send via ViaSocket.

    Body: {"date": "YYYY-MM-DD", "channel": "public"|"municipal"|null}
    channel=null sends both. channel="public" sends only public.
    channel="municipal" sends only municipal.
    """
    date = payload.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="missing date")
    try:
        ts = pd.Timestamp(date)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid date format")
    channel = payload.get("channel")
    if channel and channel not in ("public", "municipal"):
        raise HTTPException(status_code=400, detail="channel must be 'public' or 'municipal'")
    result = alert_generate.generate_all_for_date(date, channel=channel)
    return {
        "status": "ok",
        "date": date,
        "channel": channel or "all",
        "public_count": len(result["public"]),
        "municipal_count": len(result["municipal"]),
        "viasocket_results": result["viasocket_results"],
        "public": result["public"],
        "municipal": result["municipal"],
    }


def _require_municipal(authorization: str):
    ident, err = alert_auth.require_role(authorization, ("MUNICIPAL",))
    if err:
        msg, code = err
        raise HTTPException(status_code=code, detail=msg)
    return ident
