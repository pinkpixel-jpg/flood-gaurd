import json
import logging
import os

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = 73.60, 18.30, 74.10, 18.75

CELLS = {
    "PUNE_G001": (18.50, 73.75),
    "PUNE_G002": (18.50, 74.00),
    "PUNE_G003": (18.75, 73.75),
    "PUNE_G004": (18.75, 74.00),
}
CELL_HALF = 0.125

RAINFALL_CSV = "data/processed/pune/pune_spatial_rainfall_2015_2025.csv"
STATIC_CSV = "data/processed/pune_static_cell_features.csv"
FLOOD_CSV = "data/flood_events/pune_flood_events.csv"
CWC_CSV = "hehehackathon/rwl_tel_hr_maharashtra_sw_007_2021_2025 (1).csv"
CWC_DAILY_OUT = "data/processed/pune_cwc_daily.csv"
OUT_CSV = "data/processed/pune_ml_dataset.csv"
VALIDATION_TXT = "reports/ml_dataset_validation.txt"

ROLL_WINDOWS = [3, 7, 14, 30]
LEVEL_COL = "River Water Level Telemetry Hourly (meter)"
TIME_COL = "Data Acquisition Time"

report_lines = []


def rep(s=""):
    print(s)
    report_lines.append(str(s))


def load_rainfall():
    df = pd.read_csv(RAINFALL_CSV, parse_dates=["Date"])
    df = df.drop(columns=[c for c in ["Year", "Month", "Day", "DayOfYear"] if c in df.columns])
    assert not df.duplicated(["Grid_ID", "Date"]).any(), "duplicate Grid_ID+Date in source"
    return df.sort_values(["Grid_ID", "Date"]).reset_index(drop=True)


def add_rainfall_features(df):
    g = df.groupby("Grid_ID", group_keys=False)["Rainfall_mm"]
    for w in ROLL_WINDOWS:
        df[f"rainfall_{w}d"] = g.apply(lambda s, w=w: s.rolling(w, min_periods=w).sum())
    df["rainfall_1d"] = df["Rainfall_mm"]

    df["monthly_rainfall_to_date"] = df.groupby(
        ["Grid_ID", df["Date"].dt.year, df["Date"].dt.month])["Rainfall_mm"].cumsum()

    def monsoon_cum(s):
        dts = df.loc[s.index, "Date"]
        y = dts.dt.year
        doy_since_jun = (dts - pd.to_datetime(y.astype(str) + "-06-01")).dt.days
        vals = s.where(doy_since_jun >= 0)
        out = vals.groupby(y).cumsum()
        out[doy_since_jun < 0] = np.nan
        return out

    df["monsoon_rainfall_to_date"] = df.groupby("Grid_ID", group_keys=False)["Rainfall_mm"].apply(monsoon_cum)

    df["year"] = df["Date"].dt.year
    df["month"] = df["Date"].dt.month
    pm = df.groupby(["Grid_ID", "year"])["Rainfall_mm"].agg(["mean", "max"]).reset_index()
    pm[["mean", "max"]] = pm.groupby("Grid_ID")[["mean", "max"]].shift(1)
    pm = pm.rename(columns={"mean": "_m", "max": "_x"})
    df = df.merge(pm, on=["Grid_ID", "year"], how="left")
    df = df.rename(columns={"_m": "hist_mean_prior_years_mm", "_x": "hist_max_prior_years_mm"})
    df = df.drop(columns=["year"])
    df["year"] = df["Date"].dt.year

    mc = df.groupby(["Grid_ID", "month", "year"])["Rainfall_mm"].mean().reset_index()
    mc = mc.sort_values(["Grid_ID", "month", "year"])
    mc[["_mc"]] = mc.groupby(["Grid_ID", "month"])[["Rainfall_mm"]].shift(1)
    df = df.merge(mc.drop(columns=["Rainfall_mm"]), on=["Grid_ID", "month", "year"], how="left")
    df = df.rename(columns={"_mc": "month_clim_mean_prior_years_mm"})
    df["rainfall_anomaly_mm"] = df["rainfall_1d"] - df["hist_mean_prior_years_mm"]

    df["is_monsoon"] = df["month"].isin([6, 7, 8, 9]).astype(int)
    return df


def add_calendar(df):
    df["month"] = df["Date"].dt.month
    df["day"] = df["Date"].dt.day
    df["dayofyear"] = df["Date"].dt.dayofyear
    return df


