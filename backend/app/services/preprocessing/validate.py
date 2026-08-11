"""Raster validation utilities."""

from pathlib import Path

import rasterio

from app.utils.raster import RasterData, RasterLoader

REQUIRED_BANDS = {"B04", "B08", "B11", "B02", "B03"}


def validate_raster(path: str | Path, min_bands: int = 3) -> RasterData:
    """Validate that a raster exists and has required geospatial metadata."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Raster file not found: {path}")
    if path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError(f"Unsupported raster format: {path.suffix}")

    with rasterio.open(path) as src:
        if src.count < min_bands:
            raise ValueError(f"Raster must have at least {min_bands} bands, found {src.count}")
        if src.transform is None or src.crs is None:
            raise ValueError("Raster must have CRS and geotransform")
        if src.width < 2 or src.height < 2:
            raise ValueError("Raster dimensions too small for analysis")

    return RasterLoader.load(path)
