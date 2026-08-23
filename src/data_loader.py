import os
import json
import logging
import pandas as pd
import xarray as xr
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def load_cities(filepath: str = "data/config/cities.csv") -> pd.DataFrame:
    """
    Loads city configurations from a CSV file.
    
    Args:
        filepath: Path to the cities CSV file.
        
    Returns:
        pd.DataFrame: DataFrame containing City, Latitude, Longitude.
    """
    if not os.path.exists(filepath):
        logger.error(f"Cities configuration file not found at: {filepath}")
        raise FileNotFoundError(f"Cities configuration file not found at: {filepath}")
    
    try:
        df = pd.read_csv(filepath)
        # Validate expected columns
        required_cols = {"City", "Latitude", "Longitude"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"Cities file must contain columns: {required_cols}")
        
        # Strip string values
        df["City"] = df["City"].astype(str).str.strip()
        df["Latitude"] = pd.to_numeric(df["Latitude"])
        df["Longitude"] = pd.to_numeric(df["Longitude"])
        
        logger.info(f"Loaded {len(df)} cities from {filepath}")
        return df
    except Exception as e:
        logger.error(f"Error loading cities file: {e}")
        raise

def load_thresholds(filepath: str = "data/config/rainfall_thresholds.json") -> Dict[str, Any]:
    """
    Loads daily rainfall thresholds and category names from a JSON file.
    
    Args:
        filepath: Path to the thresholds JSON file.
        
    Returns:
        Dict[str, Any]: Dictionary containing thresholds and metadata.
    """
    if not os.path.exists(filepath):
        logger.error(f"Rainfall thresholds configuration file not found at: {filepath}")
        raise FileNotFoundError(f"Thresholds configuration file not found at: {filepath}")
        
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded rainfall thresholds from {filepath}")
        return data
    except Exception as e:
        logger.error(f"Error loading thresholds file: {e}")
        raise

def load_yearly_netcdf(year: int, directory: str = "data/raw/imd") -> xr.Dataset:
    """
    Loads a specific yearly IMD rainfall NetCDF file.
    
    Args:
        year: The calendar year (e.g., 2015).
        directory: Directory where IMD raw NetCDF files are stored.
        
    Returns:
        xr.Dataset: The opened xarray Dataset.
    """
    filename = f"RF25_ind{year}_rfp25.nc"
    filepath = os.path.join(directory, filename)
    
    if not os.path.exists(filepath):
        logger.error(f"IMD NetCDF file not found for year {year} at: {filepath}")
        raise FileNotFoundError(f"IMD NetCDF file not found for year {year} at: {filepath}")
        
    try:
        # Open dataset with xarray
        # Use chunks if dataset is extremely large, but 25MB is small enough to load directly.
        ds = xr.open_dataset(filepath)
        logger.info(f"Successfully loaded NetCDF dataset for year {year} (size: {ds.sizes})")
        return ds
    except Exception as e:
        logger.error(f"Error opening NetCDF file {filepath}: {e}")
        raise
