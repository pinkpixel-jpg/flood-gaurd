import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import List

# Import modular pipeline functions
from src.data_loader import load_cities, load_thresholds
from src.rainfall_extractor import extract_city_rainfall
from src.data_cleaning import validate_base_dataset, generate_quality_reports
from src.feature_engineering import engineer_features
from src.elevation_extractor import extract_city_elevations
from src.dataset_validator import perform_final_validation

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_validation_plots(df: pd.DataFrame, figures_dir: str = "outputs/figures"):
    """
    Generates and saves the required validation plots using rich aesthetics.
    """
    logger.info("Generating validation plots...")
    os.makedirs(figures_dir, exist_ok=True)
    
    # Set style properties for modern, premium appearance
    plt.rcParams['font.sans-serif'] = 'sans-serif'
    plt.rcParams['axes.edgecolor'] = '#CCCCCC'
    plt.rcParams['axes.linewidth'] = 0.8
    plt.rcParams['xtick.color'] = '#333333'
    plt.rcParams['ytick.color'] = '#333333'
    
    # 1. Annual rainfall by city
    plt.figure(figsize=(10, 6), dpi=150)
    # Calculate annual sums
    annual_sum = df.groupby(["City", "Year"])["Rainfall_mm"].sum().reset_index()
    # Average across all years for each city for sorting/plotting
    city_avg_annual = annual_sum.groupby("City")["Rainfall_mm"].mean().sort_values(ascending=False)
    
    colors = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896']
    # Plot line chart of annual rainfall over time for each city
    for i, city in enumerate(city_avg_annual.index):
        city_data = annual_sum[annual_sum["City"] == city].sort_values(by="Year")
        plt.plot(city_data["Year"], city_data["Rainfall_mm"], marker='o', linewidth=2, label=city, color=colors[i % len(colors)])
        
    plt.title("Total Annual Rainfall by City (2015–2025)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Year", fontsize=12)
    plt.ylabel("Annual Rainfall (mm)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(frameon=True, facecolor='white', edgecolor='none')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "annual_rainfall.png"))
    plt.close()
    
    # 2. Monthly rainfall climatology by city
    plt.figure(figsize=(12, 6), dpi=150)
    # Monthly average of daily rainfall
    monthly_avg = df.groupby(["City", "Month"])["Rainfall_mm"].mean().reset_index()
    
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    # Plot bar grouping or lines. Lines are cleaner for 8 cities.
    for i, city in enumerate(city_avg_annual.index):
        city_data = monthly_avg[monthly_avg["City"] == city].sort_values(by="Month")
        plt.plot(month_names, city_data["Rainfall_mm"], marker='s', markersize=4, linewidth=1.5, label=city, color=colors[i % len(colors)])
        
    plt.title("Monthly Rainfall Climatology by City (2015–2025)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Month", fontsize=12)
    plt.ylabel("Average Daily Rainfall (mm)", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(frameon=True, facecolor='white', edgecolor='none')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "monthly_rainfall.png"))
    plt.close()
    
    # 3. Daily rainfall distribution (Log scaled)
    plt.figure(figsize=(10, 6), dpi=150)
    # Filter for rainy days to look at the distribution of non-zero rainfall
    rainy_data = df[df["Rainfall_mm"] > 0]
    
    # Histogram of rainfall values on a log-scale x-axis
    bins = np.logspace(np.log10(0.1), np.log10(rainy_data["Rainfall_mm"].max()), 50)
    plt.hist(rainy_data["Rainfall_mm"], bins=bins, color='#3498db', alpha=0.7, edgecolor='#2980b9', density=True)
    
    plt.xscale('log')
    plt.title("Daily Rainfall Intensity Distribution (Rainy Days Only, Log Scale)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Rainfall (mm/day) - Log Scale", fontsize=12)
    plt.ylabel("Probability Density", fontsize=12)
    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "rainfall_distribution.png"))
    plt.close()
    
    # 4. Year x Month rainfall heatmap for Pune
    plt.figure(figsize=(10, 8), dpi=150)
    pune_df = df[df["City"] == "Pune"]
    # Monthly total rainfall for Pune
    pune_monthly = pune_df.groupby(["Year", "Month"])["Rainfall_mm"].sum().reset_index()
    # Pivot into Year x Month matrix
    pune_pivot = pune_monthly.pivot(index="Year", columns="Month", values="Rainfall_mm")
    pune_pivot.columns = month_names
    
    # Custom simple heatmap using matplotlib's imshow
    plt.imshow(pune_pivot, cmap='Blues', aspect='auto')
    
    # Set axis ticks and labels
    plt.xticks(np.arange(12), month_names)
    plt.yticks(np.arange(len(pune_pivot.index)), pune_pivot.index)
    
    # Add data annotations inside cells
    for y_idx in range(len(pune_pivot.index)):
        for m_idx in range(12):
            val = pune_pivot.iloc[y_idx, m_idx]
            color = "white" if val > pune_pivot.values.max() * 0.55 else "black"
            plt.text(m_idx, y_idx, f"{int(val)}", ha='center', va='center', color=color, fontsize=9)
            
    plt.colorbar(label="Total Monthly Rainfall (mm)")
    plt.title("Pune Rainfall Intensity Heatmap (Year × Month, mm)", fontsize=14, fontweight='bold', pad=15)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "pune_rainfall_heatmap.png"))
    plt.close()
    
    # 5. Top extreme rainfall events
    plt.figure(figsize=(10, 6), dpi=150)
    # Get top 15 extreme events in the whole dataset
    top_events = df.sort_values(by="Rainfall_mm", ascending=False).head(15)
    
    y_labels = [f"{r['City']} ({r['Date']})" for _, r in top_events.iterrows()]
    plt.barh(np.arange(len(y_labels)), top_events["Rainfall_mm"], color='#e74c3c', alpha=0.8, edgecolor='#c0392b')
    plt.yticks(np.arange(len(y_labels)), y_labels)
    plt.gca().invert_yaxis()  # top event at the top
    
    plt.title("Top 15 Extreme Daily Rainfall Events (2015–2025)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Rainfall (mm/day)", fontsize=12)
    plt.grid(True, axis='x', linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, "extreme_events.png"))
    plt.close()
    
    logger.info("Validation plots generated and saved successfully.")

