import os
import sys
import pandas as pd
import numpy as np

# Configure standard output to use UTF-8 to prevent Windows terminal print errors
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_vulnerability(grid_id):
    # Static mapping based on geographic location and urban density
    if grid_id == "PUNE_G001":
        return {
            "zone": "Central Urban Area",
            "elevation": "Low",
            "built_up": "High",
            "drainage": "Poor",
            "waterlogging": "Frequent"
        }
    elif grid_id == "PUNE_G002":
        return {
            "zone": "Eastern Suburban",
            "elevation": "Low",
            "built_up": "Moderate",
            "drainage": "Moderate",
            "waterlogging": "Moderate"
        }
    elif grid_id == "PUNE_G003":
        return {
            "zone": "Northern Suburban Area",
            "elevation": "High",
            "built_up": "Moderate",
            "drainage": "Moderate",
            "waterlogging": "Moderate"
        }
    else:  # PUNE_G004
        return {
            "zone": "Northeastern Plains",
            "elevation": "Low",
            "built_up": "Low",
            "drainage": "Good",
            "waterlogging": "Rare"
        }

def compute_risk(row):
    vuln = get_vulnerability(row["Grid_ID"])
    
    # Base score
    score = 0
    
    # 1. 24h Rainfall contribution
    rain = row["Rainfall_mm"]
    if rain > 115.5:  # Extreme
        score += 4
    elif rain > 64.4:  # Heavy
        score += 3
    elif rain > 15.5:  # Moderate
        score += 1.5
        
    # 2. Prior saturation (previous 7 days accumulated rain)
    accum = row["Rainfall_Accumulated_7D"]
    if accum > 150:
        score += 3
    elif accum > 100:
        score += 2
    elif accum > 50:
        score += 1
        
    # 3. Built-up and drainage vulnerability contribution
    if vuln["built_up"] == "High":
        score += 2
    elif vuln["built_up"] == "Moderate":
        score += 1
        
    if vuln["drainage"] == "Poor":
        score += 2
    elif vuln["drainage"] == "Moderate":
        score += 1
        
    # Determine risk category
    if score >= 8:
        return "🔴 HIGH", score
    elif score >= 4.5:
        return "🟡 MODERATE", score
    else:
        return "🟢 LOW", score

def print_risk_block(row, risk_label):
    vuln = get_vulnerability(row["Grid_ID"])
    print("PUNE FLOOD RISK")
    print("────────────────────")
    print(f"\nZone: {vuln['zone']} ({row['Grid_ID']}) on {row['Date']}")
    print("\nRainfall:")
    print(f"{row['Rainfall_mm']:.1f} mm / 24h")
    print("\nPrevious 7-day rainfall:")
    print(f"{row['Rainfall_Accumulated_7D']:.1f} mm")
    print("\nElevation:")
    print(vuln["elevation"])
    print("\nBuilt-up:")
    print(vuln["built_up"])
    print("\nDrainage proximity:")
    print(vuln["drainage"])
    print("\nHistorical waterlogging:")
    print(vuln["waterlogging"])
    print("\nRisk:")
    print(risk_label)
    print("\n" + "="*40 + "\n")

def main():
    filepath = "data/processed/pune/pune_training_dataset_2015_2025.csv"
    if not os.path.exists(filepath):
        print(f"Error: Training dataset not found at {filepath}")
        return
        
    df = pd.read_csv(filepath)
    
    # Calculate risks and scores for each row
    risks = []
    scores = []
    for _, row in df.iterrows():
        risk_label, score = compute_risk(row)
        risks.append(risk_label)
        scores.append(score)
        
    df["Computed_Risk"] = risks
    df["Risk_Score"] = scores
    
    # Find the top 3 high-risk events to print
    high_risk_events = df[df["Computed_Risk"] == "🔴 HIGH"].sort_values(by="Risk_Score", ascending=False).head(3)
    
    if len(high_risk_events) == 0:
        # Fallback to highest score overall
        high_risk_events = df.sort_values(by="Risk_Score", ascending=False).head(3)
        
    print("\n" + "#" * 50)
    print("          PUNE FLOOD RISK ASSESSMENT REPORTS")
    print("#" * 50 + "\n")
    
    for _, row in high_risk_events.iterrows():
        print_risk_block(row, row["Computed_Risk"])

if __name__ == "__main__":
    main()
