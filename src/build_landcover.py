import os
import logging

import numpy as np
import requests
import rasterio
from rasterio.windows import Window

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = 73.60, 18.30, 74.10, 18.75

LOCAL_FULL = os.path.join("hehehackathon", "IHSA6_GIS", "pune_landcover_full.tif")
OUT_PATH = os.path.join("data", "processed", "pune_landcover.tif")

WORLDCOVER_TILE = "ESA_WorldCover_10m_2021_v200_N18E072_Map.tif"
S3_HTTPS = f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/{WORLDCOVER_TILE}"
S3_VSIS3 = f"/vsis3/esa-worldcover/v200/2021/map/{WORLDCOVER_TILE}"

CLASS_NAMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}
GREEN_CLASSES = [10, 20, 30]
BUILT_UP_CLASS = 50


def local_raster_covers_study(path):
    if not os.path.exists(path):
        return False
    try:
        with rasterio.open(path) as src:
            b = src.bounds
            if not (b.left <= MIN_LON and b.bottom <= MIN_LAT and b.right >= MAX_LON and b.top >= MAX_LAT):
                logger.info("Local raster %s does not cover study bbox.", path)
                return False
            from rasterio.windows import from_bounds
            win = from_bounds(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, src.transform)
            win = win.round_offsets().round_lengths()
            _ = src.read(1, window=win)
        return True
    except Exception as e:
        logger.warning("Local raster %s unreadable over study window: %s", path, str(e)[:120])
        return False


def fetch_from_aws(dst_path):
    env_opts = dict(
        AWS_NO_SIGN_REQUEST="YES",
        GDAL_HTTP_TIMEOUT="120",
        GDAL_HTTP_MAX_RETRY="3",
        GDAL_HTTP_RETRY_DELAY="5",
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    )
    last_err = None
    for url in (S3_VSIS3, f"/vsicurl/{S3_HTTPS}"):
        try:
            logger.info("Attempting windowed COG read: %s", url)
            with rasterio.Env(**env_opts):
                with rasterio.open(url) as src:
                    logger.info("Remote tile: crs=%s res=%.8f dims=%dx%d bounds=%s",
                                src.crs, src.res[0], src.width, src.height,
                                tuple(round(x, 4) for x in src.bounds))
                    from rasterio.windows import from_bounds
                    win = from_bounds(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, src.transform)
                    win = win.round_offsets().round_lengths()
                    data = src.read(1, window=win)
                    transform = src.window_transform(win)
                    profile = {
                        "driver": "GTiff", "height": data.shape[0], "width": data.shape[1],
                        "count": 1, "dtype": "uint8", "crs": src.crs,
                        "transform": transform, "nodata": 0, "compress": "deflate",
                    }
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    with rasterio.open(dst_path, "w", **profile) as dst:
                        dst.write(data, 1)
                        dst.set_band_description(1, "ESA WorldCover 2021 v200 class")
                    logger.info("Saved windowed WorldCover (%d px x %d px) -> %s",
                                data.shape[1], data.shape[0], dst_path)
                    return True
        except Exception as e:
            last_err = e
            logger.warning("Source failed (%s): %s", url, str(e)[:160])
    raise RuntimeError(f"All WorldCover sources failed. Last error: {last_err}")


def validate(dst_path):
    with rasterio.open(dst_path) as src:
        arr = src.read(1)
        b = src.bounds
        covers = (b.left <= MIN_LON and b.bottom <= MIN_LAT and b.right >= MAX_LON and b.top >= MAX_LAT)
        logger.info("[WORLDCOVER] file=%s crs=%s res=%.8f deg (~%.2f m)", dst_path, src.crs,
                    src.res[0], src.res[0] * 111320 * np.cos(np.radians((MIN_LAT + MAX_LAT) / 2)))
        logger.info("[WORLDCOVER] bounds=%s covers_study_bbox=%s nodata=%s",
                    tuple(round(x, 6) for x in b), covers, src.nodata)
        if not covers:
            raise RuntimeError("Repaired WorldCover still does not cover the study bbox.")

    valid = arr[arr != 0]
    total_valid = valid.size
    logger.info("[WORLDCOVER] valid_px=%d (%.2f%% of window)", total_valid, 100 * total_valid / arr.size)
    u, c = np.unique(valid.astype(int), return_counts=True)
    for cls, cnt in zip(u.tolist(), c.tolist()):
        name = CLASS_NAMES.get(cls, "UNKNOWN CLASS")
        logger.info("[WORLDCOVER] class %3d %-26s %12d px (%5.2f%%)",
                    cls, name, cnt, 100.0 * cnt / total_valid)

    built_pct = 100.0 * c[u.tolist().index(50)] / total_valid if 50 in u.tolist() else 0.0
    green_mask = np.isin(valid, GREEN_CLASSES)
    green_pct = 100.0 * green_mask.sum() / total_valid
    logger.info("[WORLDCOVER] study-area totals: built_up=%.2f%% green(Tree/Shrub/Grass)=%.2f%%",
                built_pct, green_pct)


def main():
    logger.info("=" * 70)
    logger.info("PHASE 3: WORLD COVER VERIFICATION / REPAIR")
    logger.info("=" * 70)

    if local_raster_covers_study(LOCAL_FULL):
        logger.info("Existing %s is fully readable over the study area. Reusing it.", LOCAL_FULL)
        import shutil
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        shutil.copy(LOCAL_FULL, OUT_PATH)
    else:
        logger.info("Local WorldCover is corrupt/incomplete over the study area.")
        logger.info("Corrupt file preserved untouched at: %s", LOCAL_FULL)
        logger.info("Repairing via windowed COG read from public AWS Open Data bucket (no Overpass involved).")
        fetch_from_aws(OUT_PATH)

    validate(OUT_PATH)
    logger.info("PHASE 3 COMPLETE.")


if __name__ == "__main__":
    main()
