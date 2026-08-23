import logging
import pandas as pd
import xarray as xr
from typing import List
from src.data_loader import load_yearly_netcdf

logger = logging.getLogger(__name__)

def extract_city_rainfall(cities_df: pd.DataFrame, years: List[int], raw_dir: str = "data/raw/imd") -> pd.DataFrame:
    """
    Extracts daily rainfall for each city from the IMD NetCDF files for the specified years.
    Guarantees coordinates match valid land cells (non-NaN in IMD dataset).
    
    Args:
        cities_df: DataFrame containing City, Latitude, Longitude.
        years: List of years to extract (e.g., list(range(2015, 2026))).
        raw_dir: Directory where raw NetCDF files are located.
        
    Returns:
        pd.DataFrame: Extracted daily rainfall records.
    """
    records = []
    
    # 1. Open the first year to find valid land grid cells (non-NaN overall)
    first_year = years[0]
    logger.info(f"Mapping cities to nearest land cells using first year dataset: {first_year}")
    try:
        with load_yearly_netcdf(first_year, raw_dir) as ds:
            # Compute mask of valid grid points (non-NaN over time)
            valid_mask = ds.RAINFALL.mean(dim="TIME").notnull()
            stacked = valid_mask.stack(gridpoint=("LATITUDE", "LONGITUDE"))
            valid_points = stacked.where(stacked, drop=True)
            lats = valid_points.LATITUDE.values
            lons = valid_points.LONGITUDE.values
    except Exception as e:
        logger.error(f"Failed to load land mask from year {first_year}: {e}")
        raise

    # 2. Pre-calculate the nearest valid land grid cell for each city
    city_grid_mappings = {}
    for _, row in cities_df.iterrows():
        city_name = row["City"]
        city_lat = row["Latitude"]
        city_lon = row["Longitude"]
        
        # Calculate Euclidean distances to all valid land grid cells
        dist_sq = (lats - city_lat)**2 + (lons - city_lon)**2
        min_idx = dist_sq.argmin()
        best_lat = float(lats[min_idx])
        best_lon = float(lons[min_idx])
        
        city_grid_mappings[city_name] = (best_lat, best_lon)
        logger.info(f"City {city_name} ({city_lat}, {city_lon}) mapped to nearest land grid cell ({best_lat}, {best_lon})")

    # 3. Process one year at a time to optimize memory and execution
    for year in years:
        logger.info(f"Processing extraction for year: {year}")
        try:
            with load_yearly_netcdf(year, raw_dir) as ds:
                # Iterate over cities
                for _, row in cities_df.iterrows():
                    city_name = row["City"]
                    city_lat = row["Latitude"]
                    city_lon = row["Longitude"]
                    grid_lat, grid_lon = city_grid_mappings[city_name]
                    
                    # Direct coordinate selection (nearest is no longer needed since we match pre-calculated coordinates exactly)
                    point_ds = ds.sel(LATITUDE=grid_lat, LONGITUDE=grid_lon)
                    
                    # Extract times and rainfall values
                    times = point_ds.TIME.values
                    rainfall_vals = point_ds.RAINFALL.values
                    
                    # Append each day's record
                    for t, r in zip(times, rainfall_vals):
                        # Convert numpy datetime64 to pandas Timestamp, then to string format YYYY-MM-DD
                        date_str = pd.to_datetime(t).strftime("%Y-%m-%d")
                        
                        records.append({
                            "City": city_name,
                            "Latitude": city_lat,
                            "Longitude": city_lon,
                            "Grid_Latitude": grid_lat,
                            "Grid_Longitude": grid_lon,
                            "Date": date_str,
                            "Rainfall_mm": float(r)
                        })
                        
        except Exception as e:
            logger.error(f"Failed to process year {year}: {e}")
            raise
            
    # Create combined DataFrame
    extracted_df = pd.DataFrame(records)
    
    # Sort by City and Date as required
    extracted_df = extracted_df.sort_values(by=["City", "Date"]).reset_index(drop=True)
    
    logger.info(f"Extracted a total of {len(extracted_df)} records across all cities and years.")
    return extracted_df

