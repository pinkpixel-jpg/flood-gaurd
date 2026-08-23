import os
import pandas as pd

def print_separator(char="=", length=60):
    print(char * length)

def display_file_content(filepath, title):
    if not os.path.exists(filepath):
        print(f"\n[Warning] {title} file not found at: {filepath}")
        return
    print_separator("=", 60)
    print(f" {title.upper()} ")
    print_separator("=", 60)
    with open(filepath, "r") as f:
        print(f.read().strip())
    print()

def display_extreme_events(filepath="data/processed/extreme_rainfall_events.csv", limit=10):
    if not os.path.exists(filepath):
        print(f"\n[Warning] Level 1 Extreme events file not found at: {filepath}")
        return
    print_separator("=", 60)
    print(f" TOP {limit} EXTREME RAINFALL EVENTS (LEVEL 1) ")
    print_separator("=", 60)
    df = pd.read_csv(filepath)
    preview = df.head(limit)
    
    # Format a pretty printed text table
    header = f"{'City':<12} | {'Date':<10} | {'Rainfall (mm)':<13} | {'Grid Lat/Lon':<13} | {'Year':<4} | {'Month':<2}"
    print(header)
    print("-" * len(header))
    for _, row in preview.iterrows():
        coords = f"{row['Grid_Latitude']},{row['Grid_Longitude']}"
        line = f"{row['City']:<12} | {row['Date']:<10} | {row['Rainfall_mm']:>13.2f} | {coords:<13} | {int(row['Year']):<4} | {int(row['Month']):<2}"
        print(line)
    print()

def display_pune_grid_statistics(filepath="data/processed/pune/pune_grid_statistics.csv"):
    if not os.path.exists(filepath):
        print(f"\n[Warning] Pune grid statistics file not found at: {filepath}")
        return
    print_separator("=", 60)
    print(" PUNE GRID-WISE CLIMATE STATISTICS (LEVEL 2) ")
    print_separator("=", 60)
    df = pd.read_csv(filepath)
    
    header = f"{'Grid_ID':<8} | {'Lat/Lon':<13} | {'Mean (mm)':<9} | {'Total (mm)':<11} | {'Max (mm)':<8} | {'Rainy Days':<10} | {'Dry Days':<8} | {'Heavy':<5} | {'Extreme':<7} | {'Max Dry Spell':<13}"
    print(header)
    print("-" * len(header))
    for _, row in df.iterrows():
        coords = f"{row['Latitude']:.2f},{row['Longitude']:.2f}"
        line = f"{row['Grid_ID']:<8} | {coords:<13} | {row['Mean_Rainfall_mm']:>9.4f} | {row['Total_Rainfall_mm']:>11.2f} | {row['Maximum_Daily_Rainfall_mm']:>8.2f} | {int(row['Rainy_Days']):>10} | {int(row['Dry_Days']):>8} | {int(row['Heavy_Rainfall_Days']):>5} | {int(row['Extreme_Rainfall_Days']):>7} | {int(row['Longest_Dry_Spell']):>13}"
        print(line)
    print()

def display_pune_extreme_events(filepath="data/processed/pune/pune_extreme_rainfall_events.csv", limit=10):
    if not os.path.exists(filepath):
        print(f"\n[Warning] Pune spatial extreme events file not found at: {filepath}")
        return
    print_separator("=", 60)
    print(f" TOP {limit} PUNE HYPERLOCAL SPATIAL EXTREME EVENTS (LEVEL 2) ")
    print_separator("=", 60)
    df = pd.read_csv(filepath)
    preview = df.head(limit)
    
    header = f"{'Grid_ID':<8} | {'Date':<10} | {'Rainfall (mm)':<13} | {'Lat/Lon':<13} | {'Year':<4} | {'Month':<2} | {'Grid Max':<8} | {'Year Max':<8} | {'Month Max':<9} | {'Heavy Days':<10} | {'Extreme Days':<12}"
    print(header)
    print("-" * len(header))
    for _, row in preview.iterrows():
        coords = f"{row['Latitude']:.2f},{row['Longitude']:.2f}"
        line = f"{row['Grid_ID']:<8} | {row['Date']:<10} | {row['Rainfall_mm']:>13.2f} | {coords:<13} | {int(row['Year']):<4} | {int(row['Month']):<2} | {row['Maximum_Daily_Rainfall_mm']:>8.2f} | {row['Yearly_Maximum_Rainfall_mm']:>8.2f} | {row['Monthly_Maximum_Rainfall_mm']:>9.2f} | {int(row['Heavy_Rainfall_Days']):>10} | {int(row['Extreme_Rainfall_Days']):>12}"
        print(line)
    print()

def main():
    print("\n" + "=" * 120)
    print("      RAINFALL INTELLIGENCE PIPELINE SUMMARY DASHBOARD (LEVEL 1 & LEVEL 2)")
    print("=" * 120 + "\n")
    
    print("================================================================================")
    print("                      LEVEL 1 - MULTI-CITY PIPELINE OUTPUTS                     ")
    print("================================================================================\n")
    
    # 1. Display Pune validation
    display_file_content("reports/pune_validation.txt", "Pune Reference Validation (Level 1)")
    
    # 2. Display final 10-point dataset validation
    display_file_content("reports/final_dataset_validation.txt", "10-Point Dataset Validation (Level 1)")
    
    # 3. Display city statistics summary
    display_file_content("reports/dataset_summary.txt", "Dataset Quality Summary (Level 1)")
    
    # 4. Display top extreme events
    display_extreme_events()
    
    print("\n================================================================================")
    print("               LEVEL 2 - HYPERLOCAL PUNE SPATIAL DATASET OUTPUTS                ")
    print("================================================================================\n")
    
    # 5. Display Pune spatial validation report
    display_file_content("reports/pune_spatial_validation.txt", "Pune Spatial 10-Point Validation (Level 2)")
    
    # 6. Display Pune reference grid validation report (Section 18)
    display_file_content("reports/pune_reference_grid_validation.txt", "Pune Reference Grid Validation (Level 2)")
    
    # 7. Display Pune grid-wise statistics
    display_pune_grid_statistics()
    
    # 8. Display Pune spatial extreme events
    display_pune_extreme_events()
    
    print_separator("=", 120)
    print(" Dashboard display completed. All files are ready in reports/ and data/processed/.")
    print("=" * 120 + "\n")

if __name__ == "__main__":
    main()
