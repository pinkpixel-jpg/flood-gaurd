import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)

def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds cyclic and standard temporal features to the dataset.
    
    Adds: Year, Month, Day, DayOfYear, DayOfWeek, WeekOfYear, Is_Leap_Year, Month_Sin, Month_Cos
    """
    logger.info("Adding temporal features...")
    df = df.copy()
    dates = pd.to_datetime(df["Date"])
    
    df["Year"] = dates.dt.year
    df["Month"] = dates.dt.month
    df["Day"] = dates.dt.day
    df["DayOfYear"] = dates.dt.dayofyear
    df["DayOfWeek"] = dates.dt.dayofweek + 1  # 1-indexed (1=Monday, 7=Sunday)
    df["WeekOfYear"] = dates.dt.isocalendar().week.astype(int)
    
    # Is_Leap_Year check (boolean cast to int: 1 or 0)
    df["Is_Leap_Year"] = dates.dt.is_leap_year.astype(int)
    
    # Cyclic seasonality representation
    df["Month_Sin"] = np.sin(2 * np.pi * df["Month"] / 12.0)
    df["Month_Cos"] = np.cos(2 * np.pi * df["Month"] / 12.0)
    
    return df

def add_rainfall_behavior_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds binary indicators for wet/dry status.
    """
    logger.info("Adding rainfall behavior features...")
    df = df.copy()
    df["Rainy_Day"] = (df["Rainfall_mm"] > 0).astype(int)
    df["Dry_Day"] = (df["Rainfall_mm"] == 0).astype(int)
    return df

def add_lag_features(df: pd.DataFrame, group_col: str = "City") -> pd.DataFrame:
    """
    Adds historical lag features. Shifts are grouped by group_col to avoid cross-group data leakage.
    
    Lags: 1D, 2D, 3D, 7D, 14D
    """
    logger.info(f"Adding historical lag features (1D, 2D, 3D, 7D, 14D) grouped by {group_col}...")
    df = df.copy()
    
    # Group by group_col and shift
    grouped = df.groupby(group_col)["Rainfall_mm"]
    
    df["Rainfall_Lag_1D"] = grouped.shift(1)
    df["Rainfall_Lag_2D"] = grouped.shift(2)
    df["Rainfall_Lag_3D"] = grouped.shift(3)
    df["Rainfall_Lag_7D"] = grouped.shift(7)
    df["Rainfall_Lag_14D"] = grouped.shift(14)
    
    return df

def add_rolling_and_accumulation_features(df: pd.DataFrame, group_col: str = "City") -> pd.DataFrame:
    """
    Adds shifted rolling average and accumulated sum features to prevent future data leakage.
    For date t, features represent calculations over days [t-W, t-1].
    
    Windows: 3D, 7D, 14D, 30D
    """
    logger.info(f"Adding shifted rolling and accumulation features (3D, 7D, 14D, 30D) grouped by {group_col}...")
    df = df.copy()
    
    # Pre-shift the rainfall series by 1 day per group to align history to date t-1
    # This prevents any leakage of today's rainfall into today's rolling history.
    shifted_rainfall = df.groupby(group_col)["Rainfall_mm"].shift(1)
    
    # Re-group the shifted series by group_col for rolling operations
    grouped_shifted = shifted_rainfall.groupby(df[group_col])
    
    for w in [3, 7, 14, 30]:
        # Rolling averages
        df[f"Rainfall_Rolling_{w}D"] = grouped_shifted.rolling(window=w, min_periods=1).mean().reset_index(level=0, drop=True)
        # Rolling accumulated sums
        df[f"Rainfall_Accumulated_{w}D"] = grouped_shifted.rolling(window=w, min_periods=1).sum().reset_index(level=0, drop=True)
        
    return df

def add_dry_spell_features(df: pd.DataFrame, group_col: str = "City") -> pd.DataFrame:
    """
    Calculates consecutive dry days prior to the current date.
    Uses shifted vectorized cumsum reset grouping logic.
    """
    logger.info(f"Adding consecutive dry days feature grouped by {group_col}...")
    df = df.copy()
    
    # Dry_Day is 1 if rainfall is 0. Shift by 1 to get history prior to date t
    prev_dry = df.groupby(group_col)["Dry_Day"].shift(1).fillna(0).astype(int)
    
    # Reset cumsum whenever a day is rainy (prev_dry is 0)
    is_rainy = (prev_dry == 0)
    run_id = is_rainy.groupby(df[group_col]).cumsum()
    
    # Sum consecutive dry days within each run
    df["Consecutive_Dry_Days"] = prev_dry.groupby([df[group_col], run_id]).cumsum()
    
    return df

def add_category_features(df: pd.DataFrame, thresholds_config: Dict[str, Any], group_col: str = "City") -> pd.DataFrame:
    """
    Classifies daily daily rainfall into scientific categories and binary hazard triggers.
    
    Categories: Dry, Light, Moderate, Heavy, Extreme
    """
    logger.info("Adding rainfall category and event classification features...")
    df = df.copy()
    
    # Load thresholds from configuration dictionary
    heavy_thresh = thresholds_config.get("heavy_rainfall_threshold_mm", 64.4)
    extreme_thresh = thresholds_config.get("extreme_event_threshold_mm", 115.5)
    
    # Hardcoded fallback matches IMD-derived thresholds if json is altered
    conditions = [
        (df["Rainfall_mm"] == 0.0),
        (df["Rainfall_mm"] > 0.0) & (df["Rainfall_mm"] <= 15.5),
        (df["Rainfall_mm"] > 15.5) & (df["Rainfall_mm"] <= 64.4),
        (df["Rainfall_mm"] > 64.4) & (df["Rainfall_mm"] <= 115.5),
        (df["Rainfall_mm"] > 115.5)
    ]
    choices = ["Dry", "Light", "Moderate", "Heavy", "Extreme"]
    
    df["Rainfall_Category"] = np.select(conditions, choices, default="Dry")
    
    # Hazard triggers
    df["Is_Heavy_Rainfall"] = (df["Rainfall_mm"] > heavy_thresh).astype(int)
    df["Is_Extreme_Event"] = (df["Rainfall_mm"] > extreme_thresh).astype(int)
    
    # Year/Month peak stats (Note: these are target descriptors for analysis, not for predictive features)
    df["Annual_Max_Rainfall"] = df.groupby([group_col, "Year"])["Rainfall_mm"].transform("max")
    df["Monthly_Max_Rainfall"] = df.groupby([group_col, "Year", "Month"])["Rainfall_mm"].transform("max")
    
    return df

def engineer_features(df: pd.DataFrame, thresholds_config: Dict[str, Any], group_col: str = "City") -> pd.DataFrame:
    """
    Applies the full feature engineering pipeline to the dataframe.
    """
    logger.info(f"Starting feature engineering pipeline grouped by {group_col}...")
    df = add_temporal_features(df)
    df = add_rainfall_behavior_features(df)
    df = add_lag_features(df, group_col=group_col)
    df = add_rolling_and_accumulation_features(df, group_col=group_col)
    df = add_dry_spell_features(df, group_col=group_col)
    df = add_category_features(df, thresholds_config, group_col=group_col)
    logger.info("Feature engineering pipeline completed successfully.")
    return df

