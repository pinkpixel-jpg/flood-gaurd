# Coordinate Reference System (CRS) Report

Spatial calculations (like densities and shortest distances) require distance metrics in meters. This document lists the coordinate transformations implemented in our pipeline.

| Dataset | Original CRS | Processing CRS | Reason |
| :--- | :--- | :--- | :--- |
| **IMD Rainfall** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Needed to reproject grid cell centroids to UTM for distance-to-water and distance-to-drainage queries. |
| **Elevation (DEM)** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Re-projected cell bounding boxes to UTM 43N to extract elevation bounds in a uniform spatial coordinate system. |
| **Slope** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Re-projected cell bounding boxes to UTM 43N to compute mean terrain slope. |
| **Land Cover** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Re-projected cell bounding boxes to UTM 43N to compute percentages of land classification. |
| **OSM Roads** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Compiling total road length in meters requires lines to be in projected coordinates. Used to calculate Road Density ($\text{meters}/\text{km}^2$). |
| **OSM Waterways** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Required for computing shortest distance from cell centers to rivers/streams in meters. |
| **OSM Drainage** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Required for computing Drainage Density ($\text{meters}/\text{km}^2$) and shortest distance from cell centers to drains in meters. |
| **River Levels** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Used to overlay telemetry station points on WGS84 cell shapes. |
| **Flood Events** | `EPSG:4326` (WGS 84) | `EPSG:32643` (UTM 43N) | Used to overlay flood event points on WGS84 cell shapes. |

### Justification for Projected CRS Selection:
We selected **WGS 84 / UTM Zone 43N** (EPSG code **`32643`**) because the Pune study area is located between $73.60^{\circ}\text{ E}$ and $74.10^{\circ}\text{ E}$ longitude and $18.30^{\circ}\text{ N}$ and $18.75^{\circ}\text{ N}$ latitude. UTM Zone 43N covers all areas between $72^{\circ}\text{ E}$ and $78^{\circ}\text{ E}$ in the northern hemisphere, minimizing distortion for distance and area calculations.
