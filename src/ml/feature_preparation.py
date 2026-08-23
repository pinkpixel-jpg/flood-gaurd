import logging
import os

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATASET_PATH = "data/processed/pune_ml_dataset.csv"

DYNAMIC_FEATURES = [
    "rainfall_1d", "rainfall_3d", "rainfall_7d", "rainfall_14d", "rainfall_30d",
    "rainfall_anomaly_mm",
    "monthly_rainfall_to_date", "monsoon_rainfall_to_date",
    "river_level_daily_mean_m", "river_level_daily_max_m",
]

STATIC_FEATURES = [
    "elevation_mean_m", "elevation_min_m", "elevation_max_m",
    "slope_mean_deg", "slope_min_deg", "slope_max_deg",
    "built_up_pct", "vegetation_pct", "water_cover_pct",
    "distance_to_nearest_waterway_m", "waterway_length_m",
    "distance_to_nearest_drainage_m", "drainage_length_m",
]

FORBIDDEN_FEATURES = {"flood_event_active", "road_density"}

TRAIN_START, TRAIN_END = "2015-01-01", "2023-12-31"
EVAL_START, EVAL_END = "2024-01-01", "2025-12-31"
EVENT_EXCLUSION_BUFFER_DAYS = 3

MISSING_POLICY = {
    "monsoon_rainfall_to_date": "fill_zero_outside_season (Jan-May: 0 mm monsoon accumulation is physically true by definition)",
    "river_level_daily_mean_m": "indicator + training-period median (CWC absent before Feb-2022; zero metres is a REAL level so never fill with 0)",
    "river_level_daily_max_m": "indicator + training-period median",
    "rainfall_anomaly_mm / hist-dependent": "training-period median for 2015 rows (no prior-year baseline exists)",
    "rolling rainfall edge NaNs": "training-period median (window-incomplete start-of-series only)",
}


def load_dataset():
    df = pd.read_csv(DATASET_PATH, parse_dates=["Date"])
    assert not df.duplicated(["Date", "Grid_ID"]).any(), "duplicate Date+Grid_ID"
    assert len(df) == 16072, f"unexpected row count {len(df)}"
    logger.info("dataset loaded: %d rows x %d cols | %s .. %s",
                *df.shape, df["Date"].min().date(), df["Date"].max().date())
    return df


def build_features(df):
    feat = pd.DataFrame(index=df.index)
    for c in DYNAMIC_FEATURES[:-2]:
        feat[c] = df[c]

    mon = df["monsoon_rainfall_to_date"]
    outside_season = mon.isna() & (df["month"] < 6)
    feat["monsoon_rainfall_to_date"] = mon.fillna(outside_season.map({True: 0.0, False: np.nan}))

    lvl_avail = df["river_level_daily_mean_m"].notna() & df["river_level_daily_max_m"].notna()
    feat["river_level_available"] = lvl_avail.astype(float)
    feat["river_level_daily_mean_m"] = df["river_level_daily_mean_m"]
    feat["river_level_daily_max_m"] = df["river_level_daily_max_m"]

    for c in STATIC_FEATURES:
        feat[c] = df[c]

    forbidden = FORBIDDEN_FEATURES.intersection(feat.columns)
    assert not forbidden, f"forbidden features present: {forbidden}"

    inf_cols = [c for c in feat.columns if np.isinf(feat[c].to_numpy(dtype="float64", na_value=np.nan)).any()]
    assert not inf_cols, f"infinite values in {inf_cols}"
    return feat


def apply_training_medians(feat, train_mask):
    medians = {}
    out = feat.copy()
    for c in feat.columns:
        na = out[c].isna()
        if not na.any():
            continue
        m = out.loc[train_mask & ~na, c].median()
        if np.isnan(m):
            raise ValueError(f"column {c} has no computable training median")
        out.loc[na, c] = m
        medians[c] = float(m)
    assert not out.isna().any().any(), "NaNs remain after imputation"
    return out, medians


def event_exclusion_mask(df):
    ev = df[df["flood_event_active"] == 1]
    keep = pd.Series(True, index=df.index)
    n_excl = 0
    for d in ev["Date"].unique():
        lo = d - pd.Timedelta(days=EVENT_EXCLUSION_BUFFER_DAYS)
        hi = d + pd.Timedelta(days=EVENT_EXCLUSION_BUFFER_DAYS)
        hit = (df["Date"] >= lo) & (df["Date"] <= hi)
        keep &= ~hit
        n_excl += int(hit.sum())
    logger.info("event-exclusion (+/-%dd): %d train rows excluded around %d event-days",
                EVENT_EXCLUSION_BUFFER_DAYS, n_excl, ev["Date"].nunique())
    return keep


def prepare():
    df = load_dataset()
    raw_feat = build_features(df)

    date = df["Date"]
    train_mask = (date >= TRAIN_START) & (date <= TRAIN_END)
    eval_mask = (date >= EVAL_START) & (date <= EVAL_END)
    fit_mask = train_mask & event_exclusion_mask(df)

    feat, medians = apply_training_medians(raw_feat, fit_mask)

    meta = {
        "n_rows": int(len(df)),
        "features": list(feat.columns),
        "dynamic_features": DYNAMIC_FEATURES,
        "static_features": STATIC_FEATURES,
        "derived_indicators": ["river_level_available"],
        "forbidden_features_verified_absent": sorted(FORBIDDEN_FEATURES),
        "missing_policy": MISSING_POLICY,
        "imputation_medians_train_fit": medians,
        "train_period": [TRAIN_START, TRAIN_END],
        "eval_period": [EVAL_START, EVAL_END],
        "fit_rows_after_event_exclusion": int(fit_mask.sum()),
    }
    logger.info("feature matrix ready: %d cols | fit rows=%d | train=%d | eval=%d",
                feat.shape[1], fit_mask.sum(), train_mask.sum(), eval_mask.sum())
    return df, feat, train_mask, eval_mask, fit_mask, meta


if __name__ == "__main__":
    prepare()
