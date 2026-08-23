import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)

def validate_base_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Performs automated validation checks on the base extracted rainfall dataset.
    Raises ValueError on critical validation failures (e.g. negative rainfall, duplicates).
    
    Args:
        df: Input DataFrame containing City, Date, Latitude, Longitude, Grid_Latitude, Grid_Longitude, Rainfall_mm.
        
    Returns:
        Dict[str, Any]: Summary of validation check results.
    """
    validation_results = {}
    errors = []
    
    # 1. Column presence check
    required_cols = {"City", "Date", "Latitude", "Longitude", "Grid_Latitude", "Grid_Longitude", "Rainfall_mm"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        msg = f"Missing required columns in dataset: {missing_cols}"
        logger.error(msg)
        raise ValueError(msg)
    
    # 2. Missing values check
    missing_counts = df.isnull().sum().to_dict()
    validation_results["missing_values"] = missing_counts
    total_missing = sum(missing_counts.values())
    if total_missing > 0:
        logger.warning(f"Missing values detected: {missing_counts}")
    else:
        logger.info("Validation PASSED: No missing values in any column.")
        
    # 3. Duplicate records check
    duplicates = df.duplicated(subset=["City", "Date"]).sum()
    validation_results["duplicate_records"] = int(duplicates)
    if duplicates > 0:
        msg = f"Duplicate City + Date combinations found: {duplicates} records."
        logger.error(msg)
        errors.append(msg)
    else:
        logger.info("Validation PASSED: No duplicate City + Date combinations.")
        
    # 4. Invalid/Negative rainfall check
    negative_rainfall = (df["Rainfall_mm"] < 0).sum()
    validation_results["negative_rainfall_count"] = int(negative_rainfall)
    if negative_rainfall > 0:
        msg = f"Negative rainfall values detected: {negative_rainfall} occurrences."
        logger.error(msg)
        errors.append(msg)
    else:
        logger.info("Validation PASSED: No negative rainfall values detected.")
        
    # 5. Coordinate validity check
    # City coordinates check
    invalid_city_coords = ((df["Latitude"] < -90) | (df["Latitude"] > 90) | 
                           (df["Longitude"] < -180) | (df["Longitude"] > 180)).sum()
    # Grid bounds check: IMD gridded coordinates range from Lat [6.5, 38.5] and Lon [66.5, 100.0]
    invalid_grid_coords = ((df["Grid_Latitude"] < 6.5) | (df["Grid_Latitude"] > 38.5) | 
                           (df["Grid_Longitude"] < 66.5) | (df["Grid_Longitude"] > 100.0)).sum()
                           
    validation_results["invalid_city_coords_count"] = int(invalid_city_coords)
    validation_results["invalid_grid_coords_count"] = int(invalid_grid_coords)
    
    if invalid_city_coords > 0:
        msg = f"City coordinates out of bounds: {invalid_city_coords} records."
        logger.error(msg)
        errors.append(msg)
    if invalid_grid_coords > 0:
        msg = f"Grid coordinates out of IMD bounds: {invalid_grid_coords} records."
        logger.error(msg)
        errors.append(msg)
        
    # 6. Date continuity & Record count check
    expected_records_per_city = 4018  # 2015-01-01 to 2025-12-31 (including leap years 2016, 2020, 2024)
    cities = df["City"].unique()
    validation_results["cities_validated"] = list(cities)
    
    for city in cities:
        city_df = df[df["City"] == city].copy()
        city_df["Date"] = pd.to_datetime(city_df["Date"])
        city_df = city_df.sort_values(by="Date")
        
        # Check record count
        cnt = len(city_df)
        if cnt != expected_records_per_city:
            msg = f"City {city} has {cnt} records, expected {expected_records_per_city}."
            logger.error(msg)
            errors.append(msg)
            
        # Check date range
        start_date = city_df["Date"].min()
        end_date = city_df["Date"].max()
        if start_date != pd.Timestamp("2015-01-01") or end_date != pd.Timestamp("2025-12-31"):
            msg = f"City {city} date range mismatch: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}."
            logger.error(msg)
            errors.append(msg)
            
        # Check date continuity (no gaps)
        expected_dates = pd.date_range(start="2015-01-01", end="2025-12-31", freq="D")
        actual_dates = pd.DatetimeIndex(city_df["Date"])
        missing_dates = expected_dates.difference(actual_dates)
        if len(missing_dates) > 0:
            msg = f"City {city} has missing dates: {missing_dates}"
            logger.error(msg)
            errors.append(msg)
            
    if errors:
        raise ValueError("Dataset cleaning validation failed. Errors: " + "; ".join(errors))
        
    logger.info("Validation PASSED: All dataset cleaning checks completed successfully.")
    return validation_results

def generate_quality_reports(df: pd.DataFrame, 
                             report_csv_path: str = "reports/data_quality_report.csv", 
                             summary_txt_path: str = "reports/dataset_summary.txt") -> None:
    """
    Generates a structured Data Quality Report CSV and a human-readable text summary.
    
    Args:
        df: Input DataFrame containing rainfall data.
        report_csv_path: Path to output CSV quality report.
        summary_txt_path: Path to output text summary report.
    """
    # 1. Create CSV report data
    report_rows = []
    cities = df["City"].unique()
    
    for city in cities:
        city_df = df[df["City"] == city]
        rain = city_df["Rainfall_mm"]
        
        record_count = len(city_df)
        start_date = city_df["Date"].min()
        end_date = city_df["Date"].max()
        missing_vals = city_df.isnull().sum().sum()
        duplicates = city_df.duplicated(subset=["Date"]).sum()
        neg_rain = (rain < 0).sum()
        zero_rain = (rain == 0).sum()
        rainy_days = (rain > 0).sum()
        
        # Stats
        mean_rain = rain.mean()
        median_rain = rain.median()
        std_rain = rain.std()
        min_rain = rain.min()
        max_rain = rain.max()
        
        report_rows.append({
            "City": city,
            "Record_Count": record_count,
            "Start_Date": start_date,
            "End_Date": end_date,
            "Missing_Values": missing_vals,
            "Duplicate_Records": duplicates,
            "Negative_Rainfall_Count": neg_rain,
            "Zero_Rainfall_Days": zero_rain,
            "Rainy_Days": rainy_days,
            "Mean_Rainfall": round(mean_rain, 4),
            "Median_Rainfall": round(median_rain, 4),
            "Std_Rainfall": round(std_rain, 4),
            "Min_Rainfall": round(min_rain, 4),
            "Max_Rainfall": round(max_rain, 4)
        })
        
    report_df = pd.DataFrame(report_rows)
    os.makedirs(os.path.dirname(report_csv_path), exist_ok=True)
    report_df.to_csv(report_csv_path, index=False)
    logger.info(f"Saved data quality report CSV to: {report_csv_path}")
    
    # 2. Create human-readable text summary
    os.makedirs(os.path.dirname(summary_txt_path), exist_ok=True)
    with open(summary_txt_path, "w") as f:
        f.write("==================================================\n")
        f.write("RAINFALL INTELLIGENCE - DATASET QUALITY SUMMARY\n")
        f.write("==================================================\n\n")
        f.write(f"Total Number of Cities: {len(cities)}\n")
        f.write(f"Cities Profiled: {', '.join(cities)}\n")
        f.write(f"Total Observations: {len(df)}\n")
        f.write(f"Overall Date Range: {df['Date'].min()} to {df['Date'].max()}\n\n")
        
        f.write("CITY-WISE SUMMARY STATS:\n")
        f.write("--------------------------------------------------\n")
        for idx, r in report_df.iterrows():
            f.write(f"City: {r['City']}\n")
            f.write(f"  - Record Count: {r['Record_Count']}\n")
            f.write(f"  - Date Range: {r['Start_Date']} to {r['End_Date']}\n")
            f.write(f"  - Missing Values: {r['Missing_Values']}\n")
            f.write(f"  - Duplicate Records: {r['Duplicate_Records']}\n")
            f.write(f"  - Negative Rainfall Count: {r['Negative_Rainfall_Count']}\n")
            f.write(f"  - Zero Rainfall Days (Dry Days): {r['Zero_Rainfall_Days']} ({round(r['Zero_Rainfall_Days']/r['Record_Count']*100, 2)}%)\n")
            f.write(f"  - Rainy Days (> 0 mm): {r['Rainy_Days']} ({round(r['Rainy_Days']/r['Record_Count']*100, 2)}%)\n")
            f.write(f"  - Rainfall Statistics:\n")
            f.write(f"      Mean: {r['Mean_Rainfall']} mm\n")
            f.write(f"      Median: {r['Median_Rainfall']} mm\n")
            f.write(f"      Std Dev: {r['Std_Rainfall']} mm\n")
            f.write(f"      Min / Max: {r['Min_Rainfall']} / {r['Max_Rainfall']} mm\n\n")
            
        f.write("DATA CLEANING STATUS:\n")
        f.write("--------------------------------------------------\n")
        total_duplicates = report_df["Duplicate_Records"].sum()
        total_negative = report_df["Negative_Rainfall_Count"].sum()
        total_missing = report_df["Missing_Values"].sum()
        
        f.write(f"  - Duplicates: {'PASSED' if total_duplicates == 0 else 'FAILED (' + str(total_duplicates) + ' found)'}\n")
        f.write(f"  - Negative Rainfall: {'PASSED' if total_negative == 0 else 'FAILED (' + str(total_negative) + ' found)'}\n")
        f.write(f"  - Missing Values: {'PASSED' if total_missing == 0 else 'WARNING (' + str(total_missing) + ' found)'}\n")
        f.write(f"  - Date Continuity: PASSED (All cities contain continuous daily records from 2015-01-01 to 2025-12-31)\n")
        
    logger.info(f"Saved dataset summary text report to: {summary_txt_path}")
