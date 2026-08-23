import os
import logging

import numpy as np
import rasterio
from rasterio.merge import merge as rio_merge
from rasterio.mask import mask as rio_mask
from rasterio.windows import from_bounds
from shapely.geometry import box
from pyproj import Geod

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = 73.60, 18.30, 74.10, 18.75
STUDY_BOX = box(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)

SRTM_DIR = os.path.join("hehehackathon", "IHSA6_GIS")
TILE_NAMES = ["N18E073.tif", "N18E074.tif"]

FULL_ELEV_OUT = os.path.join(SRTM_DIR, "pune_elevation_full.tif")
FULL_SLOPE_OUT = os.path.join(SRTM_DIR, "pune_slope_full.tif")
PROC_ELEV_OUT = os.path.join("data", "processed", "pune_elevation.tif")
PROC_SLOPE_OUT = os.path.join("data", "processed", "pune_slope.tif")

ELEV_NODATA = -32768
SLOPE_NODATA = -9999.0


def merge_tiles(tile_paths, dst_path):
    logger.info("Opening %d SRTM tiles: %s", len(tile_paths), [os.path.basename(p) for p in tile_paths])
    srcs = [rasterio.open(p) for p in tile_paths]
    try:
        for s in srcs:
            logger.info("  %s | crs=%s res=%.8f,%0.8f bounds=%s",
                        os.path.basename(s.name), s.crs, s.res[0], s.res[1],
                        tuple(round(b, 6) for b in s.bounds))
        mosaic, transform = rio_merge(srcs, method="first", nodata=ELEV_NODATA)
        profile = srcs[0].profile.copy()
    finally:
        for s in srcs:
            s.close()

    height, width = mosaic.shape[1], mosaic.shape[2]
    profile.update(driver="GTiff", height=height, width=width,
                   transform=transform, count=1, dtype="int16",
                   nodata=ELEV_NODATA, compress="deflate")

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with rasterio.open(dst_path, "w", **profile) as dst:
        dst.write(mosaic.astype("int16"))

    bounds = rasterio.transform.array_bounds(height, width, transform)
    logger.info("Merged DEM written: %s (%dx%d)", dst_path, width, height)
    return bounds


def verify_coverage(path_or_bounds, min_lon, min_lat, max_lon, max_lat, label):
    if isinstance(path_or_bounds, str):
        with rasterio.open(path_or_bounds) as src:
            b = src.bounds
            res = src.res
            crs = src.crs
    else:
        left, bottom, right, top = path_or_bounds
        b = rasterio.coords.BoundingBox(left, bottom, right, top)
        res = (None, None)
        crs = None
    covers = (b.left <= min_lon and b.bottom <= min_lat and b.right >= max_lon and b.top >= max_lat)
    logger.info("[%s] bounds=(%.6f, %.6f, %.6f, %.6f) covers study bbox: %s",
                label, b.left, b.bottom, b.right, b.top, covers)
    if crs is not None:
        logger.info("[%s] crs=%s res=%.8f deg", label, crs, res[0])
    if not covers:
        raise RuntimeError(f"{label} does NOT fully cover the study bounding box.")
    return True


def cell_sizes_in_meters(transform, width, height, lat_center, lon_center):
    geod = Geod(ellps="WGS84")
    _, _, dy_m = geod.inv(lon_center, lat_center, lon_center, lat_center + abs(transform.e))
    _, _, dx_m = geod.inv(lon_center, lat_center, lon_center + abs(transform.a), lat_center)
    logger.info("Pixel ground size: dx=%.2f m dy=%.2f m", dx_m, dy_m)
    return dx_m, dy_m


