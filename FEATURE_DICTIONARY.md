# Feature Dictionary

This document defines every variable present in the final Master Feature Table ([`pune_spatial_features.csv`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/processed/pune_spatial_features.csv)).

## 1. Identifiers & Geolocation

### `zone_id`
- **Meaning**: Unique identifier for the spatial grid unit.
- **Source**: System-defined.
- **Unit**: String (e.g. `PUNE_G001`).
- **Calculation**: Sequential index matching the 0.25° grid layout.

### `latitude`
- **Meaning**: Latitude coordinate of the cell centroid.
- **Source**: IMD gridded metadata.
- **Unit**: Degrees North (WGS 84).

### `longitude`
- **Meaning**: Longitude coordinate of the cell centroid.
- **Source**: IMD gridded metadata.
- **Unit**: Degrees East (WGS 84).

---

## 2. Rainfall features

### `rainfall_mean` / `rainfall_historical_mean`
- **Meaning**: Long-term mean daily rainfall.
- **Source**: IMD daily NetCDF (2015–2025).
- **Unit**: Millimeters (mm).
- **Calculation**: Mean of daily rainfall values over the 11-year dataset for the cell.
- **Significance**: Establishes the baseline wetness / climatological average.

### `rainfall_max`
- **Meaning**: Maximum daily rainfall observed historically.
- **Source**: IMD daily NetCDF (2015–2025).
- **Unit**: Millimeters (mm).
- **Calculation**: Maximum single-day rainfall value.
- **Significance**: Identifies the worst-case extreme rainfall event for design/stress-test.

### `rainfall_24h_if_available`
- **Meaning**: Representative current 24-hour rainfall.
- **Source**: IMD daily NetCDF.
- **Unit**: Millimeters (mm).
- **Calculation**: Daily rainfall value of the last recorded date in the series.

### `rainfall_7d_if_available`
- **Meaning**: Maximum 7-day rolling accumulated rainfall.
- **Source**: IMD daily NetCDF (2015–2025).
- **Unit**: Millimeters (mm).
- **Calculation**: Max value of the 7-day rolling sum.
- **Significance**: Indicator of soil saturation and antecedent moisture capacity.

---

## 3. Terrain & Topography

### `elevation_mean`
- **Meaning**: Average elevation above sea level.
- **Source**: USGS SRTM DEM (30m).
- **Unit**: Meters (m).
- **Calculation**: Mean elevation of valid DEM pixels falling within the cell boundaries.
- **Significance**: Higher areas are generally less vulnerable to pooling than low-lying valleys.

### `elevation_min`
- **Meaning**: Minimum elevation.
- **Source**: USGS SRTM DEM (30m).
- **Unit**: Meters (m).
- **Calculation**: Minimum pixel value.
- **Significance**: Low points are likely collection zones for gravity-driven water pooling.

### `elevation_max`
- **Meaning**: Maximum elevation.
- **Source**: USGS SRTM DEM (30m).
- **Unit**: Meters (m).
- **Calculation**: Maximum pixel value.

### `slope_mean`
- **Meaning**: Mean terrain slope.
- **Source**: Derived from SRTM DEM.
- **Unit**: Degrees (°).
- **Calculation**: Mean slope angle within the cell boundaries.
- **Significance**: Steep slopes increase surface runoff speed; flat plains slow water down, increasing waterlogging duration.

---

## 4. Land Cover & Urbanization

### `built_up_pct`
- **Meaning**: Built-up / impervious surface coverage percentage.
- **Source**: ESA WorldCover (10m).
- **Unit**: Percentage (%).
- **Calculation**: Percentage of pixels belonging to class `50` (built-up) inside the cell.
- **Significance**: Reflects concrete fraction which reduces water infiltration, dramatically increasing surface runoff.

### `green_cover_pct`
- **Meaning**: Vegetation/green cover percentage.
- **Source**: ESA WorldCover (10m).
- **Unit**: Percentage (%).
- **Calculation**: Percentage of pixels belonging to classes `10` (tree cover), `20` (shrubland), or `30` (grassland).
- **Significance**: High vegetative cover increases infiltration and slows down flash flooding.

---

## 5. Hydrological & Built Infrastructure

### `distance_to_water`
- **Meaning**: Shortest distance to natural rivers or streams.
- **Source**: OSM waterways database.
- **Unit**: Meters (m).
- **Calculation**: Distance from grid center point to nearest river/stream line segment (projected UTM 43N).
- **Significance**: Proximity to major rivers increases risk of riverine overflow.

### `distance_to_drainage`
- **Meaning**: Shortest distance to man-made drainage or canals.
- **Source**: OSM waterways database.
- **Unit**: Meters (m).
- **Calculation**: Distance from grid center point to nearest canal/drain line segment (projected UTM 43N).
- **Significance**: Proximity to storm drains helps direct drainage, but congested drains cause backflow.

### `drainage_density`
- **Meaning**: Length of drainage channels per unit area.
- **Source**: OSM waterways database.
- **Unit**: Meters / km².
- **Calculation**: Total length of canals and drains in meters inside the cell divided by cell area in km².
- **Significance**: High drainage density suggests well-channeled water discharge capacity.

### `road_density`
- **Meaning**: Length of road network per unit area.
- **Source**: OSM road network graph.
- **Unit**: Meters / km².
- **Calculation**: Total length of road edges in meters inside the cell divided by cell area in km².
- **Significance**: Serves as a proxy for urban density and runoff barriers.

---

## 6. Historical Level Telemetry & Flood Labels

### `telemetry_stations_count`
- **Meaning**: Count of river telemetry monitoring stations.
- **Source**: CWC Hourly Telemetry dataset.
- **Unit**: Integer.
- **Calculation**: Count of station points falling within the cell.

### `river_level_historical_max`
- **Meaning**: Highest river water level recorded.
- **Source**: CWC Hourly Telemetry (2021-2025).
- **Unit**: Meters (m).
- **Calculation**: Max water level recorded across stations inside the cell boundaries.
- **Significance**: Identifies historical high-water marks.

### `river_level_historical_mean`
- **Meaning**: Mean river water level.
- **Source**: CWC Hourly Telemetry (2021-2025).
- **Unit**: Meters (m).
- **Calculation**: Average river level across stations inside the cell.

### `flood_label`
- **Meaning**: Count of historical flood occurrences inside the spatial unit.
- **Source**: IMD Historical Flood log.
- **Unit**: Integer (event count).
- **Calculation**: Count of event points falling inside the cell boundaries.
- **Significance**: Target / validation flag for vulnerability validation.