def add_static_features(df):
    st = pd.read_csv(STATIC_CSV)
    drop_cols = {"Latitude", "Longitude"}
    st_join = st.drop(columns=[c for c in drop_cols if c in st.columns])
    df = df.merge(st_join, on="Grid_ID", how="left")
    lat_map = dict(zip(st["Grid_ID"], st["Latitude"]))
    lon_map = dict(zip(st["Grid_ID"], st["Longitude"]))
    df["Latitude"] = df["Grid_ID"].map(lat_map)
    df["Longitude"] = df["Grid_ID"].map(lon_map)
    return df


def build_cwc_daily(cell_polys):
    if not os.path.exists(CWC_CSV):
        logger.warning("CWC file missing -> no CWC features")
        return pd.DataFrame(), pd.DataFrame()
    usecols = ["Station", "Latitude", "Longitude", TIME_COL, LEVEL_COL]
    raw = pd.read_csv(CWC_CSV, usecols=usecols, encoding="cp1252", low_memory=False)
    raw[TIME_COL] = pd.to_datetime(raw[TIME_COL], format="%d-%m-%Y %H:%M", errors="coerce")
    raw = raw.dropna(subset=[TIME_COL])
    raw["level"] = pd.to_numeric(raw[LEVEL_COL], errors="coerce")

    st_meta = raw.groupby("Station").first()[["Latitude", "Longitude"]].reset_index()
    st_meta["grid_id"] = None
    for i, r in st_meta.iterrows():
        pt = Point(r["Longitude"], r["Latitude"])
        for gid, poly in cell_polys.items():
            if poly.contains(pt):
                st_meta.at[i, "grid_id"] = gid
                break
    in_cell = st_meta.dropna(subset=["grid_id"])
    logger.info("stations inside study cells: %s",
                in_cell[["Station", "grid_id"]].to_dict("records"))

    sub = raw.merge(in_cell[["Station", "grid_id"]], on="Station", how="inner")
    sub["date"] = sub[TIME_COL].dt.normalize()
    daily = (sub.groupby(["grid_id", "Station", "date"])
             .agg(level_daily_mean_m=("level", "mean"),
                  level_daily_max_m=("level", "max"),
                  n_obs=("level", "size"))
             .round(3).reset_index())
    daily.to_csv(CWC_DAILY_OUT, index=False)
    logger.info("saved %s (%d station-days)", CWC_DAILY_OUT, len(daily))

    cell_day = (daily.groupby(["grid_id", "date"])
                .agg(river_level_daily_mean_m=("level_daily_mean_m", "mean"),
                     river_level_daily_max_m=("level_daily_max_m", "max"))
                .round(3).reset_index()
                .rename(columns={"grid_id": "Grid_ID", "date": "Date"}))
    n_st = in_cell.groupby("grid_id")["Station"].nunique()
    cell_day["cwc_stations_in_cell"] = cell_day["Grid_ID"].map(n_st)
    return cell_day, in_cell


def add_flood_labels(df, cell_polys):
    fdf = pd.read_csv(FLOOD_CSV)
    df["flood_event_active"] = 0
    mapped = []
    for _, ev in fdf.iterrows():
        pt = Point(float(ev["longitude"]), float(ev["latitude"]))
        gid_hit = None
        for gid, poly in cell_polys.items():
            if poly.contains(pt):
                gid_hit = gid
                break
        start = pd.Timestamp(ev["start_date"])
        end = pd.Timestamp(ev["end_date"])
        if gid_hit is not None:
            mask = (df["Grid_ID"] == gid_hit) & (df["Date"] >= start) & (df["Date"] <= end)
            n = int(mask.sum())
            df.loc[mask, "flood_event_active"] = 1
            mapped.append({"event_id": int(ev["event_id"]), "grid": gid_hit,
                           "start": str(start.date()), "end": str(end.date()),
                           "rows_labelled_in_dataset": n,
                           "within_rainfall_window": bool(n > 0)})
    rep("")
    rep("FLOOD LABEL MAPPING (verified events only):")
    for m in mapped:
        rep(f"  event {m['event_id']}: {m['start']}..{m['end']} -> {m['grid']} | "
            f"rows labelled={m['rows_labelled_in_dataset']}")
    return df, mapped


