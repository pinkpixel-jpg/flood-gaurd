# Data Provenance Report — Pune FloodShield ML Dataset

Updated: 2026-08-22. Every feature traces to a REAL source or a reproducible
derivation from real data. No hardcoded GIS values exist in the pipeline.

## 1. Source Datasets

| Source | File(s) | Native Resolution | Coverage Used |
| :--- | :--- | :--- | :--- |
| IMD daily gridded rainfall (RF25) | `data/raw/imd/RF25_ind20??_rfp25.nc` (11 files) | 0.25° (~27 km), daily | 4 cells × 2015-01-01..2025-12-31 |
| NASA SRTM DEM | `hehehackathon/IHSA6_GIS/N18E073.tif`, `N18E074.tif` | ~30 m (1 arc-sec), int16, nodata −32768 | merged → clipped to study bbox |
| ESA WorldCover 2021 v200 | repaired clip from public S3 COG `ESA_WorldCover_10m_2021_v200_N18E072_Map.tif` (windowed read; corrupt original preserved untouched at `hehehackathon/IHSA6_GIS/pune_landcover_full.tif`) | ~10 m (8.33e-5°), uint8, nodata 0 | exactly 73.60–74.10 E × 18.30–18.75 N |
| OSM waterways/drainage | `data/raw/osm/pune_waterways_raw.geojson` (376 feats, Overpass fetch 2026-08-22) | vector lines, EPSG:4326 | full study bbox |
| CWC river-level telemetry | `hehehackathon/rwl_tel_hr_maharashtra_sw_007_2021_2025 (1).csv` (2,015,253 rows) | hourly/15-min point stations, metres | 45 stations audited; 4 lie inside study cells |
| Historical flood events | `data/flood_events/pune_flood_events.csv` | points + dates | 5 verified events |

Spatial unit (unchanged, see SPATIAL_UNIT_DECISION.md): IMD 0.25° grid cells
PUNE_G001..G004 centred at (18.50/18.75 N × 73.75/74.00 E); feature domain =
cell ∩ study bounding box.

## 2. Feature Provenance (final dataset columns)

### Keys & calendar
| Feature | Derivation | Units / Values |
| :--- | :--- | :--- |
| `Date`, `Grid_ID`, `Latitude`, `Longitude` | IMD extraction (existing validated pipeline) | date, id, °N, °E |
| `year`, `month`, `day`, `dayofyear` | calendar decomposition of Date | ints |
| `is_monsoon` | month ∈ {Jun..Sep} | 0/1 |

### Rainfall dynamics (source: IMD)
| Feature | Derivation | Missing |
| :--- | :--- | :--- |
| `rainfall_1d` | daily rainfall at t | none |
| `rainfall_{3,7,14,30}d` | rolling sums incl. current day t−(w−1)..t; STRICT window (`min_periods=w`) | first w−1 days/cell NaN by design |
| `monthly_rainfall_to_date` | cumsum within (cell, calendar month) | none |
| `monsoon_rainfall_to_date` | cumsum from Jun 1 within year | NaN outside Jun 1–Dec 31 season start (non-monsoon months = NaN) |
| `hist_mean_prior_years_mm` | per-cell mean over ALL years strictly BEFORE current year | 2015 = NaN (no prior year) |
| `hist_max_prior_years_mm` | same, max | 2015 = NaN |
| `month_clim_mean_prior_years_mm` | per cell×month mean over prior years only | 2015 = NaN |
| `rainfall_anomaly_mm` | `rainfall_1d − hist_mean_prior_years_mm` | inherits 2015 NaN |

### Static terrain (SRTM, derived slope)
| Feature | Derivation |
| :--- | :--- |
| `elevation_mean/min/max_m` | zonal stats over cell∩bbox from clipped DEM (29 m px) |
| `slope_mean/min/max_deg` | Horn 3×3 slope computed from REAL DEM (`src/build_dem.py`), then zonal stats |

### Static land surface (WorldCover v200 2021 classes)
| Feature | Classes used |
| :--- | :--- |
| `built_up_pct` | class 50 (Built-up) |
| `vegetation_pct` | classes 10 Tree cover + 20 Shrubland + 30 Grassland |
| `water_cover_pct` | class 80 (Permanent water bodies) |
| `cropland_pct` | class 40 (Cropland) |

### Hydrology / infrastructure (OSM, UTM 43N metric ops)
| Feature | Derivation | Interpretation rule |
| :--- | :--- | :--- |
| `distance_to_nearest_waterway_m` | min distance cell-centre→river/stream/canal lines (projected EPSG:32643) | NaN only if layer empty |
| `waterway_length_m` | total mapped length intersecting cell∩bbox | 0 = no mapped line inside cell (verified count logged); NOT proof of absence |
| `distance_to_nearest_drainage_m`, `drainage_length_m` | same for drain/ditch | same rule; G003/G004 have genuinely 0 mapped drains in OSM |
| `road_density` | **UNAVAILABLE** — complete Pune road data does not exist; central-Pune-only graphml explicitly rejected | 100 % NaN by policy (`osm_status.json`) |

### River level (CWC telemetry — companion features)
| Feature | Derivation |
| :--- | :--- |
| `cwc_stations_in_cell` | # stations located inside that cell (Dattawadi, Pimpale Gurav → G001; Nighoje → G003; Koregaon Bhima → G004). G002 has NO station → its river-level features are always NaN |
| `river_level_daily_mean/max_m` | station-day aggregation → cell-day mean of station means/maxes; source sampling 15–60 min, units metres |
| Companion file | `data/processed/pune_cwc_daily.csv` (per-station daily, 3,398 station-days, Feb-2022→Dec-2024) |

### Flood label (VERIFIED events only)
| Feature | Derivation |
| :--- | :--- |
| `flood_event_active` | 1 ONLY on date×cell rows matching a recorded event's [start,end] at its mapped location. 5 positive rows: 2015-06-23, 2015-07-20, 2016-07-01..03 (all PUNE_G004). The two 2014 events precede the rainfall record (labelled 0 rows). NO threshold-based, synthetic, or interpolated labels exist anywhere. |

## 3. Reproducibility

Pipeline order (all deterministic, no manual steps):
1. `python -m src.build_dem` (SRTM merge → slope)
2. `python -m src.build_landcover` (verify-or-repair WorldCover)
3. `python -m src.build_spatial_features` (static cell features; re-splits OSM categories offline)
4. `python -m src.build_ml_dataset` (this dataset + validation)

Environment: Python 3.10; rasterio 1.4.4, geopandas 1.1.4, osmnx 2.0.7,
pandas 2.2.3, numpy 2.2.6, xarray/netCDF4.
