import os
import argparse
import logging
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def merge_rasters(
    elevation_path: str = "python_folder/pune_elevation.tif",
    slope_path: str = "python_folder/pune_slope.tif",
    landcover_path: str = "python_folder/pune_landcover.tif",
    output_path: str = "python_folder/pune_merged.tif",
    target_res: str = "high"
):
    """
    Merges Pune elevation, slope, and landcover datasets into a single 3-band GeoTIFF.
    
    Bands:
      Band 1: Elevation (m)
      Band 2: Slope (deg)
      Band 3: Land Cover classification code (ESA WorldCover)
    """
    logger.info(f"Starting raster merge process. Target resolution mode: {target_res}")
    
    # 1. Open all source rasters
    with rasterio.open(elevation_path) as src_elev, \
         rasterio.open(slope_path) as src_slope, \
         rasterio.open(landcover_path) as src_lc:
         
        logger.info(f"Elevation: {src_elev.width}x{src_elev.height}, CRS: {src_elev.crs}")
        logger.info(f"Slope: {src_slope.width}x{src_slope.height}, CRS: {src_slope.crs}")
        logger.info(f"Land Cover: {src_lc.width}x{src_lc.height}, CRS: {src_lc.crs}")
        
        # Determine target profile
        if target_res.lower() == "high":
            # Target matches landcover (high resolution)
            target_meta = src_lc.meta.copy()
            target_meta.update({
                'count': 3,
                'dtype': 'float32',  # Use float32 to hold float slope values
                'nodata': -9999.0
            })
            target_shape = (src_lc.height, src_lc.width)
            target_transform = src_lc.transform
            target_crs = src_lc.crs
        else:
            # Target matches elevation/slope (low resolution)
            target_meta = src_elev.meta.copy()
            target_meta.update({
                'count': 3,
                'dtype': 'float32',
                'nodata': -9999.0
            })
            target_shape = (src_elev.height, src_elev.width)
            target_transform = src_elev.transform
            target_crs = src_elev.crs
            
        logger.info(f"Target dimensions: {target_shape[1]}x{target_shape[0]} (width x height)")
        
        # Prepare arrays for target bands
        band1_data = np.empty(target_shape, dtype=np.float32)
        band2_data = np.empty(target_shape, dtype=np.float32)
        band3_data = np.empty(target_shape, dtype=np.float32)
        
        # 2. Resample / Reproject and read Band 1 (Elevation)
        logger.info("Resampling and reading Band 1 (Elevation)...")
        reproject(
            source=rasterio.band(src_elev, 1),
            destination=band1_data,
            src_transform=src_elev.transform,
            src_crs=src_elev.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear
        )
        
        # 3. Resample / Reproject and read Band 2 (Slope)
        logger.info("Resampling and reading Band 2 (Slope)...")
        reproject(
            source=rasterio.band(src_slope, 1),
            destination=band2_data,
            src_transform=src_slope.transform,
            src_crs=src_slope.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear
        )
        
        # 4. Resample / Reproject and read Band 3 (Land Cover)
        logger.info("Resampling and reading Band 3 (Land Cover)...")
        # For categorical data like land cover, we MUST use nearest-neighbor resampling
        reproject(
            source=rasterio.band(src_lc, 1),
            destination=band3_data,
            src_transform=src_lc.transform,
            src_crs=src_lc.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.nearest
        )
        
        # 5. Write to target multiband file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        logger.info(f"Writing merged rasters to: {output_path}")
        with rasterio.open(output_path, 'w', **target_meta) as dst:
            dst.write(band1_data, 1)
            dst.set_band_description(1, "Elevation (m)")
            
            dst.write(band2_data, 2)
            dst.set_band_description(2, "Slope (degrees)")
            
            dst.write(band3_data, 3)
            dst.set_band_description(3, "Land Cover (ESA class)")
            
    logger.info("Raster merge process completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge Pune elevation, slope, and landcover into a multiband TIF.")
    parser.add_argument("--res", type=str, choices=["high", "low"], default="high", 
                        help="Target resolution mode: 'high' (matches land cover, default) or 'low' (matches elevation/slope).")
    parser.add_argument("--output", type=str, default="python_folder/pune_merged.tif",
                        help="Output path for the merged TIF file.")
    args = parser.parse_args()
    
    # Run merge to output path
    merge_rasters(output_path=args.output, target_res=args.res)
    
    # Also save a copy in the expected pipeline raw data directory: data/raw/elevation/pune_merged.tif
    pipeline_raw_path = "data/raw/elevation/pune_merged.tif"
    os.makedirs(os.path.dirname(pipeline_raw_path), exist_ok=True)
    logger.info(f"Copying merged file to pipeline raw directory: {pipeline_raw_path}")
    import shutil
    shutil.copy(args.output, pipeline_raw_path)
    logger.info("Copy complete.")
