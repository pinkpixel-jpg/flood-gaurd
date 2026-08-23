import os
import pandas as pd
import numpy as np

def main():
    filepath = "data/processed/pune/pune_training_dataset_2015_2025.csv"
    if not os.path.exists(filepath):
        print(f"Error: Dataset not found at {filepath}")
        return
        
    print("\n" + "=" * 90)
    print("           DETAILED METADATA & STATISTICAL PREVIEW OF PUNE HYPERLOCAL DATASET")
    print("=" * 90 + "\n")
    
    df = pd.read_csv(filepath)
    
    print(f"1. DATASET DIMENSIONS:")
    print("-" * 50)
    print(f"  * Total Rows (Observations): {df.shape[0]}")
    print(f"  * Total Columns (Features) : {df.shape[1]}")
    print()
    
    print(f"2. COLUMN TYPE & COMPLETENESS PROFILE:")
    print("-" * 50)
    # Get column summaries
    col_profile = []
    for col in df.columns:
        null_count = df[col].isnull().sum()
        pct_missing = (null_count / len(df)) * 100
        dtype = df[col].dtype
        unique_count = df[col].nunique()
        col_profile.append({
            "Column Name": col,
            "Dtype": str(dtype),
            "Unique Count": unique_count,
            "NaN Count": null_count,
            "NaN %": f"{pct_missing:.2f}%"
        })
    profile_df = pd.DataFrame(col_profile)
    print(profile_df.to_string(index=False))
    print()
    
    # Select numeric columns for describe
    numeric_cols = [
        "Latitude", "Longitude", "Rainfall_mm", "Rainfall_Lag_1D", "Rainfall_Lag_3D",
        "Rainfall_Lag_7D", "Rainfall_Rolling_3D", "Rainfall_Rolling_7D",
        "Rainfall_Accumulated_3D", "Rainfall_Accumulated_7D", "Consecutive_Dry_Days"
    ]
    print(f"3. SUMMARY STATISTICS FOR REPRESENTATIVE FEATURES:")
    print("-" * 50)
    summary_df = df[numeric_cols].describe().transpose()
    print(summary_df.round(4).to_string())
    print()
    
    print(f"4. CATEGORICAL CLASSIFICATION DISTRIBUTION:")
    print("-" * 50)
    cat_counts = df["Rainfall_Category"].value_counts()
    cat_pct = df["Rainfall_Category"].value_counts(normalize=True) * 100
    for idx in cat_counts.index:
        print(f"  * {idx:<10}: {cat_counts[idx]:>5} records ({cat_pct[idx]:.2f}%)")
    print()
    
    print(f"5. HAZARD FLAGS DETECTED:")
    print("-" * 50)
    heavy_count = df["Is_Heavy_Rainfall"].sum()
    extreme_count = df["Is_Extreme_Event"].sum()
    print(f"  * Heavy Rainfall Days (>64.4 mm)  : {heavy_count} occurrences ({heavy_count/len(df)*100:.3f}% of data)")
    print(f"  * Extreme Rainfall Days (>115.5 mm): {extreme_count} occurrences ({extreme_count/len(df)*100:.3f}% of data)")
    print("\n" + "=" * 90 + "\n")

if __name__ == "__main__":
    main()
