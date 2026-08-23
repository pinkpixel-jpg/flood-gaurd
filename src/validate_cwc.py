import logging
import os

import numpy as np
import pandas as pd
from shapely.geometry import Point, box
from pyproj import Geod

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = 73.60, 18.30, 74.10, 18.75
STUDY_BOX = box(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)
CWC_CSV = "hehehackathon/rwl_tel_hr_maharashtra_sw_007_2021_2025 (1).csv"
OUT_CSV = "reports/cwc_station_validation.csv"
RELEVANCE_KM = 15.0
geod = Geod(ellps="WGS84")


def distance_km_to_box(lon, lat):
    p = Point(lon, lat)
    if STUDY_BOX.contains(p) or STUDY_BOX.touches(p):
        return 0.0
    min_d = None
    for lon2, lat2 in list(STUDY_BOX.exterior.coords):
        _, _, d = geod.inv(lon, lat, lon2, lat2)
        min_d = d if min_d is None else min(min_d, d)
    return min_d / 1000.0


def main():
    logger.info("Loading CWC telemetry file (large): %s", CWC_CSV)
    usecols = ["Station", "River", "Basin", "District", "Tehsil",
               "Latitude", "Longitude", "Data Acquisition Time",
               "River Water Level Telemetry Hourly (meter)", "RL_of_zeroGauge"]
    df = pd.read_csv(CWC_CSV, usecols=usecols, encoding="cp1252", low_memory=False)
    level_col = "River Water Level Telemetry Hourly (meter)"
    time_col = "Data Acquisition Time"
    df[time_col] = pd.to_datetime(df[time_col], format="%d-%m-%Y %H:%M", errors="coerce")

    g = df.groupby("Station")
    rows = []
    for st, sub in g:
        lat = sub["Latitude"].iloc[0]
        lon = sub["Longitude"].iloc[0]
        t = sub[time_col]
        lv = pd.to_numeric(sub[level_col], errors="coerce")
        rows.append({
            "station": st,
            "river": str(sub["River"].iloc[0]).strip(),
            "basin": str(sub["Basin"].iloc[0]).strip(),
            "district": str(sub["District"].iloc[0]).strip(),
            "tehsil": str(sub["Tehsil"].iloc[0]).strip(),
            "latitude": float(lat),
            "longitude": float(lon),
            "n_records": int(len(sub)),
            "time_start": t.min(),
            "time_end": t.max(),
            "level_min_m": float(lv.min()),
            "level_max_m": float(lv.max()),
            "level_mean_m": round(float(lv.mean()), 3),
            "gauge_zero_rl_m": float(sub["RL_of_zeroGauge"].iloc[0]),
            "distance_to_study_area_km": round(distance_km_to_box(lon, lat), 2),
        })

    out = pd.DataFrame(rows).sort_values("distance_to_study_area_km")
    out["relevant"] = np.where(out["distance_to_study_area_km"] <= RELEVANCE_KM, "YES", "NO")
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    print()
    print("CWC STATION VALIDATION (sorted by distance to Pune study area)")
    print("=" * 100)
    cols = ["station", "river", "district", "latitude", "longitude", "n_records",
            "time_start", "time_end", "distance_to_study_area_km", "relevant"]
    print(out[cols].to_string(index=False))
    print()
    rel = out[out["relevant"] == "YES"]
    print(f"stations total={len(out)} | relevant (<={RELEVANCE_KM} km)={len(rel)}")
    if len(rel):
        print(rel[["station", "river", "distance_to_study_area_km"]].to_string(index=False))
    units_note = f"{level_col} [meter]; timestamps {t.min()}..{t.max()}"
    logger.info("saved -> %s | %s", OUT_CSV, units_note)


if __name__ == "__main__":
    main()
