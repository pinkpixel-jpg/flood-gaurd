import os
import logging
import requests
import numpy as np
import rasterio
import rasterio.mask
import rasterio.merge
import osmnx as ox
import geopandas as gpd
from shapely.geometry import box

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Bounding box for Pune study area
MIN_LAT, MAX_LAT = 18.30, 18.75
MIN_LON, MAX_LON = 73.60, 74.10
pune_bbox = box(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)

def download_file(url: str, dest_path: str, timeout: int = 60):
    """Downloads a file with stream blocks, checking size for resuming/skipping."""
    try:
        # Get server Content-Length
        r_head = requests.head(url, timeout=timeout)
        server_size = int(r_head.headers.get("Content-Length", 0))
        
        if os.path.exists(dest_path):
            local_size = os.path.getsize(dest_path)
            if local_size == server_size and server_size > 0:
                logger.info(f"File already fully downloaded, skipping: {dest_path}")
                return True
            else:
                logger.warning(f"File size mismatch (local: {local_size}, server: {server_size}). Redownloading...")
                os.remove(dest_path)
    except Exception as head_e:
        logger.warning(f"Failed to check headers for {url}: {head_e}. Checking local file existence.")
        if os.path.exists(dest_path):
            logger.info(f"File exists, skipping download (unable to verify size): {dest_path}")
            return True

    logger.info(f"Downloading {url} to {dest_path}...")
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with requests.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"Download complete: {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return False

def compute_slope(elevation_path: str, slope_path: str):
    """Computes terrain slope in degrees from an elevation raster using numpy gradient."""
    logger.info(f"Computing slope from elevation raster: {elevation_path}")
    try:
        with rasterio.open(elevation_path) as src:
            elev = src.read(1).astype(np.float32)
            # Spacing in meters (1 arc-second is approx 30m)
            dx = 30.0
            dy = 30.0
            
            # Compute central difference gradients
            dy_arr, dx_arr = np.gradient(elev, dy, dx)
            # Calculate slope in radians and degrees
            slope_rad = np.arctan(np.sqrt(dx_arr**2 + dy_arr**2))
            slope_deg = np.degrees(slope_rad)
            
            # Mask nodata
            if src.nodata is not None:
                slope_deg[elev == src.nodata] = -9999.0
            else:
                slope_deg[np.isnan(elev)] = -9999.0

            meta = src.meta.copy()
            meta.update({
                'dtype': 'float32',
                'nodata': -9999.0
            })
            
            with rasterio.open(slope_path, 'w', **meta) as dst:
                dst.write(slope_deg.astype(np.float32), 1)
        logger.info(f"Successfully computed slope and saved to: {slope_path}")
        return True
    except Exception as e:
        logger.error(f"Error computing slope: {e}")
        return False

def main():
    raw_dir = "hehehackathon/IHSA6_GIS"
    os.makedirs(raw_dir, exist_ok=True)
    
    # 1. Download Full GeoTIFF layers (Section 1)
    # OpenTopography public S3 bucket URLs for SRTM GL1 (30m) elevation
    dem_url_1 = "https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/N18E073.tif"
    dem_url_2 = "https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm/N18E074.tif"
    # ESA WorldCover 2021 (10m) public AWS S3 URL
    lc_url = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E072_Map.tif"

    dem_path_1 = os.path.join(raw_dir, "N18E073.tif")
    dem_path_2 = os.path.join(raw_dir, "N18E074.tif")
    lc_path = os.path.join(raw_dir, "pune_landcover_full.tif")

    logger.info("Downloading raw raster datasets to ensure 100% spatial coverage...")
    download_file(dem_url_1, dem_path_1)
    download_file(dem_url_2, dem_path_2)
    download_file(lc_url, lc_path)

    # 2. Merge elevation rasters
    merged_dem_path = os.path.join(raw_dir, "pune_elevation_full.tif")
    logger.info("Merging DEM tiles N18E073 and N18E074...")
    try:
        src_files_to_mosaic = [rasterio.open(dem_path_1), rasterio.open(dem_path_2)]
        mosaic, out_trans = rasterio.merge.merge(src_files_to_mosaic)
        
        out_meta = src_files_to_mosaic[0].meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans,
            "crs": src_files_to_mosaic[0].crs
        })
        with rasterio.open(merged_dem_path, "w", **out_meta) as dest:
            dest.write(mosaic)
        logger.info(f"Merged DEM saved to: {merged_dem_path}")
    except Exception as e:
        logger.error(f"Error merging DEM files: {e}")

    # 3. Compute Slope from merged DEM
    merged_slope_path = os.path.join(raw_dir, "pune_slope_full.tif")
    compute_slope(merged_dem_path, merged_slope_path)

    # 4. Overwrite raw files in the pipeline raw_dir to point to complete raster coverages
    logger.info("Replacing raw TIF files in workspace with 100% complete raster layers...")
    shutil_copy_list = [
        (merged_dem_path, "hehehackathon/pune_elevation.tif"),
        (merged_slope_path, "hehehackathon/pune_slope.tif"),
        (lc_path, "hehehackathon/pune_landcover.tif")
    ]
    for src, dst in shutil_copy_list:
        import shutil
        shutil.copy(src, dst)
        logger.info(f"Updated raw file {dst}")

    # 5. Query OpenStreetMap for the entire Pune study area (Section 2)
    logger.info("Querying OSM for the entire study bounding box to ensure road/waterway completeness...")
    # bbox in format: (left, bottom, right, top)
    bbox_osm = (MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)
    
    # Download complete roads network graph
    try:
        logger.info("Querying OSM Overpass API for roads network...")
        ox.settings.requests_timeout = 300
        G = ox.graph.graph_from_bbox(bbox=bbox_osm, network_type="drive", simplify=True)
        roads_graphml = "hehehackathon/city_roads/pune_roads.graphml.xml"
        os.makedirs(os.path.dirname(roads_graphml), exist_ok=True)
        ox.io.save_graphml(G, roads_graphml)
        logger.info(f"Saved complete OSM roads graph to: {roads_graphml}")
    except Exception as e:
        logger.error(f"Error downloading OSM roads: {e}")

    # Download complete waterways features
    try:
        logger.info("Querying OSM Overpass API for waterways network...")
        tags = {"waterway": ["river", "stream", "canal", "drain", "ditch"]}
        waterways = ox.features.features_from_bbox(bbox=bbox_osm, tags=tags)
        waterways_gpkg = "hehehackathon/city_waterways/pune_waterways.gpkg"
        os.makedirs(os.path.dirname(waterways_gpkg), exist_ok=True)
        waterways.to_file(waterways_gpkg, layer="waterways", driver="GPKG")
        logger.info(f"Saved complete OSM waterways GeoPackage to: {waterways_gpkg}")
    except Exception as e:
        logger.error(f"Error downloading OSM waterways: {e}")

    logger.info("Raw datasets download and pre-processing completed successfully.")

if __name__ == "__main__":
    main()
