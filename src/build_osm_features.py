import argparse
import json
import logging
import os
import time

import geopandas as gpd
import osmnx as ox

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = 73.60, 18.30, 74.10, 18.75

TEST_BBOX = (73.79, 18.51, 73.83, 18.54)

CATEGORIES = {
    "roads": {"highway": [
        "motorway", "motorway_link", "trunk", "trunk_link",
        "primary", "primary_link", "secondary", "secondary_link",
        "tertiary", "tertiary_link", "unclassified", "residential",
    ]},
    "waterways": {"waterway": ["river", "stream", "canal"]},
    "drainage": {"waterway": ["drain", "ditch"]},
}

ENDPOINTS = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
]

VALID_LINE_TYPES = {"LineString", "MultiLineString"}


def fetch_category(category, bbox, timeout_s, max_endpoints):
    tags = CATEGORIES[category]
    original_endpoint = ox.settings.overpass_url
    ox.settings.requests_timeout = timeout_s

    timed_out = False
    attempts = ENDPOINTS[:max_endpoints]
    for i, endpoint in enumerate(attempts, start=1):
        try:
            ox.settings.overpass_url = endpoint
            logger.info("[%s] attempt %d/%d -> %s (timeout=%ss)",
                        category, i, len(attempts), endpoint, timeout_s)
            t0 = time.time()
            gdf = ox.features_from_bbox(bbox=bbox, tags=tags)
            dt = time.time() - t0
            gdf = gdf.reset_index()
            logger.info("[%s] SUCCESS via %s: %d raw features in %.1fs",
                        category, endpoint, len(gdf), dt)
            return gdf, timed_out
        except Exception as e:
            msg = str(e)
            if "timeout" in msg.lower() or "timed out" in msg.lower():
                timed_out = True
            logger.warning("[%s] endpoint %s failed after %.1fs: %s",
                           category, endpoint, time.time() - t0, msg[:140])
        finally:
            ox.settings.overpass_url = original_endpoint
        if i < len(attempts):
            time.sleep(3)
    return None, timed_out


def clean_lines(gdf, tag_col):
    keep = ["name", tag_col, "geometry"]
    cols = [c for c in keep if c in gdf.columns]
    out = gdf[cols].copy()
    out = out[~(out.geometry.isna() | out.geometry.is_empty)]
    out = out[out.geom_type.isin(VALID_LINE_TYPES)]
    if out.crs != "EPSG:4326":
        out = out.to_crs("EPSG:4326")
    return out


def validate_gdf(gdf, tag_col):
    stats = {
        "n_features": int(len(gdf)),
        "n_empty": int((gdf.geometry.isna() | gdf.geometry.is_empty).sum()) if len(gdf) else 0,
        "n_invalid": int((~gdf.geometry.is_valid).sum()) if len(gdf) else 0,
        "geom_types": gdf.geom_type.value_counts().to_dict() if len(gdf) else {},
        "tag_values": gdf[tag_col].value_counts().to_dict() if len(gdf) else {},
    }
    if len(gdf):
        b = gdf.total_bounds
        stats["bounds"] = tuple(round(float(x), 5) for x in b)
    return stats


def save_geojson(gdf, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")
    size_kb = os.path.getsize(path) / 1024.0
    logger.info("saved %s (%d features, %.1f KB)", path, len(gdf), size_kb)
    return size_kb


def run_test(args):
    results = {}
    any_timeout = False

    for category in ("roads", "waterways", "drainage"):
        out_path = os.path.join(args.out_dir, f"{category}_test.geojson")
        entry = {"status": "FAILED", "n_features": 0}
        try:
            gdf, timed_out = fetch_category(category, TEST_BBOX, args.timeout, args.max_endpoints)
            any_timeout = any_timeout or timed_out
            if gdf is None or len(gdf) == 0:
                logger.error("[%s] TEST FAILED (no features / all endpoints failed).", category)
                results[category] = entry
                continue
            lines = clean_lines(gdf, list(CATEGORIES[category].keys())[0])
            stats = validate_gdf(lines, list(CATEGORIES[category].keys())[0])
            size_kb = save_geojson(lines, out_path) if len(lines) else 0.0
            entry.update({
                "status": "OK" if len(lines) else "EMPTY",
                **stats,
                "file_kb": round(size_kb, 1),
                "file": out_path if len(lines) else None,
            })
            logger.info("[%s] validation: %s", category,
                        json.dumps({k: v for k, v in entry.items() if k != 'status'}, default=str))
        except Exception as e:
            logger.error("[%s] unexpected error: %s", category, str(e)[:160])
        results[category] = entry

    invalid_total = sum(r.get("n_invalid", 0) + r.get("n_empty", 0) for r in results.values())
    print()
    print("OSM TEST RESULTS")
    print("----------------")
    for category in ("roads", "waterways", "drainage"):
        r = results[category]
        print(f"{category.capitalize()}: {r['n_features']} ({r['status']})")
    print(f"Invalid geometries: {invalid_total}")
    print(f"Timeout: {'YES' if any_timeout else 'NO'}")
    print()

    with open(os.path.join(args.out_dir, "osm_test_results.json"), "w") as f:
        json.dump({"bbox": TEST_BBOX, "timeout_s": args.timeout,
                   "results": results, "any_timeout": any_timeout}, f, indent=2, default=str)
    logger.info("TEST COMPLETE. Full-pune download NOT started.")


def main():
    ap = argparse.ArgumentParser(description="Independent, strictly timeboxed OSM feature downloader")
    ap.add_argument("--category", choices=list(CATEGORIES.keys()), default=None,
                    help="run one full-area category (quadrant-split)")
    ap.add_argument("--test", action="store_true", help="small-area connectivity/geometries test")
    ap.add_argument("--timeout", type=int, default=60, help="strict per-request timeout seconds")
    ap.add_argument("--max-endpoints", type=int, default=2, help="max endpoints tried per operation")
    ap.add_argument("--out-dir", default=os.path.join("data", "processed", "osm_test"))
    args = ap.parse_args()

    if args.test:
        logger.info("=" * 70)
        logger.info("OSM SMALL-AREA TEST | bbox=%s | timeout=%ss | max_endpoints=%d",
                    TEST_BBOX, args.timeout, args.max_endpoints)
        logger.info("=" * 70)
        run_test(args)
        return

    if args.category:
        raise SystemExit(
            "Full-area downloads are intentionally locked until tests pass and "
            "explicit go-ahead is given. Use --test first.")
    ap.print_help()


if __name__ == "__main__":
    main()
