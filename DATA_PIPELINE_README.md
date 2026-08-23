# Data Pipeline README

This document outlines the data preparation, projection, cleaning, clipping, and spatial aggregation pipeline used to generate the final ML-ready datasets for **Pune FloodShield**.

---

## Data Engineering Flow

```mermaid
graph TD
    %% Input Layer
    subgraph Raw Data Ingestion ("Raw Ingestion (hehehackathon/)")
        A[IMD Rainfall NetCDF]
        B[USGS DEM GeoTIFF]
        C[OSM Roads GraphML]
        D[OSM Waterways GPKG]
        E[CWC River Telemetry CSV]
        F[IMD Flood Events CSV]
    end

    %% Pipeline Processing
    subgraph Pipeline Logic ("Pipeline Engine (pune_gis_pipeline.py)")
        G[Rainfall Quality Audit & Gap Check]
        H[Coordinate Standardization: Reproject to UTM 43N]
        I[Study Area Raster & Vector Spatial Clipping]
        J[Spatial Zonal Aggregation per Grid Cell]
    end

    %% Processed Outputs
    subgraph Processed Datasets ("Processed Outputs (data/processed/)")
        K[pune_spatial_features.csv]
        L[pune_rainfall_spatial.csv]
        M[pune_elevation.tif / pune_slope.tif / pune_landcover.tif]
        N[pune_roads.geojson / pune_drainage.geojson / pune_waterways.geojson]
    end

    %% Visual Validation
    subgraph Visual Validation ("Outputs (outputs/data_validation/)")
        O[Rainfall, DEM, Land Cover, Roads, and Water Overlay Maps]
    end

    %% Connections
    A & B & C & D & E & F --> G
    G --> H
    H --> I
    I --> J
    J --> K
    J --> L
    J --> M
    J --> N
    J --> O
```

---

## Pipeline Execution

To execute the entire data engineering and validation pipeline:

```bash
python -m src.pune_gis_pipeline
```

### Steps Executed Automatically:

1. **Raw Ingestion & Verification**: 
   Reads original raw spatial datasets from the `hehehackathon` folder. Verify coordinate compliance.
2. **Rainfall Quality Validation**: 
   Audits the NetCDF gridded files for coordinates, temporal completeness, and anomalies (NaN or negative counts).
3. **CRS Standardization**: 
   Standardizes geographic inputs (`EPSG:4326`) to the conformal projected coordinate reference system **UTM Zone 43N** (`EPSG:32643`) for Pune.
4. **Spatial Clipping**: 
   Clips rasters and clips/filters vectors (separating waterways into natural rivers/streams and man-made canals/drains) to Pune's spatial bounds `[73.60, 18.30, 74.10, 18.75]`.
5. **Zonal Extraction & Feature Engineering**: 
   - Computes spatial stats for rasters (elevation min/mean/max, mean slope, built-up %, and vegetative green cover %) per cell extent.
   - Calculates density metrics (road and drainage density in $\text{meters}/\text{km}^2$) and shortest proximity distance in meters from cell centers to waterways/drainage.
   - Summarizes hourly telemetry river water levels (mean/max) for active stations inside each cell.
   - Aggregates historical flood events to calculate target event counts.
6. **Master Compilation**: 
   Saves the aggregated master feature table `pune_spatial_features.csv` (1 row per grid cell) and daily timeseries table `pune_rainfall_spatial.csv`.
7. **Validation Mapping**: 
   Saves 5 validation maps under `outputs/data_validation/`.
