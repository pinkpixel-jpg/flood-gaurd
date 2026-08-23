"""LIVE ZONE RISK ENGINE — Module 2 (historical replay implementation).

Combines (all REAL, all pre-existing):
  1. frozen Isolation-Forest anomaly score      [temporal ML signal]
  2. Module 1 Transparent Vulnerability Index   [static signal]
  3. leak-safe expanding percentile of rainfall_7d per grid
                                                [temporal intensity]

Output = documented, configurable "zone risk score" 0-100.
NOT a flood probability, NOT a live prediction (no live feed exists).

Public contract:
    get_live_risk(date="2024-07-15", grid_id="PUNE_G004") -> dict

A future LSTM/sequence model can replace component #1 by producing the
same 0-100 signal per (date x grid); nothing else changes.
"""

import json
import logging
import os

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "live_risk_config.json")
DATASET_PATH = "data/processed/pune_ml_dataset.csv"
ANOMALY_CSV = "outputs/ml/anomaly_scores.csv"
VULN_CSV = "outputs/vulnerability/vulnerability_scores.csv"
OUT_DIR = "outputs/risk"
RISK_CSV = os.path.join(OUT_DIR, "historical_risk_scores.csv")

VALID_GRIDS = ("PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _load_inputs():
    use = ["Date", "Grid_ID", "rainfall_7d",
           "river_level_daily_mean_m", "river_level_daily_max_m",
           "cwc_stations_in_cell"]
    df = pd.read_csv(DATASET_PATH, usecols=use, parse_dates=["Date"])
    anom = pd.read_csv(ANOMALY_CSV, usecols=["Date", "Grid_ID",
                                             "ml_anomaly_score_0_100",
                                             "anomaly_percentile"],
                       parse_dates=["Date"])
    vuln = pd.read_csv(VULN_CSV, usecols=["Grid_ID", "vulnerability_score",
                                          "vulnerability_level"])
    df = df.merge(anom, on=["Date", "Grid_ID"], how="left", validate="1:1")
    assert not df["ml_anomaly_score_0_100"].isna().any(), "anomaly join gap"
    df = df.merge(vuln, on="Grid_ID", how="left", validate="many_to_one")
    assert not df["vulnerability_score"].isna().any(), "vulnerability join gap"
    return df.sort_values(["Grid_ID", "Date"]).reset_index(drop=True)


def _expanding_percentile(s):
    """Leak-safe: percentile of value t among values <= t only (mid-rank)."""
    return s.expanding(min_periods=1).rank(method="average", pct=True) * 100.0


def _level_of(score, bands):
    for name, b in bands.items():
        if b["min"] <= score < b["max_exclusive"]:
            return name
    raise ValueError(f"score {score} outside configured bands")


def _trend_of(delta, th):
    if pd.isna(delta):
        return None
    if delta >= th["STRONGLY_INCREASING"]:
        return "STRONGLY_INCREASING"
    if delta >= th["INCREASING"]:
        return "INCREASING"
    if delta > th["STABLE"]:
        return "STABLE"
    return "DECREASING"


def build_risk_table(write=True):
    cfg = load_config()
    w = cfg["weights"]
    df = _load_inputs()

    df["temporal_intensity"] = (
        df.groupby("Grid_ID")["rainfall_7d"]
          .apply(lambda s: _expanding_percentile(s.fillna(0.0)))
          .round(2).reset_index(level=0, drop=True))

    df["risk_score"] = (
        w["ml_anomaly"]["weight"] * df["ml_anomaly_score_0_100"]
        + w["temporal_intensity"]["weight"] * df["temporal_intensity"]
        + w["vulnerability"]["weight"] * df["vulnerability_score"]
    ).round(2)

    df["risk_level"] = df["risk_score"].apply(lambda s: _level_of(s, cfg["risk_levels"]))

    g = df.groupby("Grid_ID")["risk_score"]
    recent = g.transform(lambda s: s.rolling(cfg["trend"]["recent_window_days"]).mean())
    previous = g.transform(
        lambda s: s.shift(cfg["trend"]["gap_days"] + cfg["trend"]["previous_window_days"])
                   .rolling(cfg["trend"]["previous_window_days"]).mean())
    df["risk_delta_3d"] = (recent - previous).round(2)
    df["risk_trend"] = df["risk_delta_3d"].apply(lambda d: _trend_of(d, cfg["trend"]["thresholds"]))

    cwc_ok = df["river_level_daily_mean_m"].notna() & df["river_level_daily_max_m"].notna()
    df["cwc_available"] = np.where(cwc_ok, "yes", "no")

    def signals(r):
        out = []
        p = r["anomaly_percentile"]
        out.append(f"ML anomaly {r['ml_anomaly_score_0_100']:.0f}/100 "
                   f"({'top ' + str(int(100-p))+'%' if p >= 95 else f'percentile {int(p)}'})")
        out.append(f"7-day rainfall percentile {r['temporal_intensity']:.0f}/100 "
                   f"(vs zone history, leak-safe)")
        out.append(f"vulnerability {r['vulnerability_score']:.1f} ({r['vulnerability_level']})")
        if r["cwc_available"] == "yes":
            out.append(f"river level {r['river_level_daily_max_m']:.2f} m "
                       f"({int(r['cwc_stations_in_cell'])} station)")
        else:
            out.append("river level unavailable (no CWC data for this cell/date)")
        return out

    df["key_signals"] = df.apply(signals, axis=1).apply(json.dumps, ensure_ascii=False)
    df["mode"] = "HISTORICAL_REPLAY"

    keep = ["Date", "Grid_ID", "risk_score", "risk_level", "risk_trend",
            "risk_delta_3d", "ml_anomaly_score_0_100", "vulnerability_score",
            "vulnerability_level", "temporal_intensity", "rainfall_7d",
            "cwc_available", "cwc_stations_in_cell", "key_signals", "mode"]

    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        df[keep].to_csv(RISK_CSV, index=False)
        logger.info("risk table -> %s (%d rows)", RISK_CSV, len(df))
        _write_summary_artifacts(df[keep])
    return df[keep]


def _write_summary_artifacts(df):
    latest_date = df["Date"].max()
    latest = df[df["Date"] == latest_date]
    summary_rows = []
    zones = {}
    for _, r in latest.iterrows():
        cwc_ok = r["cwc_available"] == "yes"
        stations = None if pd.isna(r.get("cwc_stations_in_cell", float("nan"))) \
            else int(r["cwc_stations_in_cell"])
        zones[r["Grid_ID"]] = {
            "date": str(r["Date"].date()),
            "risk_score": float(r["risk_score"]),
            "risk_level": r["risk_level"],
            "risk_trend": r["risk_trend"],
            "components": {
                "anomaly_score": float(r["ml_anomaly_score_0_100"]),
                "temporal_rainfall_signal": float(r["temporal_intensity"]),
                "vulnerability_score": float(r["vulnerability_score"]),
            },
            "data_status": ("IMD daily rainfall OK; CWC river level "
                            + (f"available ({stations} station(s) in cell)"
                               if cwc_ok else "UNAVAILABLE (missing, not zero)")),
            "mode": "HISTORICAL_REPLAY",
            "key_signals": json.loads(r["key_signals"]),
            "disclaimer": load_config()["disclaimer"],
        }
        summary_rows.append({
            "Grid_ID": r["Grid_ID"], "date": str(r["Date"].date()),
            "risk_score": r["risk_score"], "risk_level": r["risk_level"],
            "risk_trend": r["risk_trend"], "risk_delta_3d": r["risk_delta_3d"],
        })

    with open(os.path.join(OUT_DIR, "latest_zone_risk.json"), "w") as f:
        json.dump({"mode": "HISTORICAL_REPLAY",
                   "note": "Historical replay snapshot — NOT a live prediction",
                   "zones": zones}, f, indent=2, ensure_ascii=False)
    pd.DataFrame(summary_rows).to_csv(
        os.path.join(OUT_DIR, "risk_trend_summary.csv"), index=False)
    logger.info("summary artifacts written (latest date %s)", latest_date.date())


def get_live_risk(date, grid_id, risk_table=None):
    """Contract function. Uses ONLY information available on/before date."""
    if grid_id not in VALID_GRIDS:
        raise ValueError(f"unknown grid_id {grid_id!r}; expected one of {VALID_GRIDS}")
    try:
        ts = pd.Timestamp(date).normalize()
    except Exception as e:
        raise ValueError(f"unparseable date {date!r}") from e

    if risk_table is None:
        if not os.path.exists(RISK_CSV):
            build_risk_table()
        risk_table = pd.read_csv(RISK_CSV, parse_dates=["Date"])

    dmin, dmax = risk_table["Date"].min(), risk_table["Date"].max()
    if ts < dmin or ts > dmax:
        raise ValueError(f"date {ts.date()} outside scored range "
                         f"{dmin.date()}..{dmax.date()} (no live feed connected)")

    row = risk_table[(risk_table["Date"] == ts) & (risk_table["Grid_ID"] == grid_id)]
    if row.empty:
        raise KeyError(f"no risk row for {ts.date()} / {grid_id}")
    r = row.iloc[0]

    cwc_ok = r["cwc_available"] == "yes"
    stations = None if pd.isna(r.get("cwc_stations_in_cell", float("nan"))) \
        else int(r["cwc_stations_in_cell"])
    data_status = ("IMD daily rainfall OK; CWC river level "
                   + (f"available ({stations} station(s) in cell)"
                      if cwc_ok else
                      "UNAVAILABLE for this cell/date (reported as missing, not zero)"))

    return {
        "date": ts.strftime("%Y-%m-%d"),
        "grid_id": grid_id,
        "risk_score": float(r["risk_score"]),
        "risk_level": r["risk_level"],
        "risk_trend": (None if pd.isna(r["risk_trend"]) else r["risk_trend"]),
        "components": {
            "anomaly_score": float(r["ml_anomaly_score_0_100"]),
            "temporal_rainfall_signal": float(r["temporal_intensity"]),
            "vulnerability_score": float(r["vulnerability_score"]),
        },
        "data_status": data_status,
        "mode": "HISTORICAL_REPLAY",
        # additive, UI-friendly extras (not required by contract):
        "key_signals": json.loads(r["key_signals"]),
        "data_quality": {"cwc_available": cwc_ok,
                         "cwc_stations_in_cell": stations},
        "disclaimer": load_config()["disclaimer"],
    }


if __name__ == "__main__":
    build_risk_table()
