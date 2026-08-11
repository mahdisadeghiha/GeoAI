"""Baseline change detection using spectral and NDVI differences."""

from dataclasses import dataclass

import numpy as np

from app.core.config import Settings, get_settings
from app.services.ndvi.ndvi_service import compute_ndvi
from app.services.preprocessing.normalize import normalize_raster
from app.utils.raster import RasterData


@dataclass
class ChangeDetectionResult:
    change_mask: RasterData
    change_intensity: RasterData
    ndbi_t1: np.ndarray | None
    ndbi_t2: np.ndarray | None
    built_up_change_percentage: float
    method: str


def compute_ndbi(swir: np.ndarray, nir: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    return (swir - nir) / (swir + nir + eps)


def _threshold_change(intensity: np.ndarray, valid_mask: np.ndarray, sigma: float) -> np.ndarray:
    valid = intensity[valid_mask]
    if valid.size == 0:
        return np.zeros_like(intensity, dtype=bool)
    mean = valid.mean()
    std = valid.std()
    if std < 1e-8:
        return np.abs(intensity - mean) > 0
    threshold = mean + sigma * std
    return (np.abs(intensity - mean) > threshold) & valid_mask


def detect_changes_baseline(
    raster_t1: RasterData,
    raster_t2: RasterData,
    valid_mask: np.ndarray,
    red_idx: int = 3,
    nir_idx: int = 4,
    swir_idx: int = 5,
    settings: Settings | None = None,
) -> ChangeDetectionResult:
    settings = settings or get_settings()

    norm_t1 = normalize_raster(raster_t1)
    norm_t2 = normalize_raster(raster_t2)

    nir_t1 = norm_t1.band(nir_idx)
    nir_t2 = norm_t2.band(nir_idx)
    red_t1 = norm_t1.band(red_idx)
    red_t2 = norm_t2.band(red_idx)

    spectral_diff = np.abs(nir_t2 - nir_t1) + np.abs(red_t2 - red_t1)
    ndvi_diff = np.abs(
        compute_ndvi(raster_t2.band(red_idx), raster_t2.band(nir_idx), settings.ndvi_eps)
        - compute_ndvi(raster_t1.band(red_idx), raster_t1.band(nir_idx), settings.ndvi_eps)
    )
    intensity = 0.6 * spectral_diff + 0.4 * ndvi_diff

    change_mask_arr = _threshold_change(intensity, valid_mask, settings.change_threshold_sigma)

    ndbi_t1 = ndbi_t2 = None
    built_up_change = 0.0
    if raster_t1.array.shape[0] > swir_idx and raster_t2.array.shape[0] > swir_idx:
        swir_t1 = raster_t1.band(swir_idx)
        swir_t2 = raster_t2.band(swir_idx)
        nir_t1_raw = raster_t1.band(nir_idx)
        nir_t2_raw = raster_t2.band(nir_idx)
        ndbi_t1 = compute_ndbi(swir_t1, nir_t1_raw, settings.ndvi_eps)
        ndbi_t2 = compute_ndbi(swir_t2, nir_t2_raw, settings.ndvi_eps)
        mean_t1 = ndbi_t1[valid_mask].mean() if valid_mask.any() else 0.0
        mean_t2 = ndbi_t2[valid_mask].mean() if valid_mask.any() else 0.0
        diff = mean_t2 - mean_t1
        if abs(mean_t1) < 0.05:
            built_up_change = diff * 100.0
        else:
            built_up_change = (diff / abs(mean_t1)) * 100.0

    return ChangeDetectionResult(
        change_mask=RasterData(change_mask_arr.astype(np.uint8), raster_t1.transform, raster_t1.crs, band_names=["CHANGE"]),
        change_intensity=RasterData(intensity.astype(np.float32), raster_t1.transform, raster_t1.crs, band_names=["INTENSITY"]),
        ndbi_t1=ndbi_t1,
        ndbi_t2=ndbi_t2,
        built_up_change_percentage=float(built_up_change),
        method="baseline_spectral_ndvi",
    )
