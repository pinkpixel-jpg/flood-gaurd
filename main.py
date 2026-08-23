import subprocess
import sys
import os

def run_script(module_name_or_file, is_module=True):
    cmd = [sys.executable]
    if is_module:
        cmd.extend(["-m", module_name_or_file])
    else:
        cmd.append(module_name_or_file)
        
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: Command '{' '.join(cmd)}' failed with exit code {e.returncode}")
        return False

def main():
    print("=" * 90)
    print("         RAINFALL INTELLIGENCE SYSTEM ORCHESTRATOR (LEVEL 1 & LEVEL 2)")
    print("=" * 90 + "\n")
    
    # 1. Level 1 - Multi-City Pipeline
    print(">>> RUNNING LEVEL 1: MULTI-CITY DATASET PREPARATION PIPELINE...")
    if not run_script("src.build_dataset"):
        sys.exit(1)
    print("Level 1 Pipeline completed successfully.\n")
        
    # 2. Level 2 - Pune Hyperlocal Spatial Pipeline
    print(">>> RUNNING LEVEL 2: PUNE HYPERLOCAL SPATIAL DATASET PREPARATION PIPELINE...")
    if not run_script("src.pune_build_dataset"):
        sys.exit(1)
    print("Level 2 Pipeline completed successfully.\n")
    
    # 2b. GIS Proximity and Vulnerability Layers
    print(">>> RUNNING GIS VULNERABILITY & LANDSCAPE LAYERS PROCESSOR...")
    if not run_script("src.gis_processor"):
        sys.exit(1)
    print("GIS layers processor completed successfully.\n")
    
    # 3. Spatiotemporal Analysis
    print(">>> RUNNING SPATIOTEMPORAL & CONCENTRATION ANALYSIS...")
    if not run_script("src.spatial_analysis"):
        sys.exit(1)
    print("Spatiotemporal analysis completed successfully.\n")
    
    # 4. Rule-Based Flood Risk Assessment
    print(">>> RUNNING RULE-BASED FLOOD RISK ASSESSMENT...")
    if not run_script("src.flood_risk_analyzer"):
        sys.exit(1)
    print("Flood risk assessment completed successfully.\n")
        
    # 5. Terminal Summary Dashboard
    print(">>> GENERATING PIPELINE REPORT SUMMARY DASHBOARD...")
    if not run_script("display_summary.py", is_module=False):
        sys.exit(1)

if __name__ == "__main__":
    main()
