import os
import logging
import shutil
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import rasterio.mask
import osmnx as ox
import matplotlib.pyplot as plt
from shapely.geometry import box, Point

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define exact Pune study-area bounding box (Section 4)
MIN_LAT, MAX_LAT = 18.30, 18.75
MIN_LON, MAX_LON = 73.60, 74.10

# Bounding box polygon in WGS84 (EPSG:4326)
pune_study_area_wgs84 = box(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT)

def clip_raster(src_path: str, dst_path: str, bbox_poly):
    """Clips a raster using rasterio mask to the study area and saves the cropped file."""
    if not os.path.exists(src_path):
        logger.error(f"Source raster not found at: {src_path}")
        return False
    try:
        with rasterio.open(src_path) as src:
            # Re-project bbox if raster CRS is different, but they are all EPSG:4326
            out_image, out_transform = rasterio.mask.mask(src, [bbox_poly], crop=True)
            out_meta = src.meta.copy()
            nodata_val = src.nodata
            if nodata_val is None:
                if "int8" in str(src.dtypes[0]) or "uint8" in str(src.dtypes[0]):
                    nodata_val = 0
                else:
                    nodata_val = -9999.0
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": nodata_val
            })
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            with rasterio.open(dst_path, "w", **out_meta) as dest:
                dest.write(out_image)
            logger.info(f"Successfully clipped raster and saved to: {dst_path}")
            return True
    except Exception as e:
        logger.error(f"Error clipping raster {src_path}: {e}")
        return False

