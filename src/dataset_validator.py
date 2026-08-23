import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

def perform_final_validation(df: pd.DataFrame, num_cities_expected: int = 8, 
                             report_path: str = "reports/final_dataset_validation.txt") -> Tuple[bool, Dict[str, Any]]:
    """
    Executes a rigorous 10-point check on the final training dataset.
    Generates a text report in reports/final_dataset_validation.txt.
    
    Args:
        df: The final processed training dataset DataFrame.
        num_cities_expected: The expected number of cities (default 8).
        report_path: File path to save the final validation report.
        
    Returns:
        Tuple[bool, Dict[str, Any]]: A tuple containing (all_passed_bool, results_dict).
    """
    logger.info("Executing final 10-point dataset validation...")
    results = {}
    passed = True
    errors = []
    
    # 1. Number of cities
    num_cities = df["City"].nunique()
    results["1_number_of_cities"] = {
        "status": "PASSED" if num_cities == num_cities_expected else "FAILED",
        "value": num_cities,
        "expected": num_cities_expected
    }
    if num_cities != num_cities_expected:
        passed = False
        errors.append(f"Expected {num_cities_expected} cities, but found {num_cities}.")
        
    # 2. Number of records per city
    records_per_city = df.groupby("City").size().to_dict()
    expected_records = 4018
    city_record_status = "PASSED"
    for city, count in records_per_city.items():
        if count != expected_records:
            city_record_status = "FAILED"
            passed = False
            errors.append(f"City {city} has {count} records, expected {expected_records}.")
            
    results["2_records_per_city"] = {
        "status": city_record_status,
        "counts": records_per_city,
        "expected": expected_records
    }
    
    # 3. Date range
    min_date = df["Date"].min()
    max_date = df["Date"].max()
    date_range_ok = (min_date == "2015-01-01") and (max_date == "2025-12-31")
    results["3_date_range"] = {
        "status": "PASSED" if date_range_ok else "FAILED",
        "min_date": min_date,
        "max_date": max_date,
        "expected": "2015-01-01 to 2025-12-31"
    }
    if not date_range_ok:
        passed = False
        errors.append(f"Expected date range 2015-01-01 to 2025-12-31, but found {min_date} to {max_date}.")
        
    # 4. Missing values (Nulls check in identifier & current columns)
    core_cols = ["City", "Date", "Latitude", "Longitude", "Grid_Latitude", "Grid_Longitude", "Rainfall_mm"]
    core_nulls = df[core_cols].isnull().sum().to_dict()
    core_nulls_ok = sum(core_nulls.values()) == 0
    results["4_core_missing_values"] = {
        "status": "PASSED" if core_nulls_ok else "FAILED",
        "null_counts": core_nulls
    }
    if not core_nulls_ok:
        passed = False
        errors.append(f"Core columns contain null values: {core_nulls}.")
        
    # 5. Duplicate city-date combinations
    duplicates = df.duplicated(subset=["City", "Date"]).sum()
    results["5_duplicate_combinations"] = {
        "status": "PASSED" if duplicates == 0 else "FAILED",
        "value": int(duplicates),
        "expected": 0
    }
    if duplicates > 0:
        passed = False
        errors.append(f"Found {duplicates} duplicate City + Date combinations.")
        
    # 6. Negative rainfall
    negative_rain = (df["Rainfall_mm"] < 0).sum()
    results["6_negative_rainfall"] = {
        "status": "PASSED" if negative_rain == 0 else "FAILED",
        "value": int(negative_rain),
        "expected": 0
    }
    if negative_rain > 0:
        passed = False
        errors.append(f"Found {negative_rain} instances of negative rainfall.")
        
    # 7. Coordinate validity (within bounds)
    invalid_city = ((df["Latitude"] < -90) | (df["Latitude"] > 90) | 
                    (df["Longitude"] < -180) | (df["Longitude"] > 180)).sum()
    invalid_grid = ((df["Grid_Latitude"] < 6.5) | (df["Grid_Latitude"] > 38.5) | 
                    (df["Grid_Longitude"] < 66.5) | (df["Grid_Longitude"] > 100.0)).sum()
    coords_ok = (invalid_city == 0) and (invalid_grid == 0)
    results["7_coordinates_validity"] = {
        "status": "PASSED" if coords_ok else "FAILED",
        "invalid_city_count": int(invalid_city),
        "invalid_grid_count": int(invalid_grid)
    }
    if not coords_ok:
        passed = False
        errors.append(f"Invalid city coordinates count: {invalid_city}; Invalid grid coordinates count: {invalid_grid}.")
        
    # 8. Feature missingness (exact expected NaN check for lags/rolling)
    # Expected NaNs per feature across 8 cities:
    # Lag_1D: 1 * 8 = 8 NaNs.
    # Lag_2D: 2 * 8 = 16 NaNs.
    # Lag_3D: 3 * 8 = 24 NaNs.
    # Lag_7D: 7 * 8 = 56 NaNs.
    # Lag_14D: 14 * 8 = 112 NaNs.
    # Rolling features have min_periods=1, so only the shifted 1st day is NaN. That's 1 * 8 = 8 NaNs per rolling column.
    expected_nans = {
        "Rainfall_Lag_1D": 8,
        "Rainfall_Lag_2D": 16,
        "Rainfall_Lag_3D": 24,
        "Rainfall_Lag_7D": 56,
        "Rainfall_Lag_14D": 112,
        "Rainfall_Rolling_3D": 8,
        "Rainfall_Rolling_7D": 8,
        "Rainfall_Rolling_14D": 8,
        "Rainfall_Rolling_30D": 8,
        "Rainfall_Accumulated_3D": 8,
        "Rainfall_Accumulated_7D": 8,
        "Rainfall_Accumulated_14D": 8,
        "Rainfall_Accumulated_30D": 8
    }
    
    nan_mismatch = {}
    features_ok = True
    for feat, expected_count in expected_nans.items():
        if feat in df.columns:
            actual_count = df[feat].isnull().sum()
            if actual_count != expected_count:
                features_ok = False
                nan_mismatch[feat] = {"actual": int(actual_count), "expected": expected_count}
                passed = False
                errors.append(f"Feature {feat} has {actual_count} NaNs, expected {expected_count}.")
                
    results["8_feature_missingness"] = {
        "status": "PASSED" if features_ok else "FAILED",
        "mismatches": nan_mismatch
    }
    
    # 9. Infinite values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_count = np.isinf(df[numeric_cols]).sum().sum()
    results["9_infinite_values"] = {
        "status": "PASSED" if inf_count == 0 else "FAILED",
        "value": int(inf_count),
        "expected": 0
    }
    if inf_count > 0:
        passed = False
        errors.append(f"Found {inf_count} infinite values in numeric columns.")
        
    # 10. Data type consistency
    # Check that types are consistent and correct
    type_checks = {
        "City": df["City"].dtype == object or df["City"].dtype == "string",
        "Date": df["Date"].dtype == object or df["Date"].dtype == "string",
        "Latitude": pd.api.types.is_float_dtype(df["Latitude"]),
        "Longitude": pd.api.types.is_float_dtype(df["Longitude"]),
        "Grid_Latitude": pd.api.types.is_float_dtype(df["Grid_Latitude"]),
        "Grid_Longitude": pd.api.types.is_float_dtype(df["Grid_Longitude"]),
        "Rainfall_mm": pd.api.types.is_float_dtype(df["Rainfall_mm"]),
        "Rainy_Day": pd.api.types.is_integer_dtype(df["Rainy_Day"]),
        "Dry_Day": pd.api.types.is_integer_dtype(df["Dry_Day"]),
        "Year": pd.api.types.is_integer_dtype(df["Year"]),
        "Month": pd.api.types.is_integer_dtype(df["Month"]),
        "Day": pd.api.types.is_integer_dtype(df["Day"]),
        "DayOfYear": pd.api.types.is_integer_dtype(df["DayOfYear"]),
        "DayOfWeek": pd.api.types.is_integer_dtype(df["DayOfWeek"]),
        "WeekOfYear": pd.api.types.is_integer_dtype(df["WeekOfYear"]),
        "Is_Leap_Year": pd.api.types.is_integer_dtype(df["Is_Leap_Year"]),
        "Is_Heavy_Rainfall": pd.api.types.is_integer_dtype(df["Is_Heavy_Rainfall"]),
        "Is_Extreme_Event": pd.api.types.is_integer_dtype(df["Is_Extreme_Event"]),
    }
    types_ok = all(type_checks.values())
    results["10_datatype_consistency"] = {
        "status": "PASSED" if types_ok else "FAILED",
        "checks": {k: "PASSED" if v else "FAILED" for k, v in type_checks.items()}
    }
    if not types_ok:
        passed = False
        failed_types = [k for k, v in type_checks.items() if not v]
        errors.append(f"Data type checks failed for columns: {failed_types}.")
        
    # Write report file
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("==================================================\n")
        f.write("FINAL TRAINING DATASET - 10-POINT VALIDATION REPORT\n")
        f.write("==================================================\n\n")
        f.write(f"Validation Status: {'PASSED' if passed else 'FAILED'}\n\n")
        
        f.write("CHECK DETAILS:\n")
        f.write("--------------------------------------------------\n")
        f.write(f"1. Number of Cities: {results['1_number_of_cities']['status']} (Found {results['1_number_of_cities']['value']}, expected {results['1_number_of_cities']['expected']})\n")
        
        records_status = results['2_records_per_city']['status']
        f.write(f"2. Records per City: {records_status} (Expected {results['2_records_per_city']['expected']} daily records each)\n")
        for c, count in results['2_records_per_city']['counts'].items():
            f.write(f"     - {c}: {count} records\n")
            
        f.write(f"3. Date Range Check: {results['3_date_range']['status']} ({results['3_date_range']['min_date']} to {results['3_date_range']['max_date']})\n")
        
        f.write(f"4. Core Columns Missingness: {results['4_core_missing_values']['status']}\n")
        for col, null_cnt in results['4_core_missing_values']['null_counts'].items():
            f.write(f"     - {col}: {null_cnt} missing values\n")
            
        f.write(f"5. Duplicate Records Check: {results['5_duplicate_combinations']['status']} (Found {results['5_duplicate_combinations']['value']} duplicates)\n")
        f.write(f"6. Negative Rainfall Check: {results['6_negative_rainfall']['status']} (Found {results['6_negative_rainfall']['value']} occurrences)\n")
        f.write(f"7. Geographic Coordinate Validity: {results['7_coordinates_validity']['status']} (Invalid City: {results['7_coordinates_validity']['invalid_city_count']}, Invalid Grid: {results['7_coordinates_validity']['invalid_grid_count']})\n")
        
        f.write(f"8. Feature Missingness (NaN Counts): {results['8_feature_missingness']['status']}\n")
        if results['8_feature_missingness']['status'] == "PASSED":
            f.write("     - All lag and rolling columns contain the mathematically expected number of NaN values on start dates.\n")
        else:
            f.write("     - Mismatches in expected NaN counts:\n")
            for feat, data in results['8_feature_missingness']['mismatches'].items():
                f.write(f"         * {feat}: found {data['actual']} NaNs, expected {data['expected']}\n")
                
        f.write(f"9. Infinite Values Check: {results['9_infinite_values']['status']} (Found {results['9_infinite_values']['value']} infinites)\n")
        
        f.write(f"10. Column Data Type Consistency: {results['10_datatype_consistency']['status']}\n")
        for col, status in results['10_datatype_consistency']['checks'].items():
            f.write(f"     - {col}: {status}\n")
            
        if not passed:
            f.write("\nVALIDATION ERROR DETAILS:\n")
            f.write("--------------------------------------------------\n")
            for err in errors:
                f.write(f"- {err}\n")
                
    logger.info(f"Saved final validation report to: {report_path}")
    return passed, results
