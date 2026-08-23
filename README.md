# Rainfall Intelligence: Dataset Preparation (Level 1 & Level 2)

A professional, configuration-driven time-series and geospatial data preparation pipeline. It ingests historical India Meteorological Department (IMD) daily gridded rainfall NetCDF datasets (2015–2025) and builds cleaned, validated, feature-engineered datasets.

---

## 1. Dual-Level Pipeline Architecture

The pipeline supports two levels of dataset outputs:

### LEVEL 1 — Multi-City Dataset (Scalability & Comparison)
*   **Purpose**: Cross-city rainfall profiling and validation.
*   **Cities**: Pune, Mumbai, Nashik, Nagpur, Bengaluru, Delhi, Chennai, Hyderabad.
*   **Extraction**: Mapped to the nearest land-masked valid grid coordinate.
*   **Feature Grouping**: Performed on column `City` to prevent cross-city leakage.

### LEVEL 2 — Hyperlocal Pune Spatial Dataset (Flood Risk & GIS Mapping)
*   **Purpose**: Spatially localized modeling for urban waterlogging and flood warning systems in Pune.
*   **Bounding Box**: Configurable in `data/config/pune_bbox.json`:
    - Latitude: 18.30 to 18.75
    - Longitude: 73.60 to 74.10
*   **Grid Cells**: Preserves all 4 IMD cells within Pune's bounding box as separate time-series:
    - `PUNE_01`: (18.50° N, 73.75° E) — matches Level 1 Pune grid location.
    - `PUNE_02`: (18.50° N, 74.00° E)
    - `PUNE_03`: (18.75° N, 73.75° E)
    - `PUNE_04`: (18.75° N, 74.00° E)
*   **Feature Grouping**: Performed on column `Grid_ID` to prevent cross-grid leakage.

---

## 2. Directory Structure

```
hackathon/
│
├── data/
│   ├── config/
│   │   ├── cities.csv                      # Level 1 city coordinates list
│   │   ├── pune_bbox.json                  # Level 2 bounding box config
│   │   └── rainfall_thresholds.json        # IMD rainfall category thresholds
│   ├── raw/
│   │   ├── imd/                            # Raw NetCDF files (2015-2025)
│   │   └── elevation/                      # SRTM elevation files (optional geotiff)
│   ├── intermediate/
│   └── processed/
│       ├── multi_city_rainfall_2015_2025.csv # Level 1 final training dataset
│       ├── rainfall_base_2015_2025.csv       # Level 1 base extracted dataset
│       ├── rainfall_training_dataset_2015_2025.csv # Level 1 duplicate check copy
│       ├── yearly_rainfall_statistics.csv    # Level 1 annual stats
│       ├── monthly_rainfall_statistics.csv   # Level 1 monthly stats
│       ├── city_elevation.csv                # Level 1 elevation stats
│       │
│       └── pune/                             # LEVEL 2 (PUNE HYPERLOCAL)
│           ├── pune_spatial_rainfall_2015_2025.csv # Base grid * date observations
│           ├── pune_grid_metadata.csv        # Stable cell coordinate lookup
│           ├── pune_grid_elevation.csv       # Extracted heights per Grid_ID
│           ├── pune_grid_statistics.csv      # Cell-wise long-term metrics
│           ├── pune_historical_flood_events.csv # Placeholder flood events schema
│           └── pune_training_dataset.csv     # Final feature-engineered spatial dataset
│
├── src/
│   ├── data_loader.py                      # Config and NetCDF loaders
│   ├── rainfall_extractor.py               # Spatial nearest-neighbor (land-masked)
│   ├── pune_spatial_extractor.py           # BBox gridded cell extractor
│   ├── data_cleaning.py                    # Cleaning validations & quality reporting
│   ├── feature_engineering.py               # Temporal, lag, rolling features (group-aware)
│   ├── elevation_extractor.py               # Samples heights from SRTM GeoTIFF
│   ├── dataset_validator.py                # Final 10-point validation suite
│   ├── build_dataset.py                    # Level 1 pipeline orchestrator
│   └── pune_build_dataset.py               # Level 2 pipeline orchestrator
│
├── reports/
│   ├── data_quality_report.csv             # Level 1 profile metrics
│   ├── dataset_summary.txt                 # Level 1 quality report text
│   ├── final_dataset_validation.txt        # Level 1 10-point check log
│   ├── pune_validation.txt                 # Level 1 Pune validation log
│   │
│   └── pune_spatial_validation.txt         # LEVEL 2 PUNE SPATIAL VALIDATION LOG
│
└── outputs/
    ├── datasets/
    └── figures/
        ├── annual_rainfall.png             # Level 1 annual total lines
        ├── monthly_rainfall.png            # Level 1 monthly daily means
        ├── rainfall_distribution.png       # Level 1 log intensity histograms
        ├── pune_rainfall_heatmap.png       # Level 1 Pune Year x Month heatmap
        ├── extreme_events.png              # Level 1 top event bar chart
        │
        ├── pune_grid_map.png               # Level 2 Grid cell scatter map
        ├── pune_avg_rainfall_map.png       # Level 2 Average daily rainfall map
        ├── pune_max_rainfall_map.png       # Level 2 Maximum daily rainfall map
        ├── pune_annual_rainfall_trend.png  # Level 2 Annual total trends
        ├── pune_monthly_rainfall_climatology.png # Level 2 Monthly daily means
        ├── pune_heatmap.png                # Level 2 Heatmap (spatial average)
        └── pune_extreme_events_spatial.png # Level 2 spatial extreme events list
```

---

## 3. Data Leakage Prevention

All rolling and lag features are shifted by 1 day before calculations to mathematically ensure that features for date $t$ only contain data from days $\le t-1$.
- **Lags**: Lag 1D, 3D, 7D, 14D represent shifted historical daily metrics.
- **Shifted Rolling**: rolling mean/sum (3D, 7D, 14D, 30D) are computed using `shift(1)` to prevent look-ahead leaks.
- **Consecutive Dry Days**: counts consecutive dry days ending on date $t-1$.
- **Peak Descriptors**: `Annual_Max_Rainfall` and `Monthly_Max_Rainfall` are descriptive columns for climate analysis and must **not** be fed to models during predictive training.

---

## 4. Scientific Category Thresholds

Categories are defined in `data/config/rainfall_thresholds.json` using the India Meteorological Department (IMD) daily thresholds:
- **Dry**: $= 0.0$ mm
- **Light**: $> 0.0$ mm and $\le 15.5$ mm
- **Moderate**: $> 15.5$ mm and $\le 64.4$ mm
- **Heavy**: $> 64.4$ mm and $\le 115.5$ mm
- **Extreme**: $> 115.5$ mm

---

## 5. Execution Instructions

Ensure dependencies are installed:
```bash
pip install xarray netCDF4 pandas numpy matplotlib
```

To run the **Level 1 (8-City) Pipeline**:
```bash
python -m src.build_dataset
```

To run the **Level 2 (Pune Hyperlocal Spatial) Pipeline**:
```bash
python -m src.pune_build_dataset
```

This will run all filters, extract cells, compute features, perform validation verification, output datasets to `data/processed/pune/`, and write verification reports and figures.
