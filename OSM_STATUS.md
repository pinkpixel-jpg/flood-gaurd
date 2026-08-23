# OSM Data Status Report

Updated: 2026-08-22 (after Overpass outage audit)

## 1. Current Download Environment Status

Public Overpass endpoints are currently unreliable from this environment:

| Endpoint | Result |
| :--- | :--- |
| `overpass-api.de` | Connect timeout (>100 s), even for tiny queries |
| `overpass.kumi.systems` | HTTP 500 / read timeout |
| `maps.mail.ru/osm/tools/overpass` | Not reachable in timeboxed test |

Decision: road layer marked **UNAVAILABLE**, not zero. No infinite retries.
The pipeline continues without roads until a reliable source/window exists.

## 2. Road Datasets Found In Project (AUDIT)

### 1. `city_roads/pune_roads.graphml.xml`
- Type: **RAW OSM** (OSMnx GraphML drive network)
- Size / nodes: 22.8 MB / 23,483 nodes
- Coverage: lon 73.78000–73.92000, lat 18.45000–18.57998
- Verdict: **CENTRAL-PUNE-ONLY. Does NOT cover the study bbox.**

### 2. `hehehackathon/city_roads/pune_roads.graphml.xml`
- Identical duplicate of #1 (md5 `a3ed4657b0af`). Same central-only coverage.

### 3. `hehehackathon/pune_roads.graphml`
- Same node set/bounds as #1 (different serialization md5). Also **CENTRAL-PUNE-ONLY**.

### 4. `data/processed/pune_roads.geojson`
- Type: **PROCESSED/DERIVED** (edges extracted from #1 by the earlier pipeline)
- 54,277 line features, EPSG:4326
- Coverage: lon 73.77990–73.92000, lat 18.44999–18.57999
- Verdict: **CENTRAL-PUNE-ONLY derivative. NOT complete Pune coverage.**

### ❌ NO complete-Pune road dataset exists anywhere in the project.
None of the above covers the study area (73.60–74.10 E, 18.30–18.75 N).
No fabricated replacement will be created. Central-Pune data will never be
labelled as full coverage.

## 3. Waterways & Drainage

Previously downloaded successfully from Overpass (full study bbox request,
2026-08-22). **PRESERVED AND USED:**

| File | Features | Notes |
| :--- | :--- | :--- |
| `data/raw/osm/pune_waterways_raw.geojson` | 376 | raw fetch incl. element types & full geometries of bbox-intersecting ways |
| `data/processed/pune_waterways.geojson` | 247 | lines only |
| `data/processed/pune_drainage.geojson` | 89 | lines only |

NOTE (category split): current files use the older split
(waterways = river/stream; drainage = canal/drain/ditch). The revised
specification (waterways = river/stream/canal; drainage = drain/ditch)
will be applied by an offline re-split of `pune_waterways_raw.geojson`
during the next pipeline stage — no network required.

## 4. Required Pipeline Behaviour While Roads Are Missing

1. `road_density`, and any road-derived feature, must be emitted as
   **MISSING/UNKNOWN (NaN)** for all cells — never `0.0`.
2. Missing roads must not block DEM, WorldCover, IMD rainfall, CWC,
   flood-event, spatial-summary, or ML-dataset construction.
3. `osm_status.json` is the machine-readable source of truth:
   - `roads`: `"UNAVAILABLE"` (source-level failure)
   - `waterways`/`drainage`: `"OK"`

## 5. Recovery Options (for later, none blocking)

- Retry Overpass in a quieter window using the timeboxed quadrant script
  (`python -m src.build_osm_features --category roads` after tests pass).
- Alternative mirrors/endpoints, or a BBBike/Geofabrik regional extract,
  clipped offline to the study bbox.