def derive_slope(elev_path, dst_path):
    with rasterio.open(elev_path) as src:
        elev = src.read(1).astype(np.float64)
        transform = src.transform
        crs = src.crs
        height, width = elev.shape

    elev[elev == ELEV_NODATA] = np.nan
    valid = np.isfinite(elev)

    lat_center = (transform.f + transform.f + transform.e * height) / 2.0
    lon_center = (transform.c + transform.c + transform.a * width) / 2.0
    dx_m, dy_m = cell_sizes_in_meters(transform, width, height, lat_center, lon_center)

    filled = np.where(valid, elev, 0.0)
    pad = np.pad(filled, 1, mode="edge")
    a = pad[:-2, :-2]; b = pad[:-2, 1:-1]; c = pad[:-2, 2:]
    d = pad[1:-1, :-2];                     f = pad[1:-1, 2:]
    g = pad[2:, :-2];   h = pad[2:, 1:-1];  i = pad[2:, 2:]

    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8.0 * dx_m)
    dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8.0 * dy_m)
    slope_deg = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))

    invalid_f = (~valid).astype(np.float32)
    from scipy.ndimage import maximum_filter
    bad_neighborhood = maximum_filter(invalid_f, size=3) > 0
    slope_deg[bad_neighborhood] = np.nan

    n_nodata_out = int(np.sum(~np.isfinite(slope_deg)))
    slope_out = np.where(np.isfinite(slope_deg), slope_deg, SLOPE_NODATA).astype(np.float32)

    profile = {
        "driver": "GTiff", "height": height, "width": width, "count": 1,
        "dtype": "float32", "crs": crs, "transform": transform,
        "nodata": SLOPE_NODATA, "compress": "deflate",
    }
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with rasterio.open(dst_path, "w", **profile) as dst:
        dst.write(slope_out, 1)
        dst.set_band_description(1, "Slope (degrees, Horn 3x3)")

    v = slope_out[slope_out != SLOPE_NODATA]
    logger.info("Slope written: %s (%dx%d) valid=%d nodata_px=%d range=[%.2f, %.2f] deg mean=%.2f",
                dst_path, width, height, v.size, n_nodata_out,
                float(v.min()), float(v.max()), float(v.mean()))


def clip_to_study(src_path, dst_path):
    with rasterio.open(src_path) as src:
        out_img, out_transform = rio_mask(src, [STUDY_BOX], crop=True, nodata=src.nodata)
        profile = src.meta.copy()
    profile.update(driver="GTiff", height=out_img.shape[1], width=out_img.shape[2],
                   transform=out_transform, compress="deflate")
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with rasterio.open(dst_path, "w", **profile) as dst:
        dst.write(out_img)
    logger.info("Clipped %s -> %s", os.path.basename(src_path), dst_path)


def report_raster_stats(path, label):
    with rasterio.open(path) as src:
        arr = src.read(1)
        nd = src.nodata
        m = np.ones(arr.shape, bool) if nd is None else (arr != nd)
        m &= np.isfinite(arr)
        v = arr[m].astype(np.float64)
        logger.info("[%s] file=%s crs=%s res=%.9f,%.9f bounds=%s nodata=%s",
                    label, path, src.crs, src.res[0], src.res[1],
                    tuple(round(x, 6) for x in src.bounds), nd)
        logger.info("[%s] valid_px=%d (%.2f%%) min=%.2f max=%.2f mean=%.2f",
                    label, v.size, 100.0 * v.size / arr.size,
                    float(v.min()), float(v.max()), float(v.mean()))


def main():
    logger.info("=" * 70)
    logger.info("PHASE 2: MERGE REAL SRTM TILES -> DERIVE SLOPE -> CLIP TO STUDY AREA")
    logger.info("=" * 70)

    tile_paths = []
    for name in TILE_NAMES:
        p = os.path.join(SRTM_DIR, name)
        if not os.path.exists(p):
            raise FileNotFoundError(f"Required SRTM tile missing: {p}")
        tile_paths.append(p)

    merged_bounds = merge_tiles(tile_paths, FULL_ELEV_OUT)
    verify_coverage(merged_bounds, MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, "MERGED-DEM(in-memory)")

    derive_slope(FULL_ELEV_OUT, FULL_SLOPE_OUT)

    clip_to_study(FULL_ELEV_OUT, PROC_ELEV_OUT)
    clip_to_study(FULL_SLOPE_OUT, PROC_SLOPE_OUT)

    verify_coverage(PROC_ELEV_OUT, MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, "PROCESSED-ELEV")
    verify_coverage(PROC_SLOPE_OUT, MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, "PROCESSED-SLOPE")

    report_raster_stats(FULL_ELEV_OUT, "FULL-DEM")
    report_raster_stats(FULL_SLOPE_OUT, "FULL-SLOPE")
    report_raster_stats(PROC_ELEV_OUT, "CLIPPED-DEM")
    report_raster_stats(PROC_SLOPE_OUT, "CLIPPED-SLOPE")

    logger.info("PHASE 2 COMPLETE.")


if __name__ == "__main__":
    main()
