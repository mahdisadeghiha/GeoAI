"""Change Vector Analysis (CVA) for multi-temporal change detection."""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import inv

from app.core.config import Settings, get_settings
from app.services.change_detection.baseline import ChangeDetectionResult
from app.utils.raster import RasterData


def detect_changes_cva(
    raster_t1: RasterData,
    raster_t2: RasterData,
    valid_mask: np.ndarray,
    red_idx: int = 3,
    nir_idx: int = 4,
    swir_idx: int = 5,
    settings: Settings | None = None,
    chi2_threshold: float = 5.991,
) -> ChangeDetectionResult:
    """CVA in NIR-Red feature space with Mahalanobis distance threshold."""
    settings = settings or get_settings()

    t1 = np.stack([raster_t1.band(nir_idx), raster_t1.band(red_idx)], axis=-1)
    t2 = np.stack([raster_t2.band(nir_idx), raster_t2.band(red_idx)], axis=-1)
    diff = t2 - t1

    valid_pixels = valid_mask.ravel()
    diff_flat = diff.reshape(-1, 2)[valid_pixels]
    if diff_flat.shape[0] < 3:
        from app.services.change_detection.baseline import detect_changes_baseline
        result = detect_changes_baseline(raster_t1, raster_t2, valid_mask, red_idx, nir_idx, swir_idx, settings)
        result.method = "baseline_fallback"
        return result

    mean = diff_flat.mean(axis=0)
    cov = np.cov(diff_flat, rowvar=False)
    if cov.ndim < 2:
        cov = np.array([[cov + 1e-6, 0], [0, cov + 1e-6]])
    cov += np.eye(2) * 1e-6
    cov_inv = inv(cov)

    mahal = np.zeros(diff.shape[:2], dtype=np.float32)
    for y in range(diff.shape[0]):
        for x in range(diff.shape[1]):
            if not valid_mask[y, x]:
                continue
            d = diff[y, x] - mean
            mahal[y, x] = float(d @ cov_inv @ d.T)

    change_mask_arr = (mahal > chi2_threshold) & valid_mask

    built_up_change = 0.0
    ndbi_t1 = ndbi_t2 = None
    if raster_t1.array.shape[0] > swir_idx:
        from app.services.change_detection.baseline import compute_ndbi

        nir_t1 = raster_t1.band(nir_idx)
        nir_t2 = raster_t2.band(nir_idx)
        ndbi_t1 = compute_ndbi(raster_t1.band(swir_idx), nir_t1, settings.ndvi_eps)
        ndbi_t2 = compute_ndbi(raster_t2.band(swir_idx), nir_t2, settings.ndvi_eps)
        mean_t1 = ndbi_t1[valid_mask].mean()
        mean_t2 = ndbi_t2[valid_mask].mean()
        if abs(mean_t1) > settings.ndvi_eps:
            built_up_change = ((mean_t2 - mean_t1) / abs(mean_t1)) * 100.0

    return ChangeDetectionResult(
        change_mask=RasterData(change_mask_arr.astype(np.uint8), raster_t1.transform, raster_t1.crs, band_names=["CHANGE"]),
        change_intensity=RasterData(mahal, raster_t1.transform, raster_t1.crs, band_names=["CVA_INTENSITY"]),
        ndbi_t1=ndbi_t1,
        ndbi_t2=ndbi_t2,
        built_up_change_percentage=float(built_up_change),
        method="cva_mahalanobis",
    )