def validate(df):
    rep("=" * 70)
    rep("FINAL DATASET VALIDATION")
    rep("=" * 70)
    rep(f"path                 : {OUT_CSV}")
    rep(f"rows x cols          : {df.shape[0]} x {df.shape[1]}")
    rep(f"date range           : {df['Date'].min().date()} .. {df['Date'].max().date()}")
    rep(f"distinct dates       : {df['Date'].nunique()} (expected 4018)")
    rep(f"cells                : {df['Grid_ID'].nunique()} -> "
        f"{df.groupby('Grid_ID').size().to_dict()}")
    dup = int(df.duplicated(['Date', 'Grid_ID']).sum())
    rep(f"duplicate Date+Grid  : {dup}")

    expected = {(d, g) for d in df['Date'].unique() for g in CELLS}
    actual = set(map(tuple, df[['Date', 'Grid_ID']].drop_duplicates().values))
    rep(f"complete 4018x4 grid : {len(actual)} combos present | missing={len(expected - actual)}")

    inf_num = int(np.isinf(df.select_dtypes(include=[np.number]).fillna(0)).sum().sum())
    rep(f"infinite values      : {inf_num}")
    neg = {c: int((df[c] < 0).sum()) for c in
           ["rainfall_1d", "rainfall_3d", "rainfall_7d", "rainfall_14d", "rainfall_30d"]}
    rep(f"negative rainfall    : {neg}")

    miss = df.isna().sum()
    miss = miss[miss > 0].sort_values(ascending=False)
    rep("")
    rep("MISSING VALUES PER COLUMN:")
    for c, v in miss.items():
        rep(f"  {c:38s} {v:>6} ({100*v/len(df):.1f}%)")

    num_cols = df.select_dtypes(include=[np.number]).columns
    rep("")
    rep("NUMERIC RANGES:")
    for c in num_cols:
        s = df[c]
        if s.notna().any():
            rep(f"  {c:38s} min={s.min():>12.3f} max={s.max():>12.3f} mean={s.mean():>10.3f}")

    rep("")
    rep("WATERWAY/DRAINAGE FEATURES (per cell, joined):")
    wf = df.groupby("Grid_ID")[["distance_to_nearest_waterway_m", "waterway_length_m",
                                "distance_to_nearest_drainage_m", "drainage_length_m"]].first()
    rep(wf.to_string())
    rep("")
    rep(f"road_density unique values     : {df['road_density'].unique().tolist()} "
        f"(status={df['osm_road_status'].iloc[0]})")
    rep(f"CWC river-level coverage rows  : {int(df['river_level_daily_mean_m'].notna().sum())} "
        f"/ {len(df)} ({100*df['river_level_daily_mean_m'].notna().mean():.1f}%)")
    rep(f"flood_event_active positives   : {int(df['flood_event_active'].sum())}")


def main():
    logger.info("=" * 70)
    logger.info("BUILD SPATIOTEMPORAL ML DATASET (no training)")
    logger.info("=" * 70)

    rain = load_rainfall()
    logger.info("rainfall loaded: %d rows", len(rain))

    df = add_rainfall_features(rain)
    df = add_calendar(df)

    df = add_static_features(df)

    cell_polys = {}
    for gid, (lat, lon) in CELLS.items():
        b = box(lon - CELL_HALF, lat - CELL_HALF, lon + CELL_HALF, lat + CELL_HALF)
        cell_polys[gid] = b.intersection(box(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT))
    cwc_cell_day, cwc_stations = build_cwc_daily(cell_polys)
    if len(cwc_cell_day):
        df = df.merge(cwc_cell_day, on=["Grid_ID", "Date"], how="left")
    else:
        df["river_level_daily_mean_m"] = np.nan
        df["river_level_daily_max_m"] = np.nan
        df["cwc_stations_in_cell"] = np.nan

    df, flood_map = add_flood_labels(df, cell_polys)

    front = ["Date", "Grid_ID", "Latitude", "Longitude"]
    ordered = ([c for c in front if c in df.columns]
               + [c for c in df.columns if c not in front and c != "Rainfall_mm"])
    df = df[ordered].sort_values(["Grid_ID", "Date"]).reset_index(drop=True)

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    logger.info("saved %s (%d rows x %d cols)", OUT_CSV, df.shape[0], df.shape[1])

    validate(df)
    with open(VALIDATION_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    logger.info("validation report saved -> %s", VALIDATION_TXT)


if __name__ == "__main__":
    main()
