# Data Inventory

This document maps all the raw and processed spatial/climate datasets identified in the workspace.

## 1. Raw Datasets

| Dataset | File | Format | Source | Coverage | Spatial Resolution | Temporal Coverage | Important Variables | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IMD Rainfall** | [`RF25_indYEAR_rfp25.nc`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/) | NetCDF | IMD | India (clipped to Pune BBox) | 0.25° (~27 km) | 2015–2025 | `RAINFALL` (mm) | **READY** |
| **Elevation** | [`pune_elevation.tif`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/IHSA6_GIS/pune_elevation.tif) | GeoTIFF | USGS SRTM | Pune area | 30m | Static | Elevation (meters) | **READY** |
| **Slope** | [`pune_slope.tif`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/IHSA6_GIS/pune_slope.tif) | GeoTIFF | Derived | Pune area | 30m | Static | Slope (degrees) | **READY** |
| **Land Cover** | [`pune_landcover.tif`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/IHSA6_GIS/pune_landcover.tif) | GeoTIFF | ESA WorldCover | Pune area | 10m | Static (2021) | Map (classification code) | **READY** |
| **OSM Roads** | [`pune_roads.graphml.xml`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/city_roads/pune_roads.graphml.xml) | GraphML | OpenStreetMap | Pune area | Vector (Lines) | Static | Network geometry, node properties | **READY** |
| **OSM Waterways** | [`pune_waterways.gpkg`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/city_waterways/pune_waterways.gpkg) | GeoPackage | OpenStreetMap | Pune area | Vector (Lines) | Static | `waterway` type (river, stream, etc) | **READY** |
| **Hourly River Levels** | [`rwl_tel_hr_maharashtra_sw_007_2021_2025 (1).csv`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/rwl_tel_hr_maharashtra_sw_007_2021_2025%20(1).csv) | CSV | CWC | Maharashtra stations | Point stations | 2021–2025 | Hourly water level (meter) | **READY** |
| **Flood Events** | [`pune_flood_events.csv`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/pune_flood_events.csv) | CSV | IMD / local | Pune area | Points | 2014–2016 | `latitude`, `longitude`, `flood` | **READY** |

---

## 2. Processed Datasets (Output)

All processed outputs are saved inside the [`data/processed/`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/) directory.

| Dataset | File | Format | Description |
| :--- | :--- | :--- | :--- |
| **Master Feature Table** | [`pune_spatial_features.csv`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_spatial_features.csv) | CSV | Combined spatial grid features, rainfall stats, and flood counts (1 row per grid cell). |
| **Spatial Rainfall** | [`pune_rainfall_spatial.csv`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_rainfall_spatial.csv) | CSV | Daily historical rainfall time series for each of the 4 grid cells (2015-2025). |
| **Clipped DEM** | [`pune_elevation.tif`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_elevation.tif) | GeoTIFF | Elevation data cropped to the exact WGS84 bounding box of the study area. |
| **Clipped Slope** | [`pune_slope.tif`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_slope.tif) | GeoTIFF | Slope dataset cropped to the WGS84 bounding box of the study area. |
| **Clipped Land Cover** | [`pune_landcover.tif`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_landcover.tif) | GeoTIFF | ESA WorldCover land classification cropped to the study area (nodata value WGS84-compliant). |
| **Clipped Roads** | [`pune_roads.geojson`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_roads.geojson) | GeoJSON | Road segments falling inside Pune's study bounding box. |
| **Clipped Drainage** | [`pune_drainage.geojson`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_drainage.geojson) | GeoJSON | Man-made OSM drainage systems (canals and drains) within the study area. |
| **Clipped Waterways** | [`pune_waterways.geojson`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_waterways.geojson) | GeoJSON | Natural waterways (rivers and streams) within the study area. |
