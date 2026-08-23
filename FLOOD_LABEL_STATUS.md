# Flood Label Status Report

This document reports on the availability, reliability, coordinate locations, and limitations of historical flood labels inside the Pune study area.

## 1. Status Overview

- **Status**: **AVAILABLE** (PARTIAL Coverage)
- **Source File**: [`hehehackathon/pune_flood_events.csv`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/hehehackathon/pune_flood_events.csv) (original copies also exist in [`python_folder/`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/python_folder/) and copied to [`data/flood_events/`](file:///c:/Users/rashmi%20rahangdale/Desktop/hackathon/data/flood_events/)).
- **Total Event Records**: 5 historical events.
- **Source Agency**: India Meteorological Department (IMD) / Local Municipal Logs.

---

## 2. Event Log Details

| Event ID | Start Date | End Date | Cause | Latitude | Longitude | Grid Mapping |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **256** | 2014-04-19 | 2014-04-19 | Heavy rains | 18.641545 | 73.918491 | `PUNE_G004` |
| **260** | 2014-08-05 | 2014-08-05 | Heavy rains | 18.641545 | 73.918491 | `PUNE_G004` |
| **60** | 2015-06-23 | 2015-06-23 | Heavy rains | 18.641545 | 73.918491 | `PUNE_G004` |
| **61** | 2015-07-20 | 2015-07-20 | Heavy rains | 18.641545 | 73.918491 | `PUNE_G004` |
| **177** | 2016-07-01 | 2016-07-03 | Heavy rain | 18.641545 | 73.918491 | `PUNE_G004` |

---

## 3. Spatial Aggregation & Verification

- The coordinates for all 5 events are exactly identical: Latitude `18.641545328302172`, Longitude `73.9184912533744`.
- Grid cell bounding box containment check:
  - Latitude `18.641545` falls within `PUNE_G004` limits `[18.625, 18.875]`.
  - Longitude `73.918491` falls within `PUNE_G004` limits `[73.875, 74.125]`.
- Output: Cell `PUNE_G004` contains exactly **5** historical event records. Cells `PUNE_G001`, `PUNE_G002`, and `PUNE_G003` contain **0** events.

---

## 4. Key Data Limitations & Gaps

1. **High Spatial Clustering**: 
   All historical events in the dataset point to the exact same coordinate location. This suggests a central municipal logging station coordinate was used as a catch-all coordinate for the district instead of mapping the precise streets/wards that suffered inundation.
2. **Temporal Gap**: 
   The records only cover the years 2014–2016. There are no flood labels recorded for extreme rain events between 2017 and 2025.
3. **Implications for Machine Learning**:
   Because of these limitations, using `flood_label` directly as a target class in a supervised classification model will lead to severe overfitting or spatial bias. We recommend treating this dataset as a **partial target check** or using unsupervised vulnerability mapping (combining slope, DEM, and built-up density) instead.
