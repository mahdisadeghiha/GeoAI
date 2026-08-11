"""NDVI computation and vegetation change analysis."""

from dataclasses import dataclass

import numpy as np

from app.core.config import Settings, get_settings
from app.utils.raster import RasterData, RasterLoader


@dataclass
class NDVIResult:
    ndvi_t1: RasterData
    ndvi_t2: RasterData
    ndvi_diff: RasterData
    ndvi_t1_mean: float
    ndvi_t2_mean: float
    ndvi_diff_mean: float
    vegetation_change_percentage: float


def compute_ndvi(red: np.ndarray, nir: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    return (nir - red) / (nir + red + eps)


def _mean_valid(values: np.ndarray, mask: np.ndarray | None = None) -> float:
    if mask is not None:
        values = values[mask]
    valid = values[np.isfinite(values)]
    if valid.size == 0:
        return 0.0
    return float(valid.mean())


def analyze_ndvi(
    raster_t1: RasterData,
    raster_t2: RasterData,
    valid_mask: np.ndarray,
    red_idx: int = 3,
    nir_idx: int = 4,
    settings: Settings | None = None,
) -> NDVIResult:
    settings = settings or get_settings()
    eps = settings.ndvi_eps

    red_t1 = raster_t1.band(red_idx)
    nir_t1 = raster_t1.band(nir_idx)
    red_t2 = raster_t2.band(red_idx)
    nir_t2 = raster_t2.band(nir_idx)

    ndvi_t1_arr = compute_ndvi(red_t1, nir_t1, eps)
    ndvi_t2_arr = compute_ndvi(red_t2, nir_t2, eps)
    ndvi_diff_arr = ndvi_t2_arr - ndvi_t1_arr

    ndvi_t1 = RasterData(ndvi_t1_arr, raster_t1.transform, raster_t1.crs, band_names=["NDVI"])
    ndvi_t2 = RasterData(ndvi_t2_arr, raster_t2.transform, raster_t2.crs, band_names=["NDVI"])
    ndvi_diff = RasterData(ndvi_diff_arr, raster_t2.transform, raster_t2.crs, band_names=["NDVI_DIFF"])

    mean_t1 = _mean_valid(ndvi_t1_arr, valid_mask)
    mean_t2 = _mean_valid(ndvi_t2_arr, valid_mask)
    diff_mean = mean_t2 - mean_t1
    if abs(mean_t1) < 0.05:
        veg_change_pct = diff_mean * 100.0
    else:
        veg_change_pct = (diff_mean / abs(mean_t1)) * 100.0

    return NDVIResult(
        ndvi_t1=ndvi_t1,
        ndvi_t2=ndvi_t2,
        ndvi_diff=ndvi_diff,
        ndvi_t1_mean=mean_t1,
        ndvi_t2_mean=mean_t2,
        ndvi_diff_mean=diff_mean,
        vegetation_change_percentage=veg_change_pct,
    )


def save_ndvi_outputs(result: NDVIResult, output_dir) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "ndvi_t1": str(RasterLoader.save(result.ndvi_t1, output_dir / "ndvi_t1.tif")),
        "ndvi_t2": str(RasterLoader.save(result.ndvi_t2, output_dir / "ndvi_t2.tif")),
        "ndvi_diff": str(RasterLoader.save(result.ndvi_diff, output_dir / "ndvi_diff.tif")),
    }
    return paths