def main():
    logger.info("=" * 70)
    logger.info("       PUNE FLOODSHIELD — DATA ENGINEERING PIPELINE")
    logger.info("=" * 70)

    # 1. Paths Setup
    raw_dir = "hehehackathon"
    processed_dir = "data/processed"
    os.makedirs(processed_dir, exist_ok=True)
    
    raw_elev = os.path.join(raw_dir, "IHSA6_GIS/pune_elevation.tif")
    raw_slope = os.path.join(raw_dir, "IHSA6_GIS/pune_slope.tif")
    raw_lc = os.path.join(raw_dir, "IHSA6_GIS/pune_landcover.tif")

    proc_elev = os.path.join(processed_dir, "pune_elevation.tif")
    proc_slope = os.path.join(processed_dir, "pune_slope.tif")
    proc_lc = os.path.join(processed_dir, "pune_landcover.tif")

    # 2. Clip and Process Rasters (Section 5 & 6)
    logger.info("Clipping elevation, slope, and landcover rasters to study area...")
    clip_raster(raw_elev, proc_elev, pune_study_area_wgs84)
    clip_raster(raw_slope, proc_slope, pune_study_area_wgs84)
    clip_raster(raw_lc, proc_lc, pune_study_area_wgs84)

    # 3. Process OSM Waterways and Drainage (Section 7)
    logger.info("Processing OSM Waterways/Drainage dataset...")
    waterways_gpkg = os.path.join(raw_dir, "city_waterways/pune_waterways.gpkg")
    proc_waterways_path = os.path.join(processed_dir, "pune_waterways.geojson")
    proc_drainage_path = os.path.join(processed_dir, "pune_drainage.geojson")

    if os.path.exists(waterways_gpkg):
        try:
            gdf_water = gpd.read_file(waterways_gpkg)
            # Standardize WGS84 CRS explicitly
            gdf_water = gdf_water.set_crs(epsg=4326, allow_override=True)
            # Clip to study area
            gdf_water_clipped = gpd.clip(gdf_water, pune_study_area_wgs84)

            # Separate into drainage (canal, drain) and natural waterways (river, stream)
            gdf_drainage = gdf_water_clipped[gdf_water_clipped["waterway"].isin(["canal", "drain"])]
            gdf_natural_water = gdf_water_clipped[gdf_water_clipped["waterway"].isin(["river", "stream"])]

            gdf_natural_water.to_file(proc_waterways_path, driver="GeoJSON")
            gdf_drainage.to_file(proc_drainage_path, driver="GeoJSON")
            logger.info(f"Saved waterways vector to {proc_waterways_path}")
            logger.info(f"Saved drainage vector to {proc_drainage_path}")
        except Exception as e:
            logger.error(f"Error processing waterways GeoPackage: {e}")
            gdf_natural_water = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            gdf_drainage = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    else:
        logger.error(f"Waterways GeoPackage not found at: {waterways_gpkg}")
        gdf_natural_water = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        gdf_drainage = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # 4. Process OSM Roads (Section 7)
    logger.info("Processing OSM Roads dataset...")
    roads_graphml = os.path.join(raw_dir, "city_roads/pune_roads.graphml.xml")
    proc_roads_path = os.path.join(processed_dir, "pune_roads.geojson")

    if os.path.exists(roads_graphml):
        try:
            G = ox.load_graphml(roads_graphml)
            gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
            # Clip to study area
            gdf_roads_clipped = gpd.clip(gdf_edges, pune_study_area_wgs84)
            # Keep only line geometries and simplify columns
            gdf_roads_clipped = gdf_roads_clipped[["geometry"]].reset_index(drop=True)
            gdf_roads_clipped.to_file(proc_roads_path, driver="GeoJSON")
            logger.info(f"Saved roads vector to {proc_roads_path}")
        except Exception as e:
            logger.error(f"Error processing roads GraphML: {e}")
            gdf_roads_clipped = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    else:
        logger.error(f"Roads GraphML not found at: {roads_graphml}")
        gdf_roads_clipped = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # 5. Define Master Spatial Units (Section 10)
    # The study area covers 4 grid cells centering at 0.25° grid coordinates
    grid_cells = [
        {"zone_id": "PUNE_G001", "center_lat": 18.50, "center_lon": 73.75},
        {"zone_id": "PUNE_G002", "center_lat": 18.50, "center_lon": 74.00},
        {"zone_id": "PUNE_G003", "center_lat": 18.75, "center_lon": 73.75},
        {"zone_id": "PUNE_G004", "center_lat": 18.75, "center_lon": 74.00},
    ]

    # Convert vector datasets to UTM Zone 43N (EPSG:32643) for distance/area metric calculations (Section 9)
    proj_crs = "EPSG:32643"
    gdf_roads_proj = gdf_roads_clipped.to_crs(proj_crs) if not gdf_roads_clipped.empty else gdf_roads_clipped
    gdf_water_proj = gdf_natural_water.to_crs(proj_crs) if not gdf_natural_water.empty else gdf_natural_water
    gdf_drain_proj = gdf_drainage.to_crs(proj_crs) if not gdf_drainage.empty else gdf_drainage

    # 6. Process Flood Events labels (Section 8)
    flood_events_path = os.path.join(raw_dir, "pune_flood_events.csv")
    flood_events = []
    if os.path.exists(flood_events_path):
        try:
            flood_df = pd.read_csv(flood_events_path)
            # Create Point geometry for each flood event
            for _, row in flood_df.iterrows():
                flood_events.append({
                    "geometry": Point(row["longitude"], row["latitude"]),
                    "event_id": row.get("event_id", 0)
                })
            logger.info(f"Loaded {len(flood_events)} historical flood events from {flood_events_path}")
        except Exception as e:
            logger.error(f"Error loading flood events: {e}")
            
    # 7. Process Hourly River Water Level Telemetry Data (Open Question Integration)
    telemetry_path = os.path.join(raw_dir, "rwl_tel_hr_maharashtra_sw_007_2021_2025 (1).csv")
    telemetry_stations = []
    if os.path.exists(telemetry_path):
        try:
            logger.info("Processing river water level telemetry station mapping...")
            tel_df = pd.read_csv(telemetry_path)
            # Group by Station to get stable coordinates and level stats
            station_groups = tel_df.groupby("Station").agg({
                "Latitude": "first",
                "Longitude": "first",
                "River Water Level Telemetry Hourly (meter)": ["max", "mean"]
            })
            station_groups.columns = ["Latitude", "Longitude", "Level_Max", "Level_Mean"]
            station_groups = station_groups.reset_index()
            
            for _, row in station_groups.iterrows():
                # Store coordinates and statistics
                telemetry_stations.append({
                    "station": row["Station"],
                    "point": Point(row["Longitude"], row["Latitude"]),
                    "level_max": float(row["Level_Max"]),
                    "level_mean": float(row["Level_Mean"])
                })
            logger.info(f"Mapped {len(telemetry_stations)} telemetry stations with hourly stats.")
        except Exception as e:
            logger.error(f"Error processing telemetry data: {e}")

    # 8. Compute Master Spatial Features (Section 11)
    feature_records = []
    
    # Load historical rainfall daily time series (Section 3)
    rainfall_ts_path = "data/processed/pune/pune_spatial_rainfall_2015_2025.csv"
    if os.path.exists(rainfall_ts_path):
        try:
            logger.info("Loading Pune daily spatial rainfall for temporal stats...")
            rain_df = pd.read_csv(rainfall_ts_path)
            # Copy to processed/pune_rainfall_spatial.csv as requested
            shutil.copy(rainfall_ts_path, os.path.join(processed_dir, "pune_rainfall_spatial.csv"))
        except Exception as e:
            logger.error(f"Error loading base rainfall dataset: {e}")
            rain_df = None
    else:
        rain_df = None

    # Load elevation, slope, and landcover rasters
    try:
        r_elev = rasterio.open(proc_elev)
        r_slope = rasterio.open(proc_slope)
        r_lc = rasterio.open(proc_lc)
    except Exception as e:
        logger.error(f"Error opening processed rasters for extraction: {e}")
        r_elev, r_slope, r_lc = None, None, None

    for cell in grid_cells:
        zone_id = cell["zone_id"]
        c_lat = cell["center_lat"]
        c_lon = cell["center_lon"]

        # Cell extent polygon (0.25° x 0.25° cell centered at coordinate)
        lat_min, lat_max = c_lat - 0.125, c_lat + 0.125
        lon_min, lon_max = c_lon - 0.125, c_lon + 0.125
        cell_geom = box(lon_min, lat_min, lon_max, lat_max)
        
        # Cell polygon and center in UTM 43N
        gdf_cell_wgs = gpd.GeoDataFrame(geometry=[cell_geom], crs="EPSG:4326")
        gdf_cell_proj = gdf_cell_wgs.to_crs(proj_crs)
        cell_geom_proj = gdf_cell_proj.geometry.values[0]
        cell_area_km2 = cell_geom_proj.area / 1e6

        gdf_center_wgs = gpd.GeoDataFrame(geometry=[Point(c_lon, c_lat)], crs="EPSG:4326")
        gdf_center_proj = gdf_center_wgs.to_crs(proj_crs)
        center_pt_proj = gdf_center_proj.geometry.values[0]

        logger.info(f"Aggregating features for spatial unit: {zone_id}...")

        # A. Raster Features (Elevation, Slope, Land cover)
        elev_mean, elev_min, elev_max = float("nan"), float("nan"), float("nan")
        slope_mean = float("nan")
        built_up_pct, green_cover_pct = float("nan"), float("nan")

        if r_elev and r_slope and r_lc:
            try:
                # Mask rasters using the cell WGS84 polygon
                elev_img, _ = rasterio.mask.mask(r_elev, [cell_geom], crop=True)
                slope_img, _ = rasterio.mask.mask(r_slope, [cell_geom], crop=True)
                lc_img, _ = rasterio.mask.mask(r_lc, [cell_geom], crop=True)

                # Flatten arrays and filter nodata/invalid
                elev_vals = elev_img[0].flatten()
                elev_valid = elev_vals[(elev_vals != r_elev.nodata) & (~np.isnan(elev_vals))]
                
                slope_vals = slope_img[0].flatten()
                slope_valid = slope_vals[(slope_vals != r_slope.nodata) & (~np.isnan(slope_vals))]

                lc_vals = lc_img[0].flatten()
                lc_valid = lc_vals[(lc_vals != r_lc.nodata) & (~np.isnan(lc_vals))]

                if len(elev_valid) > 0:
                    elev_mean = float(np.mean(elev_valid))
                    elev_min = float(np.min(elev_valid))
                    elev_max = float(np.max(elev_valid))
                
                if len(slope_valid) > 0:
                    slope_mean = float(np.mean(slope_valid))

                if len(lc_valid) > 0:
                    # 50 = Built-up (ESA classification)
                    built_up_pixels = np.sum(lc_valid == 50)
                    built_up_pct = float((built_up_pixels / len(lc_valid)) * 100)

                    # 10 = Tree cover, 20 = Shrubland, 30 = Grassland
                    green_pixels = np.sum(np.isin(lc_valid, [10, 20, 30]))
                    green_cover_pct = float((green_pixels / len(lc_valid)) * 100)

            except Exception as mask_e:
                logger.warning(f"Failed to mask rasters for spatial unit {zone_id}: {mask_e}")

        # B. OSM Densities (Roads, Drainage)
        road_density = 0.0
        drainage_density = 0.0

        if not gdf_roads_proj.empty:
            # Intersect roads with cell
            roads_clipped = gdf_roads_proj[gdf_roads_proj.intersects(cell_geom_proj)].copy()
            if not roads_clipped.empty:
                roads_clipped.geometry = roads_clipped.geometry.intersection(cell_geom_proj)
                total_road_len_m = roads_clipped.geometry.length.sum()
                road_density = float(total_road_len_m / cell_area_km2)

        if not gdf_drain_proj.empty:
            # Intersect drainage with cell
            drain_clipped = gdf_drain_proj[gdf_drain_proj.intersects(cell_geom_proj)].copy()
            if not drain_clipped.empty:
                drain_clipped.geometry = drain_clipped.geometry.intersection(cell_geom_proj)
                total_drain_len_m = drain_clipped.geometry.length.sum()
                drainage_density = float(total_drain_len_m / cell_area_km2)

        # C. Shortest Distances (Waterways, Drainage)
        distance_to_water = float("nan")
        distance_to_drainage = float("nan")

        if not gdf_water_proj.empty:
            # Shortest distance from cell center (in UTM) to any waterways line
            distance_to_water = float(gdf_water_proj.distance(center_pt_proj).min())

        if not gdf_drain_proj.empty:
            # Shortest distance from cell center (in UTM) to any drainage line
            distance_to_drainage = float(gdf_drain_proj.distance(center_pt_proj).min())

        # D. Temporal Rainfall Statistics (Section 3)
        rain_mean, rain_max, rain_24h, rain_7d, rain_hist_mean = float("nan"), float("nan"), float("nan"), float("nan"), float("nan")
        if rain_df is not None:
            cell_rain = rain_df[rain_df["Grid_ID"] == zone_id]
            if len(cell_rain) > 0:
                rain_mean = float(cell_rain["Rainfall_mm"].mean())
                rain_max = float(cell_rain["Rainfall_mm"].max())
                rain_hist_mean = rain_mean
                # Latest daily rainfall as 24h representative
                rain_24h = float(cell_rain.sort_values("Date")["Rainfall_mm"].iloc[-1])
                # Calculate 7d rolling sum statistics
                rolling_7d = cell_rain.sort_values("Date")["Rainfall_mm"].rolling(window=7).sum()
                rain_7d = float(rolling_7d.max()) # Max historical 7d accumulated rainfall

        # E. Flood Labels count
        flood_label = 0
        for event in flood_events:
            if cell_geom.contains(event["geometry"]):
                flood_label += 1

        # F. Hourly Telemetry Integration (Section 8 / Open Questions)
        tel_count = 0
        tel_max = float("nan")
        tel_mean = float("nan")
        cell_stations = []
        for station in telemetry_stations:
            if cell_geom.contains(station["point"]):
                cell_stations.append(station)
                tel_count += 1
        
        if tel_count > 0:
            tel_max = float(max(s["level_max"] for s in cell_stations))
            tel_mean = float(np.mean([s["level_mean"] for s in cell_stations]))
            logger.info(f"Grid {zone_id} contains {tel_count} telemetry stations. Max level={tel_max:.2f}m")

        feature_records.append({
            "zone_id": zone_id,
            "latitude": c_lat,
            "longitude": c_lon,
            
            # Rainfall
            "rainfall_mean": rain_mean,
            "rainfall_max": rain_max,
            "rainfall_24h_if_available": rain_24h,
            "rainfall_7d_if_available": rain_7d,
            "rainfall_historical_mean": rain_hist_mean,
            
            # Elevation
            "elevation_mean": elev_mean,
            "elevation_min": elev_min,
            "elevation_max": elev_max,
            
            # Slope
            "slope_mean": slope_mean,
            
            # Land Cover
            "built_up_pct": built_up_pct,
            "green_cover_pct": green_cover_pct,
            
            # Hydrological & Proximity
            "distance_to_water": distance_to_water,
            "distance_to_drainage": distance_to_drainage,
            "drainage_density": drainage_density,
            
            # Roads
            "road_density": road_density,
            
            # Telemetry (Open Question additions)
            "telemetry_stations_count": tel_count,
            "river_level_historical_max": tel_max,
            "river_level_historical_mean": tel_mean,
            
            # Flood label
            "flood_label": flood_label
        })

    # Save Pune Master Feature Table (Section 11)
    proc_features_df = pd.DataFrame(feature_records)
    proc_features_path = os.path.join(processed_dir, "pune_spatial_features.csv")
    proc_features_df.to_csv(proc_features_path, index=False)
    logger.info(f"Saved master feature table to: {proc_features_path}")

    # Close rasters
    if r_elev:
        r_elev.close()
    if r_slope:
        r_slope.close()
    if r_lc:
        r_lc.close()

    # 9. Visual Validation Plotting (Section 14)
    logger.info("Generating visual validation maps under outputs/data_validation/...")
    val_plots_dir = "outputs/data_validation"
    os.makedirs(val_plots_dir, exist_ok=True)

    # 1. Rainfall Map (Maximum Daily Rainfall per grid point)
    plt.figure(figsize=(8, 6))
    plt.scatter(proc_features_df["longitude"], proc_features_df["latitude"], 
                c=proc_features_df["rainfall_max"], cmap="Blues", s=500, edgecolor="black")
    plt.colorbar(label="Max Daily Rainfall (mm)")
    for _, r in proc_features_df.iterrows():
        plt.text(r["longitude"], r["latitude"] + 0.02, f"{r['zone_id']}\n({r['rainfall_max']:.1f} mm)", 
                 ha="center", fontsize=9, fontweight="bold")
    plt.title("Rainfall Spatial Distribution (Max Daily Rainfall)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.xlim(MIN_LON - 0.05, MAX_LON + 0.05)
    plt.ylim(MIN_LAT - 0.05, MAX_LAT + 0.05)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.savefig(os.path.join(val_plots_dir, "rainfall_map.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # 2. Elevation Map
    plt.figure(figsize=(8, 6))
    if os.path.exists(proc_elev):
        try:
            with rasterio.open(proc_elev) as r:
                elev_img = r.read(1)
                extent = [r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top]
                # mask nodata
                elev_img = np.where(elev_img == r.nodata, np.nan, elev_img)
                plt.imshow(elev_img, cmap="terrain", extent=extent)
                plt.colorbar(label="Elevation (meters)")
        except Exception as e:
            logger.error(f"Error plotting elevation raster: {e}")
    plt.title("Pune Digital Elevation Model (DEM)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.savefig(os.path.join(val_plots_dir, "elevation_map.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # 3. Land Cover Map
    plt.figure(figsize=(8, 6))
    if os.path.exists(proc_lc):
        try:
            with rasterio.open(proc_lc) as r:
                lc_img = r.read(1)
                extent = [r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top]
                lc_img = np.where(lc_img == r.nodata, np.nan, lc_img)
                plt.imshow(lc_img, cmap="tab10", extent=extent)
                plt.colorbar(label="ESA class code")
        except Exception as e:
            logger.error(f"Error plotting landcover raster: {e}")
    plt.title("Pune Land Cover Classification (ESA WorldCover)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.savefig(os.path.join(val_plots_dir, "landcover_map.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # 4. Drainage & Waterways Overlay Map
    plt.figure(figsize=(8, 6))
    if not gdf_natural_water.empty:
        gdf_natural_water.plot(ax=plt.gca(), color="blue", linewidth=1.5, label="Waterways (River/Stream)")
    if not gdf_drainage.empty:
        gdf_drainage.plot(ax=plt.gca(), color="cyan", linewidth=1.0, linestyle="--", label="Drainage (Canal/Drain)")
    plt.title("Pune Waterways & Drainage Networks Overlay")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.savefig(os.path.join(val_plots_dir, "drainage_map.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # 5. Spatial Units Overlay and Flood Events Map
    plt.figure(figsize=(8, 6))
    # Plot cell bounding boxes
    for cell in grid_cells:
        c_lat = cell["center_lat"]
        c_lon = cell["center_lon"]
        lat_min, lat_max = c_lat - 0.125, c_lat + 0.125
        lon_min, lon_max = c_lon - 0.125, c_lon + 0.125
        # draw box outline
        plt.plot([lon_min, lon_max, lon_max, lon_min, lon_min], 
                 [lat_min, lat_min, lat_max, lat_max, lat_min], 
                 color="purple", linestyle="--", linewidth=1.5)
        plt.text(c_lon, c_lat, cell["zone_id"], ha="center", va="center", color="purple", fontsize=12, fontweight="bold")
    
    # Overlay flood events
    if len(flood_events) > 0:
        event_lats = [e["geometry"].y for e in flood_events]
        event_lons = [e["geometry"].x for e in flood_events]
        plt.scatter(event_lons, event_lats, color="red", marker="x", s=100, label="Flood Events", zorder=5)
        
    plt.title("Pune Spatial Units & Historical Flood Events Overlay")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.xlim(MIN_LON - 0.05, MAX_LON + 0.05)
    plt.ylim(MIN_LAT - 0.05, MAX_LAT + 0.05)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.savefig(os.path.join(val_plots_dir, "spatial_units_map.png"), dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Visual validation maps generated successfully.")
    logger.info("Pune spatial data preparation phase completed successfully.")

if __name__ == "__main__":
    main()
