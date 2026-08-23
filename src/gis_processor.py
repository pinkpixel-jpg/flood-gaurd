import os
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class GISLayerProcessor:
    """
    Modular GIS processor to enrich Pune hyperlocal grid cells with landscape,
    urban, and hydrological vulnerability layers.
    
    Can later be extended to load from actual GIS raster/shapefiles (using GDAL/GeoPandas).
    """
    def __init__(self, metadata_path: str = "data/processed/pune/pune_grid_metadata.csv"):
        self.metadata_path = metadata_path
        if os.path.exists(metadata_path):
            self.grid_df = pd.read_csv(metadata_path)
        else:
            self.grid_df = None
            logger.error(f"Grid metadata not found at: {metadata_path}")

    def compute_derived_gis_layers(self) -> pd.DataFrame:
        """
        Calculates or maps GIS layers for the Pune grid cells.
        For the hackathon demo, this implements a modular fallback system mapping:
        - Slope & Aspect (terrain)
        - Land Cover & Built-Up percentage (surface impermeability)
        - Distance to Drainage & Water Bodies (hydrological proximity)
        - Population Density (socio-economic vulnerability)
        """
        if self.grid_df is None:
            raise FileNotFoundError("Metadata grid dataframe is uninitialized.")
            
        logger.info("Enriching grid cells with modular GIS vulnerability layers...")
        enriched = self.grid_df.copy()
        
        # Static fallback/lookup mappings
        elevations = {
            "PUNE_G001": 560.0,
            "PUNE_G002": 605.0,
            "PUNE_G003": 650.0,
            "PUNE_G004": 615.0
        }
        slopes = {
            "PUNE_G001": 3.5,
            "PUNE_G002": 1.2,
            "PUNE_G003": 7.8,
            "PUNE_G004": 1.5
        }
        aspects = {
            "PUNE_G001": 240.0,
            "PUNE_G002": 90.0,
            "PUNE_G003": 270.0,
            "PUNE_G004": 180.0,
        }
        land_covers = {
            "PUNE_G001": "Urban_Dense",
            "PUNE_G002": "Urban_Suburban",
            "PUNE_G003": "Vegetation_Hilly",
            "PUNE_G004": "Agriculture_Plains"
        }
        built_up_pct = {
            "PUNE_G001": 85.0,
            "PUNE_G002": 55.0,
            "PUNE_G003": 15.0,
            "PUNE_G004": 25.0
        }
        dist_drainage = {
            "PUNE_G001": 150.0,
            "PUNE_G002": 450.0,
            "PUNE_G003": 800.0,
            "PUNE_G004": 350.0
        }
        dist_river = {
            "PUNE_G001": 300.0,
            "PUNE_G002": 950.0,
            "PUNE_G003": 1500.0,
            "PUNE_G004": 200.0
        }
        pop_density = {
            "PUNE_G001": 14500,
            "PUNE_G002": 6800,
            "PUNE_G003": 1200,
            "PUNE_G004": 2200
        }

        # Try to sample from merged TIF file
        merged_tif_path = "data/raw/elevation/pune_merged.tif"
        use_raster = False
        if os.path.exists(merged_tif_path):
            try:
                import rasterio
                use_raster = True
                logger.info(f"Loading real GIS features from merged GeoTIFF: {merged_tif_path}")
            except ImportError:
                logger.warning("rasterio package not available. Falling back to static GIS mappings.")

        final_elevs = []
        final_slopes = []
        final_lc = []
        final_builtup = []

        # ESA WorldCover class mapping
        lc_map = {
            10: ("Vegetation_Hilly", 15.0),
            20: ("Vegetation_Hilly", 15.0),
            30: ("Vegetation_Hilly", 15.0),
            40: ("Agriculture_Plains", 25.0),
            50: ("Urban_Dense", 85.0),
            60: ("Agriculture_Plains", 20.0), # Barren
            80: ("Water_Bodies", 0.0),
            90: ("Wetland", 5.0)
        }

        if use_raster:
            try:
                with rasterio.open(merged_tif_path) as src:
                    for _, row in self.grid_df.iterrows():
                        grid_id = row["Grid_ID"]
                        lat = row["Latitude"]
                        lon = row["Longitude"]
                        
                        # Bounds check in EPSG:4326 (WGS84)
                        if (src.bounds.left <= lon <= src.bounds.right and 
                            src.bounds.bottom <= lat <= src.bounds.top):
                            
                            coords = [(lon, lat)]
                            try:
                                sample_gen = src.sample(coords)
                                vals = next(sample_gen)
                                elev_val = float(vals[0])
                                slope_val = float(vals[1])
                                lc_code = int(vals[2])
                                
                                # Check nodata
                                if src.nodata is not None and any(v == src.nodata for v in vals):
                                    raise ValueError("Sampled nodata value")
                                    
                                # Map land cover
                                lc_str, built_up_val = lc_map.get(lc_code, ("Urban_Suburban", 55.0))
                                
                                final_elevs.append(elev_val)
                                final_slopes.append(slope_val)
                                final_lc.append(lc_str)
                                final_builtup.append(built_up_val)
                                logger.info(f"Grid {grid_id} sampled from raster: Elev={elev_val:.1f}m, Slope={slope_val:.2f}deg, LC={lc_str} ({lc_code})")
                            except Exception as sample_err:
                                logger.warning(f"Error sampling grid {grid_id} at ({lat}, {lon}): {sample_err}. Using fallback.")
                                final_elevs.append(elevations[grid_id])
                                final_slopes.append(slopes[grid_id])
                                final_lc.append(land_covers[grid_id])
                                final_builtup.append(built_up_pct[grid_id])
                        else:
                            # Out of bounds
                            logger.info(f"Grid {grid_id} at ({lat}, {lon}) is out of raster bounds. Using fallback.")
                            final_elevs.append(elevations[grid_id])
                            final_slopes.append(slopes[grid_id])
                            final_lc.append(land_covers[grid_id])
                            final_builtup.append(built_up_pct[grid_id])
            except Exception as raster_err:
                logger.error(f"Failed to read/process merged GeoTIFF: {raster_err}. Using all fallback values.")
                use_raster = False

        if not use_raster:
            final_elevs = [elevations[gid] for gid in self.grid_df["Grid_ID"]]
            final_slopes = [slopes[gid] for gid in self.grid_df["Grid_ID"]]
            final_lc = [land_covers[gid] for gid in self.grid_df["Grid_ID"]]
            final_builtup = [built_up_pct[gid] for gid in self.grid_df["Grid_ID"]]

        # Populate dataframe columns
        enriched["Elevation_m"] = final_elevs
        enriched["Slope_deg"] = final_slopes
        enriched["Aspect_deg"] = enriched["Grid_ID"].map(aspects)
        enriched["Land_Cover"] = final_lc
        enriched["Built_up_Percentage"] = final_builtup
        enriched["Distance_to_Drainage_m"] = enriched["Grid_ID"].map(dist_drainage)
        enriched["Distance_to_Water_Bodies_m"] = enriched["Grid_ID"].map(dist_river)
        enriched["Population_Density_per_km2"] = enriched["Grid_ID"].map(pop_density)
        
        logger.info("GIS layers enrichment complete.")
        return enriched

    def merge_to_training_dataset(self, training_path: str = "data/processed/pune/pune_training_dataset_2015_2025.csv") -> None:
        """
        Merges GIS layers into the final spatiotemporal training dataset.
        """
        if not os.path.exists(training_path):
            logger.error(f"Training dataset not found at: {training_path}")
            return
            
        gis_df = self.compute_derived_gis_layers()
        train_df = pd.read_csv(training_path)
        
        logger.info("Merging GIS layers with training dataset...")
        
        # Drop existing elevation if present in train_df to prevent duplicate suffix columns
        if "Elevation_m" in train_df.columns:
            train_df = train_df.drop(columns=["Elevation_m"])
            
        # Select GIS columns to merge
        gis_cols = [
            "Grid_ID", "Elevation_m", "Slope_deg", "Aspect_deg", "Land_Cover", 
            "Built_up_Percentage", "Distance_to_Drainage_m", "Distance_to_Water_Bodies_m", "Population_Density_per_km2"
        ]
        
        merged_df = train_df.merge(gis_df[gis_cols], on="Grid_ID", how="left")
        
        # Save back
        merged_df.to_csv(training_path, index=False)
        logger.info(f"Successfully saved GIS-enriched dataset to: {training_path}")

def main():
    processor = GISLayerProcessor()
    
    # Save enriched metadata lookup separately
    gis_meta = processor.compute_derived_gis_layers()
    enriched_meta_path = "data/processed/pune/pune_grid_metadata_enriched.csv"
    gis_meta.to_csv(enriched_meta_path, index=False)
    logger.info(f"Saved enriched grid metadata lookup to: {enriched_meta_path}")
    
    # Merge into training dataset
    processor.merge_to_training_dataset()

if __name__ == "__main__":
    main()