def perform_pune_validation(base_df: pd.DataFrame, 
                            reference_csv_path: str = "data/processed/pune_rainfall_reference.csv", 
                            report_path: str = "reports/pune_validation.txt") -> None:
    """
    Compares the newly extracted Pune rainfall series with the reference dataset.
    Generates reports/pune_validation.txt.
    """
    logger.info("Running mandatory Pune reference dataset validation...")
    
    # Load reference dataset
    if not os.path.exists(reference_csv_path):
        raise FileNotFoundError(f"Reference Pune dataset not found at: {reference_csv_path}")
    
    ref_df = pd.read_csv(reference_csv_path)
    ref_df["Date"] = pd.to_datetime(ref_df["Date"]).dt.strftime("%Y-%m-%d")
    ref_df = ref_df.sort_values(by="Date").reset_index(drop=True)
    
    # Filter newly extracted base dataset for Pune
    extracted_pune = base_df[base_df["City"] == "Pune"].copy()
    extracted_pune["Date"] = pd.to_datetime(extracted_pune["Date"]).dt.strftime("%Y-%m-%d")
    extracted_pune = extracted_pune.sort_values(by="Date").reset_index(drop=True)
    
    pune_records = len(extracted_pune)
    ref_records = len(ref_df)
    
    # 1. Date mismatch check
    # Merge on Date to check matching pairs
    merged = pd.merge(extracted_pune, ref_df, on="Date", suffixes=("_extracted", "_reference"))
    date_mismatch = max(pune_records, ref_records) - len(merged)
    
    # 2. Rainfall mismatch check (with tolerance)
    # Check absolute difference between matched dates
    tolerance = 1e-4
    merged["diff"] = (merged["Rainfall_mm_extracted"] - merged["Rainfall_mm_reference"]).abs()
    rainfall_mismatch = (merged["diff"] > tolerance).sum()
    
    # Overall validation status
    validation_passed = (pune_records == 4018) and (date_mismatch == 0) and (rainfall_mismatch == 0)
    
    # Format and save output
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(f"Pune records: {pune_records}\n")
        f.write(f"Reference records: {ref_records}\n")
        f.write(f"Date mismatch: {date_mismatch}\n")
        f.write(f"Rainfall mismatch: {rainfall_mismatch}\n")
        f.write(f"Validation: {'PASSED' if validation_passed else 'FAILED'}\n")
        
    logger.info(f"Pune validation results saved to {report_path}. Status: {'PASSED' if validation_passed else 'FAILED'}")

