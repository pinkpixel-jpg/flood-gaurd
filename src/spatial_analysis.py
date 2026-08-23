import os
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def compute_gini(array):
    """Calculate the Gini coefficient of a numpy array (measures inequality/concentration)."""
    # Array must be non-zero and sorted
    array = array.flatten()
    if np.amin(array) < 0:
        # Values cannot be negative
        array -= np.amin(array)
    # Mean value must not be zero
    if np.sum(array) == 0:
        return 0.0
    array = np.sort(array)
    index = np.arange(1, array.shape[0] + 1)
    n = array.shape[0]
    return ((2 * np.sum(index * array)) / (n * np.sum(array))) - ((n + 1) / n)

def main():
    filepath = "data/processed/pune/pune_spatial_rainfall_2015_2025.csv"
    if not os.path.exists(filepath):
        logger.error(f"Base spatial rainfall file not found at: {filepath}. Please run pipeline first.")
        return
        
    print("\n" + "=" * 80)
    print("      PUNE HYPERLOCAL SPATIOTEMPORAL DATASET ANALYSIS")
    print("=" * 80 + "\n")
    
    df = pd.read_csv(filepath)
    df["Date"] = pd.to_datetime(df["Date"])
    
    # 1. Spatial Correlation Analysis
    # Pivot rainfall to columns: columns = Grid_ID, index = Date
    pivot_df = df.pivot(index="Date", columns="Grid_ID", values="Rainfall_mm")
    corr_matrix = pivot_df.corr(method="pearson")
    
    print("1. SPATIAL CORRELATION MATRIX (PEARSON COEFFICIENTS):")
    print("-" * 60)
    print(corr_matrix.round(4).to_string())
    print("\n[Interpretation]: High correlation (> 0.95) indicates strong spatial homogeneity. ")
    print("Slightly lower correlation indicates localized convective or topographic variations.\n")
    
    # 2. Gini Index of Rainfall (Concentration analysis)
    print("2. RAINFALL CONCENTRATION INDEX (GINI COEFFICIENT) PER CELL:")
    print("-" * 60)
    gini_results = {}
    for grid_id in df["Grid_ID"].unique():
        grid_rain = df[df["Grid_ID"] == grid_id]["Rainfall_mm"].values
        # Only compute on rainy days to see intensity concentration
        rainy_days = grid_rain[grid_rain > 0]
        gini = compute_gini(rainy_days)
        gini_results[grid_id] = gini
        print(f"  - {grid_id}: {gini:.4f}")
    print("\n[Interpretation]: A higher Gini index indicates that a few extreme days account for ")
    print("the majority of the seasonal rainfall, highlighting high flash flood vulnerability.\n")
    
    # 3. Monthly Rainfall Contribution Climatology
    print("3. MONTHLY AVERAGE DAILY RAINFALL CLIMATOLOGY (mm):")
    print("-" * 60)
    monthly_climo = df.groupby(["Grid_ID", "Month"])["Rainfall_mm"].mean().unstack(level=0)
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_climo.index = month_names
    print(monthly_climo.round(4).to_string())
    print()
    
    # 4. Long-Term Dry spell vs Wet Spell stats
    print("4. MONSOON AND DRY spell COMPARATIVE METRICS:")
    print("-" * 60)
    stats_df = pd.read_csv("data/processed/pune/pune_grid_statistics.csv")
    for _, row in stats_df.iterrows():
        print(f"Grid Cell {row['Grid_ID']} ({row['Latitude']:.2f}° N, {row['Longitude']:.2f}° E):")
        print(f"  * Mean daily rain: {row['Mean_Rainfall_mm']:.4f} mm")
        print(f"  * Cumulative 11-year rainfall: {row['Total_Rainfall_mm']:.2f} mm")
        print(f"  * Rainy Days: {int(row['Rainy_Days'])} days ({row['Rainy_Days']/40.18:.2f}%)")
        print(f"  * Heavy Rainfall Days (>64.4 mm): {int(row['Heavy_Rainfall_Days'])}")
        print(f"  * Extreme Rainfall Days (>115.5 mm): {int(row['Extreme_Rainfall_Days'])}")
        print(f"  * Longest dry spell: {int(row['Longest_Dry_Spell'])} days")
        print()
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
