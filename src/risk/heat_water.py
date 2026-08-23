"""MODULE 4 — Heat + Water environmental risk (transparent proxies).

Independently computes:
  HEAT  : urban heat EXPOSURE PROXY from real ESA WorldCover fractions
          (no temperature telemetry exists -> explicitly a proxy)
  WATER : meteorological WATER DEFICIT PROXY comparing recent 30-day
          rainfall against the zone's prior-years climatology
          (no reservoir telemetry exists -> explicitly a proxy)

Deterministic, stdlib+pandas+numpy only, zero imports from other modules.
Scores are exposure/deficit indicators — NOT probabilities.
"""

import json
import logging
import os

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(_DIR, "heat_water_config.json")
DATASET_PATH = "data/processed/pune_ml_dataset.csv"
OUT_CSV = "outputs/risk/environmental_scores.csv"

VALID_GRIDS = ("PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _minmax(s):
    lo, hi = float(s.min()), float(s.max())
    if hi == lo:
        raise ValueError(f"constant factor {s.name}; relative index degenerate")
    return (s - lo) / (hi - lo) * 100.0


def _level(score, bands):
    for name, b in bands.items():
        if b["min"] <= score < b["max_exclusive"]:
            return name
    raise ValueError(f"{score} outside bands")


def compute_heat():
    cfg = load_config()["heat"]
    df = pd.read_csv(DATASET_PATH, usecols=["Grid_ID", "built_up_pct",
                                            "vegetation_pct"])
    f = df.groupby("Grid_ID").first()
    built_mm = _minmax(f["built_up_pct"])
    veg_inv = 100.0 - _minmax(f["vegetation_pct"])
    w_b = cfg["weights"]["built_up_higher_is_hotter"]["weight"]
    w_v = cfg["weights"]["vegetation_lower_is_hotter"]["weight"]
    score = (w_b * built_mm + w_v * veg_inv).round(2)

    out = pd.DataFrame({
        "Grid_ID": f.index,
        "heat_score": score.values,
        "heat_level": [_level(v, cfg["levels"]) for v in score.values],
        "heat_inputs": [json.dumps({"built_up_pct": round(float(r.built_up_pct), 2),
                                    "vegetation_pct": round(float(r.vegetation_pct), 2)})
                        for r in f.itertuples()],
    })
    return out


def build_water_table(dataset=None):
    cfg = load_config()["water"]
    if dataset is None:
        dataset = pd.read_csv(DATASET_PATH, usecols=[
            "Date", "Grid_ID", "rainfall_30d", "hist_mean_prior_years_mm"],
            parse_dates=["Date"])
    d = dataset.copy()
    d["expected_30d"] = 30.0 * d["hist_mean_prior_years_mm"]
    ratio = 1.0 - d["rainfall_30d"] / d["expected_30d"]
    d["water_deficit_ratio"] = ratio.clip(0.0, 1.0)

    has_baseline = d["hist_mean_prior_years_mm"].notna() & d["rainfall_30d"].notna()
    d.loc[has_baseline, "water_score"] = (
        d.loc[has_baseline, "water_deficit_ratio"] * 100.0).round(2)
    d["water_level"] = d["water_score"].apply(
        lambda v: None if pd.isna(v) else _level(v, cfg["levels"]))

    def explain(r):
        if pd.isna(r["water_score"]):
            return json.dumps(["insufficient history: no prior-year baseline "
                               "and/or incomplete 30-day window (left null)"])
        ratio = float(r["water_deficit_ratio"])
        if ratio <= 0.001:
            detail = "at or above climatology (surplus)"
        else:
            detail = f"deficit vs own climatology ({ratio*100:.0f}% of expected shortfall)"
        return json.dumps([f"rainfall_30d={r['rainfall_30d']:.1f} mm vs "
                           f"expected {r['expected_30d']:.1f} mm", detail])

    d["water_explanations"] = d.apply(explain, axis=1)
    return d[["Date", "Grid_ID", "water_deficit_ratio", "water_score",
              "water_level", "water_explanations"]]


def get_environmental_risk(date, grid_id):
    """Contract function. mode is always HISTORICAL_REPLAY."""
    if grid_id not in VALID_GRIDS:
        raise ValueError(f"unknown grid_id {grid_id!r}")
    try:
        ts = pd.Timestamp(date).normalize()
    except Exception as e:
        raise ValueError(f"unparseable date {date!r}") from e

    cfg = load_config()

    heat = compute_heat().set_index("Grid_ID")
    if grid_id not in heat.index:
        raise KeyError(grid_id)
    hrow = heat.loc[grid_id]

    water_path = OUT_CSV
    if not os.path.exists(water_path):
        build_water_table().to_csv(water_path, index=False)
    wtab = pd.read_csv(water_path, parse_dates=["Date"])
    wmin, wmax = wtab["Date"].min(), wtab["Date"].max()
    if ts < wmin or ts > wmax:
        raise ValueError(f"date {ts.date()} outside covered range "
                         f"{wmin.date()}..{wmax.date()} (no live feed)")
    wr = wtab[(wtab["Date"] == ts) & (wtab["Grid_ID"] == grid_id)]
    if wr.empty:
        raise KeyError(f"no environmental row for {ts.date()} / {grid_id}")
    w = wr.iloc[0]

    return {
        "date": ts.strftime("%Y-%m-%d"),
        "grid_id": grid_id,
        "heat": {
            "score": float(hrow["heat_score"]),
            "level": hrow["heat_level"],
            "type": cfg["heat"]["type"],
            "explanations": [
                "urban surface exposure from real WorldCover fractions "
                "(built-up up / vegetation down)",
                "static exposure proxy - temperature telemetry UNAVAILABLE",
            ],
        },
        "water": {
            "score": (None if pd.isna(w["water_score"]) else float(w["water_score"])),
            "level": (None if pd.isna(w["water_level"]) else w["water_level"]),
            "type": cfg["water"]["type"],
            "explanations": json.loads(w["water_explanations"]),
        },
        "data_status": dict(cfg["telemetry_status"]),
        "mode": cfg["mode"],
        "disclaimer": cfg["disclaimer"],
    }


if __name__ == "__main__":
    t = build_water_table()
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    t.to_csv(OUT_CSV, index=False)
    logger.info("environmental table -> %s (%d rows)", OUT_CSV, len(t))
    print(get_environmental_risk("2024-05-15", "PUNE_G003"))