def main():
    logger.info("Initializing Rainfall Intelligence Data Preparation Pipeline...")
    
    # 1. Configuration loading
    cities_df = load_cities("data/config/cities.csv")
    thresholds_config = load_thresholds("data/config/rainfall_thresholds.json")
    
    # Setup directories
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    # 2. Rainfall Ingestion & Extraction
    years = list(range(2015, 2026))
    extracted_df = extract_city_rainfall(cities_df, years, "data/raw/imd")
    
    # 3. Save Base Dataset
    base_df = extracted_df.copy()
    dates_dt = pd.to_datetime(base_df["Date"])
    # Construct base columns
    base_df["Year"] = dates_dt.dt.year
    base_df["Month"] = dates_dt.dt.month
    base_df["Day"] = dates_dt.dt.day
    base_df["DayOfYear"] = dates_dt.dt.dayofyear
    
    base_cols = [
        "City", "Date", "Year", "Month", "Day", "DayOfYear", 
        "Latitude", "Longitude", "Grid_Latitude", "Grid_Longitude", "Rainfall_mm"
    ]
    base_df = base_df[base_cols]
    
    base_output_path = "data/processed/rainfall_base_2015_2025.csv"
    base_df.to_csv(base_output_path, index=False)
    logger.info(f"Saved base extracted dataset to: {base_output_path}")
    
    # 4. Perform Data Cleaning Validation & Reports
    validate_base_dataset(base_df)
    generate_quality_reports(base_df, "reports/data_quality_report.csv", "reports/dataset_summary.txt")
    
    # 5. Extract City Elevations (Graceful skip if unavailable)
    elevation_df = extract_city_elevations(cities_df, "data/raw/elevation")
    # Save city elevations report
    city_elev_path = "data/processed/city_elevation.csv"
    elevation_df.to_csv(city_elev_path, index=False)
    logger.info(f"Saved city elevation report to: {city_elev_path}")
    
    # 6. Feature Engineering
    engineered_df = engineer_features(extracted_df, thresholds_config)
    
    # Merge elevation into the engineered dataset
    engineered_df = engineered_df.merge(elevation_df[["City", "Elevation_m"]], on="City", how="left")
    
    # Re-order columns to match request in Section 20
    final_cols = [
        # Identification
        "City", "Date",
        # Geographic
        "Latitude", "Longitude", "Grid_Latitude", "Grid_Longitude", "Elevation_m",
        # Temporal
        "Year", "Month", "Day", "DayOfYear", "DayOfWeek", "WeekOfYear", "Is_Leap_Year", "Month_Sin", "Month_Cos",
        # Current rainfall
        "Rainfall_mm", "Rainy_Day", "Dry_Day",
        # Historical rainfall
        "Rainfall_Lag_1D", "Rainfall_Lag_2D", "Rainfall_Lag_3D", "Rainfall_Lag_7D", "Rainfall_Lag_14D",
        # Rolling/accumulated
        "Rainfall_Rolling_3D", "Rainfall_Rolling_7D", "Rainfall_Rolling_14D", "Rainfall_Rolling_30D",
        "Rainfall_Accumulated_3D", "Rainfall_Accumulated_7D", "Rainfall_Accumulated_14D", "Rainfall_Accumulated_30D",
        # Dry spell
        "Consecutive_Dry_Days",
        # Event classification
        "Rainfall_Category", "Is_Heavy_Rainfall", "Is_Extreme_Event"
    ]
    
    # Verify all expected columns exist
    missing_final_cols = set(final_cols) - set(engineered_df.columns)
    if missing_final_cols:
        logger.error(f"Missing engineered columns in final mapping: {missing_final_cols}")
        
    final_df = engineered_df[final_cols]
    
    # Save Final Dataset
    final_output_path = "data/processed/rainfall_training_dataset_2015_2025.csv"
    final_df.to_csv(final_output_path, index=False)
    logger.info(f"Saved final training dataset to: {final_output_path}")
    
    # 7. Generate Statistical Datasets
    # 7a. Yearly stats
    yearly_stats = final_df.groupby(["City", "Year"]).agg(
        Annual_Rainfall_mm=("Rainfall_mm", "sum"),
        Average_Daily_Rainfall_mm=("Rainfall_mm", "mean"),
        Maximum_Daily_Rainfall_mm=("Rainfall_mm", "max"),
        Rainy_Days=("Rainy_Day", "sum"),
        Dry_Days=("Dry_Day", "sum")
    ).reset_index()
    # Round float columns
    yearly_stats["Annual_Rainfall_mm"] = yearly_stats["Annual_Rainfall_mm"].round(2)
    yearly_stats["Average_Daily_Rainfall_mm"] = yearly_stats["Average_Daily_Rainfall_mm"].round(4)
    yearly_stats["Maximum_Daily_Rainfall_mm"] = yearly_stats["Maximum_Daily_Rainfall_mm"].round(2)
    
    yearly_stats_path = "data/processed/yearly_rainfall_statistics.csv"
    yearly_stats.to_csv(yearly_stats_path, index=False)
    logger.info(f"Saved yearly rainfall statistics to: {yearly_stats_path}")
    
    # 7b. Monthly stats
    monthly_stats = final_df.groupby(["City", "Year", "Month"]).agg(
        Total_Rainfall_mm=("Rainfall_mm", "sum"),
        Average_Daily_Rainfall_mm=("Rainfall_mm", "mean"),
        Maximum_Daily_Rainfall_mm=("Rainfall_mm", "max"),
        Rainy_Days=("Rainy_Day", "sum")
    ).reset_index()
    # Round float columns
    monthly_stats["Total_Rainfall_mm"] = monthly_stats["Total_Rainfall_mm"].round(2)
    monthly_stats["Average_Daily_Rainfall_mm"] = monthly_stats["Average_Daily_Rainfall_mm"].round(4)
    monthly_stats["Maximum_Daily_Rainfall_mm"] = monthly_stats["Maximum_Daily_Rainfall_mm"].round(2)
    
    monthly_stats_path = "data/processed/monthly_rainfall_statistics.csv"
    monthly_stats.to_csv(monthly_stats_path, index=False)
    logger.info(f"Saved monthly rainfall statistics to: {monthly_stats_path}")
    
    # 7c. Extreme rainfall events table (Top events per city, sorted descending by rainfall)
    top_events = final_df.groupby("City").apply(lambda x: x.nlargest(10, "Rainfall_mm")).reset_index(drop=True)
    extreme_cols = ["City", "Date", "Rainfall_mm", "Grid_Latitude", "Grid_Longitude", "Year", "Month"]
    extreme_df = top_events[extreme_cols].sort_values(by="Rainfall_mm", ascending=False).reset_index(drop=True)
    
    extreme_events_path = "data/processed/extreme_rainfall_events.csv"
    extreme_df.to_csv(extreme_events_path, index=False)
    logger.info(f"Saved extreme rainfall events to: {extreme_events_path}")
    
    # Copy stats tables to reports directory as requested by prompt
    yearly_stats.to_csv("reports/yearly_statistics.csv", index=False)
    monthly_stats.to_csv("reports/monthly_statistics.csv", index=False)
    logger.info("Copied yearly and monthly stats reports to reports/ directory.")
    
    # 8. Perform final 10-point validation
    validation_success, _ = perform_final_validation(final_df, num_cities_expected=len(cities_df))
    
    # 9. Perform mandatory Pune Reference Validation
    perform_pune_validation(base_df, "data/processed/pune_rainfall_reference.csv")
    
    # 10. Generate Validation Plots
    generate_validation_plots(final_df)
    
    logger.info(" rainfall dataset pipeline finished successfully.")

if __name__ == "__main__":
    main()
