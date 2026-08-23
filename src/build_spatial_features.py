import json
import logging
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rio_mask
from shapely.geometry import Point, box

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = 73.60, 18.30, 74.10, 18.75
STUDY_BOX = box(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)
PROJ_CRS = "EPSG:32643"

CELLS = {
    "PUNE_G001": (18.50, 73.75),
    "PUNE_G002": (18.50, 74.00),
    "PUNE_G003": (18.75, 73.75),
    "PUNE_G004": (18.75, 74.00),
}
CELL_HALF = 0.125

ELEV_TIF = "data/processed/pune_elevation.tif"
SLOPE_TIF = "data/processed/pune_slope.tif"
LANDCOVER_TIF = "data/processed/pune_landcover.tif"

WATERWAYS_RAW = "data/raw/osm/pune_waterways_raw.geojson"
WATERWAYS_OUT = "data/processed/pune_waterways.geojson"
DRAINAGE_OUT = "data/processed/pune_drainage.geojson"

FLOOD_CSV = "data/flood_events/pune_flood_events.csv"
OSM_STATUS_JSON = "data/processed/osm_status.json"

STATIC_OUT = "data/processed/pune_static_cell_features.csv"
SPATIAL_SUMMARY_OUT = "data/processed/pune_spatial_features.csv"

WATERWAY_CLASSES = ["river", "stream", "canal"]
DRAINAGE_CLASSES = ["drain", "ditch"]

WC_BUILT_UP = 50
WC_VEGETATION = [10, 20, 30]
WC_WATER = 80
WC_CROPLAND = 40
WC_NODATA = 0


def resplit_osm_categories():
    if not os.path.exists(WATERWAYS_RAW):
        raise FileNotFoundError(WATERWAYS_RAW)
    g = gpd.read_file(WATERWAYS_RAW)
    keep = [c for c in ("name", "waterway", "geometry") if c in g.columns]
    g = g[keep]
    g = g[~(g.geometry.isna() | g.geometry.is_empty)]
    g = g[g.geom_type.isin(["LineString", "MultiLineString"])]
    if g.crs != "EPSG:4326":
        g = g.to_crs("EPSG:4326")

    wat = g[g["waterway"].isin(WATERWAY_CLASSES)].reset_index(drop=True)
    drn = g[g["waterway"].isin(DRAINAGE_CLASSES)].reset_index(drop=True)
    wat.to_file(WATERWAYS_OUT, driver="GeoJSON")
    drn.to_file(DRAINAGE_OUT, driver="GeoJSON")
    logger.info("re-split OK -> %s (%d river/stream/canal), %s (%d drain/ditch)",
                WATERWAYS_OUT, len(wat), DRAINAGE_OUT, len(drn))
    return wat, drn


def raster_cell_stats(tif_path, geom_wgs84):
    with rasterio.open(tif_path) as src:
        img, _ = rio_mask(src, [geom_wgs84], crop=True, nodata=src.nodata)
        arr = img[0].astype("float64")
        nod = src.nodata
    m = np.isfinite(arr)
    if nod is not None:
        m &= (arr != nod)
    v = arr[m]
    if v.size == 0:
        return float("nan"), float("nan"), float("nan"), 0
    return float(v.mean()), float(v.min()), float(v.max()), int(v.size)


def landcover_cell_stats(geom_wgs84):
    with rasterio.open(LANDCOVER_TIF) as src:
        img, _ = rio_mask(src, [geom_wgs84], crop=True, nodata=WC_NODATA)
        arr = img[0]
    valid = arr[arr != WC_NODATA]
    n = int(valid.size)
    if n == 0:
        return {"built_up_pct": np.nan, "vegetation_pct": np.nan,
                "water_cover_pct": np.nan, "cropland_pct": np.nan,
                "lc_valid_px": 0, "lc_class_counts": {}}
    u, c = np.unique(valid.astype(int), return_counts=True)
    counts = dict(zip(u.tolist(), c.tolist()))

    def pct(k):
        return round(100.0 * counts.get(k, 0) / n, 4)

    stats = {
        "built_up_pct": pct(WC_BUILT_UP),
        "vegetation_pct": round(sum(counts.get(k, 0) for k in WC_VEGETATION) * 100.0 / n, 4),
        "water_cover_pct": pct(WC_WATER),
        "cropland_pct": pct(WC_CROPLAND),
        "lc_valid_px": n,
    }
    return stats, counts


