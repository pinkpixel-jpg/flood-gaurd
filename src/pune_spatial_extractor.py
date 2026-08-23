import os
import json
import logging
import pandas as pd
import xarray as xr
from typing import List, Tuple, Dict
from src.data_loader import load_yearly_netcdf

logger = logging.getLogger(__name__)

def load_pune_bbox(filepath: str = "data/config/pune_bbox.json") -> Dict[str, float]:
    """
    Loads Pune bounding box coordinates from a json config file.
    """
    if not os.path.exists(filepath):
        # Default fallback to requested coordinates
        logger.warning(f"Pune bounding box config not found at: {filepath}. Using defaults.")
        return {
            "min_lat": 18.30,
            "max_lat": 18.75,
            "min_lon": 73.60,
            "max_lon": 74.10
        }
    with open(filepath, "r") as f:
        return json.load(f)

def extract_pune_spatial_rainfall(years: List[int], raw_dir: str = "data/raw/imd") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ingests daily rainfall for all grid cells falling inside Pune's bounding box.
    Returns:
        pune_spatial_df: Daily rainfall dataset for each grid cell.
        grid_metadata_df: stable grid coordinate-ID lookup table.
    """
    bbox = load_pune_bbox()
    min_lat, max_lat = bbox["min_lat"], bbox["max_lat"]
    min_lon, max_lon = bbox["min_lon"], bbox["max_lon"]
    
    # Verify coordinates fall within IMD limits
    if min_lat < 6.5 or max_lat > 38.5 or min_lon < 66.5 or max_lon > 100.0:
        raise ValueError(
            f"Pune BBox coordinates Lat [{min_lat}, {max_lat}], Lon [{min_lon}, {max_lon}] "
            f"fall outside IMD dataset bounds Lat [6.5, 38.5], Lon [66.5, 100.0]."
        )
    
    logger.info(f"Extracting Pune spatial rainfall within BBox: Lat [{min_lat}, {max_lat}], Lon [{min_lon}, {max_lon}]")
    
    # 1. Establish stable Grid IDs from the first year dataset
    first_year = years[0]
    try:
        with load_yearly_netcdf(first_year, raw_dir) as ds:
            # Slice spatial dimensions (coords in IMD NC are ascending LATITUDE, LONGITUDE)
            spatial_ds = ds.sel(LATITUDE=slice(min_lat, max_lat), LONGITUDE=slice(min_lon, max_lon))
            
            # Find unique coordinate pairs
            lats = spatial_ds.LATITUDE.values
            lons = spatial_ds.LONGITUDE.values
            
            grid_points = []
            for lat in lats:
                for lon in lons:
                    grid_points.append((float(lat), float(lon)))
                    
            # Sort coordinates ascending: latitude first, then longitude
            grid_points = sorted(grid_points, key=lambda x: (x[0], x[1]))
            
            grid_mappings = {}
            metadata_records = []
            for idx, (lat, lon) in enumerate(grid_points):
                grid_id = f"PUNE_G{idx+1:03d}"
                grid_mappings[(lat, lon)] = grid_id
                metadata_records.append({
                    "Grid_ID": grid_id,
                    "Latitude": lat,
                    "Longitude": lon
                })
                
            grid_metadata_df = pd.DataFrame(metadata_records)
            logger.info(f"Established {len(grid_metadata_df)} stable grid cells in Pune study area.")
            for _, r in grid_metadata_df.iterrows():
                logger.info(f"  - {r['Grid_ID']}: Lat {r['Latitude']}, Lon {r['Longitude']}")
                
    except Exception as e:
        logger.error(f"Failed to load grid coordinates from year {first_year}: {e}")
        raise

    records = []
    
    # 2. Extract rainfall year by year for all grid points
    for year in years:
        logger.info(f"Processing Pune spatial extraction for year: {year}")
        try:
            with load_yearly_netcdf(year, raw_dir) as ds:
                # Slice spatial dimensions
                spatial_ds = ds.sel(LATITUDE=slice(min_lat, max_lat), LONGITUDE=slice(min_lon, max_lon))
                
                # Verify coordinates match our pre-calculated mappings
                curr_lats = spatial_ds.LATITUDE.values
                curr_lons = spatial_ds.LONGITUDE.values
                times = spatial_ds.TIME.values
                
                # xarray variables order is (TIME, LATITUDE, LONGITUDE)
                # Convert to numpy array for fast index access
                rainfall_cube = spatial_ds.RAINFALL.values
                
                # Extract records
                for t_idx, t_val in enumerate(times):
                    date_str = pd.to_datetime(t_val).strftime("%Y-%m-%d")
                    dt_obj = pd.to_datetime(t_val)
                    
                    year_val = dt_obj.year
                    month_val = dt_obj.month
                    day_val = dt_obj.day
                    doy_val = dt_obj.dayofyear
                    
                    for lat_idx, lat_val in enumerate(curr_lats):
                        for lon_idx, lon_val in enumerate(curr_lons):
                            lat_key = float(lat_val)
                            lon_key = float(lon_val)
                            grid_id = grid_mappings.get((lat_key, lon_key))
                            
                            if grid_id:
                                r_val = float(rainfall_cube[t_idx, lat_idx, lon_idx])
                                
                                records.append({
                                    "Grid_ID": grid_id,
                                    "Date": date_str,
                                    "Year": year_val,
                                    "Month": month_val,
                                    "Day": day_val,
                                    "DayOfYear": doy_val,
                                    "Latitude": lat_key,
                                    "Longitude": lon_key,
                                    "Rainfall_mm": r_val
                                })
        except Exception as e:
            logger.error(f"Failed to process Pune spatial year {year}: {e}")
            raise
            
    pune_spatial_df = pd.DataFrame(records)
    
    # Sort by Grid_ID and Date to ensure structured time-series consistency
    pune_spatial_df = pune_spatial_df.sort_values(by=["Grid_ID", "Date"]).reset_index(drop=True)
    
    logger.info(f"Extracted {len(pune_spatial_df)} total grid-day records for Pune hyperlocal study area.")
    return pune_spatial_df, grid_metadata_df
