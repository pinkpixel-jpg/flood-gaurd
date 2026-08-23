# Spatial Unit Decision Report

To train a robust machine learning vulnerability model, we must establish a consistent spatial coordinate system. This document outlines our chosen unit and aggregation logic.

---

## 1. Selected Spatial Unit

We have selected the **0.25° gridded grid cells** as our **Master Spatial Unit**.

Specifically, our study area in Pune is divided into **4 grid cells**:
1. **`PUNE_G001`**: Centered at $18.50^{\circ}\text{ N}$, $73.75^{\circ}\text{ E}$ (covering $18.375^{\circ}$–$18.625^{\circ}\text{ N}$, $73.625^{\circ}$–$73.875^{\circ}\text{ E}$).
2. **`PUNE_G002`**: Centered at $18.50^{\circ}\text{ N}$, $74.00^{\circ}\text{ E}$ (covering $18.375^{\circ}$–$18.625^{\circ}\text{ N}$, $73.875^{\circ}$–$74.125^{\circ}\text{ E}$).
3. **`PUNE_G003`**: Centered at $18.75^{\circ}\text{ N}$, $73.75^{\circ}\text{ E}$ (covering $18.625^{\circ}$–$18.875^{\circ}\text{ N}$, $73.625^{\circ}$–$73.875^{\circ}\text{ E}$).
4. **`PUNE_G004`**: Centered at $18.75^{\circ}\text{ N}$, $74.00^{\circ}\text{ E}$ (covering $18.625^{\circ}$–$18.875^{\circ}\text{ N}$, $73.875^{\circ}$–$74.125^{\circ}\text{ E}$).

---

## 2. Justification for Selection

1. **Alignment with Climate Drivers**: 
   Rainfall is the primary dynamic driver of flooding. Our historical rainfall source (IMD gridded NetCDF dataset) has a native resolution of 0.25°. By setting the master spatial unit to match this grid, we prevent spatial scaling artifacts or artificial spatial interpolation of rainfall.
2. **Computational Feasibility**: 
   Aggregating fine-grained vector and raster layers (10m, 30m, and complex line graphs) to 4 large regions provides stable region-level baseline statistics.
3. **Prevention of Scale Leakage**:
   Ensures that every row in the dataset matches a physical unit of observation where the rainfall is uniform, avoiding the "One pixel = One row" mismatch.

---

## 3. Dimensions & Mapping Strategy

- **Approximate Cell Dimensions**: $\approx 27.5\text{ km} \times 26.1\text{ km}$ at Pune's latitude.
- **Approximate Cell Area**: $\approx 720\text{ km}^2$–$730\text{ km}^2$.
- **Projected Grid Cells**: The cell coordinates are transformed to UTM Zone 43N (`EPSG:32643`) to calculate area in square meters directly.
- **Mapping IMD Rainfall**: Daily rainfall time series map 1-to-1 to each cell based on the native coordinates in the NetCDF files.

---

## 4. Aggregation & Feature Calculation Formulas

### A. Raster Layers (USGS DEM, Slope, Land Cover)
We clip the rasters to the bounding box of each grid cell.
- **Topographic Statistics**: 
  $$\text{elevation\_mean} = \frac{1}{N}\sum_{i=1}^N z_i, \quad \text{slope\_mean} = \frac{1}{N}\sum_{i=1}^N s_i$$
  where $z_i$ and $s_i$ are valid pixel elevations/slopes (nodata values ignored).
- **Land Cover Fractions**:
  $$\text{built\_up\_pct} = \frac{\sum \text{pixels}(lc = 50)}{\sum \text{all\_pixels}} \times 100$$
  $$\text{green\_cover\_pct} = \frac{\sum \text{pixels}(lc \in \{10, 20, 30\})}{\sum \text{all\_pixels}} \times 100$$

### B. OSM Line Vectors (Roads, Drainage, Waterways)
We reproject the line features to UTM 43N (`EPSG:32643`).
- **Road & Drainage Density**:
  $$\text{Road Density} = \frac{\sum \text{Length of roads inside cell (meters)}}{\text{Cell area (km}^2\text{)}}$$
  $$\text{Drainage Density} = \frac{\sum \text{Length of canals/drains inside cell (meters)}}{\text{Cell area (km}^2\text{)}}$$
- **Shortest Proximity Distance**:
  We calculate the Euclidean distance from the projected cell center coordinate ($X_c, Y_c$) to the nearest line geometry segment:
  $$\text{distance\_to\_water} = \min \left( \text{distance}\big((X_c, Y_c), \text{waterways\_line}\big) \right)$$
  $$\text{distance\_to\_drainage} = \min \left( \text{distance}\big((X_c, Y_c), \text{drainage\_line}\big) \right)$$
  This metrics are in meters.