def vector_features(lines_wgs, cell_geom_wgs, center_pt_proj, kind):
    dist_key = f"distance_to_nearest_{kind}_m"
    len_key = f"{kind}_length_m"
    if lines_wgs is None or len(lines_wgs) == 0:
        logger.warning("[%s] layer EMPTY/missing -> features stay NaN", kind)
        return {dist_key: np.nan, len_key: np.nan}
    lp = lines_wgs.to_crs(PROJ_CRS)
    d = float(lp.distance(center_pt_proj).min())
    cp_mask = lp.intersects(cell_geom_wgs)
    n_intersect = int(cp_mask.sum())
    cp = lp[cp_mask]
    clipped = cp.intersection(cell_geom_wgs) if n_intersect else cp
    total_len = float(clipped.length.sum()) if n_intersect else 0.0
    logger.info("[%s] %d/%d lines intersect cell | nearest=%.1f m | length_in_cell=%.1f m",
                kind, n_intersect, len(lp), d, total_len)
    return {dist_key: round(d, 2), len_key: round(total_len, 2)}


def load_flood_counts(cell_polys):
    counts = {k: 0 for k in cell_polys}
    events = []
    if not os.path.exists(FLOOD_CSV):
        logger.warning("flood events csv missing: %s", FLOOD_CSV)
        return counts, events
    fdf = pd.read_csv(FLOOD_CSV)
    for _, r in fdf.iterrows():
        pt = Point(float(r["longitude"]), float(r["latitude"]))
        hit = None
        for gid, poly in cell_polys.items():
            if poly.contains(pt):
                hit = gid
                break
        if hit:
            counts[hit] += 1
        events.append({"event_id": r.get("event_id"), "date": r.get("start_date"),
                       "grid_id": hit})
    return counts, events


def main():
    logger.info("=" * 70)
    logger.info("STATIC PER-CELL GIS FEATURE EXTRACTION (real data only)")
    logger.info("=" * 70)

    with open(OSM_STATUS_JSON) as f:
        osm_status = json.load(f)
    road_status = osm_status.get("roads", "UNKNOWN")
    logger.info("OSM road status: %s", road_status)

    water_gdf, drain_gdf = resplit_osm_categories()

    cell_polys_eff = {}
    cell_polys_proj = {}
    cell_centers_proj = {}
    for gid, (lat, lon) in CELLS.items():
        raw = box(lon - CELL_HALF, lat - CELL_HALF, lon + CELL_HALF, lat + CELL_HALF)
        eff = raw.intersection(STUDY_BOX)
        cell_polys_eff[gid] = eff
        gs = gpd.GeoSeries([eff], crs="EPSG:4326").to_crs(PROJ_CRS)
        cell_polys_proj[gid] = gs.values[0]
        gdf_c = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326").to_crs(PROJ_CRS)
        cell_centers_proj[gid] = gdf_c.geometry.values[0]

    flood_counts, flood_events = load_flood_counts(cell_polys_eff)

    rows = []
    lc_report = {}
    for gid, (lat, lon) in CELLS.items():
        eff_poly = cell_polys_eff[gid]
        logger.info("--- %s ---", gid)

        e_mean, e_min, e_max, e_px = raster_cell_stats(ELEV_TIF, eff_poly)
        s_mean, s_min, s_max, s_px = raster_cell_stats(SLOPE_TIF, eff_poly)
        lc, counts = landcover_cell_stats(eff_poly)
        lc_report[gid] = counts

        wfeat = vector_features(water_gdf, cell_polys_proj[gid], cell_centers_proj[gid], "waterway")
        dfeat = vector_features(drain_gdf, cell_polys_proj[gid], cell_centers_proj[gid], "drainage")

        rows.append({
            "Grid_ID": gid,
            "Latitude": lat,
            "Longitude": lon,
            "elevation_mean_m": round(e_mean, 2),
            "elevation_min_m": round(e_min, 2),
            "elevation_max_m": round(e_max, 2),
            "elevation_valid_px": e_px,
            "slope_mean_deg": round(s_mean, 4),
            "slope_min_deg": round(s_min, 4),
            "slope_max_deg": round(s_max, 4),
            "slope_valid_px": s_px,
            **lc,
            **wfeat,
            **dfeat,
            "road_density": np.nan,
            "osm_road_status": road_status,
            "flood_event_count_verified": flood_counts[gid],
        })

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(STATIC_OUT), exist_ok=True)
    df.to_csv(STATIC_OUT, index=False)
    df.to_csv(SPATIAL_SUMMARY_OUT, index=False)
    logger.info("static features saved -> %s", STATIC_OUT)
    logger.info("spatial summary refreshed -> %s", SPATIAL_SUMMARY_OUT)

    print()
    print(df.drop(columns=["elevation_valid_px", "slope_valid_px"]).to_string(index=False))
    print()
    for gid, cc in lc_report.items():
        logger.info("WorldCover class pixel counts %s: %s", gid, cc)
    logger.info("verified flood events mapped to cells: %s", flood_events)


if __name__ == "__main__":
    main()
