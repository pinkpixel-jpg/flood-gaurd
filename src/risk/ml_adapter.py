"""ML ADAPTER — the ONLY sanctioned way to consume ML anomaly results.

Reads the frozen Isolation-Forest output (outputs/ml/anomaly_scores.csv)
and exposes one clean function:

    get_ml_result(date, grid_id) -> dict

Contract (docs/RISK_ENGINE_CONTRACT.md):
    {
        "date": "YYYY-MM-DD",
        "grid_id": "PUNE_G00x",
        "ml_anomaly_score": float 0-100,
        "anomaly_percentile": int 0-100
    }

This adapter does NOT compute rule scores, final risk, alerts,
ViaSocket calls, or modify the model in any way.
"""

import os
from datetime import date as _date, datetime

import pandas as pd

SCORES_PATH = os.path.join("outputs", "ml", "anomaly_scores.csv")

VALID_GRID_IDS = ("PUNE_G001", "PUNE_G002", "PUNE_G003", "PUNE_G004")

_cache = {"df": None, "mtime": None}


def _load():
    mtime = os.path.getmtime(SCORES_PATH)
    if _cache["df"] is None or _cache["mtime"] != mtime:
        df = pd.read_csv(SCORES_PATH, usecols=["Date", "Grid_ID",
                                               "ml_anomaly_score_0_100",
                                               "anomaly_percentile"])
        df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
        _cache["df"] = df.set_index(["Date", "Grid_ID"]).sort_index()
        _cache["mtime"] = mtime
    return _cache["df"]


def get_ml_result(date, grid_id):
    """Return the frozen ML anomaly result for one date x grid cell.

    `date` accepts 'YYYY-MM-DD', datetime.date, or pandas Timestamp.
    Raises ValueError for invalid grid/date; KeyError if not scored.
    """
    if grid_id not in VALID_GRID_IDS:
        raise ValueError(f"unknown grid_id {grid_id!r}; expected one of {VALID_GRID_IDS}")

    if isinstance(date, str):
        try:
            ts = pd.Timestamp(date)
        except Exception as e:
            raise ValueError(f"unparseable date {date!r}") from e
    elif isinstance(date, (_date, datetime, pd.Timestamp)):
        ts = pd.Timestamp(date)
    else:
        raise ValueError(f"unsupported date type {type(date).__name__}")
    ts = ts.normalize()

    idx = _load()
    key = (ts, grid_id)
    if key not in idx.index:
        raise KeyError(f"no ML score for {ts.date()} / {grid_id} "
                       f"(scored range 2015-01-01..2025-12-31)")

    row = idx.loc[key]
    return {
        "date": ts.strftime("%Y-%m-%d"),
        "grid_id": grid_id,
        "ml_anomaly_score": float(row["ml_anomaly_score_0_100"]),
        "anomaly_percentile": int(row["anomaly_percentile"]),
    }
