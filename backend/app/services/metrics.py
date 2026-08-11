"""Compute extended geospatial / spectral analytics for the dashboard."""

from __future__ import annotations

from typing import Any

import numpy as np

from app.services.change_detection.baseline import compute_ndbi
from app.services.ndvi.ndvi_service import compute_ndvi
from app.services.spatial_analysis.polygonize import SpatialAnalysisResult
from app.utils.raster import RasterData, pixel_area_km2, pixel_area_m2


def _safe(value: float, digits: int = 4) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    return round(float(value), digits)


def _arr_stats(values: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    data = values[mask]
    data = data[np.isfinite(data)]
    if data.size == 0:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p25": 0.0,
            "p75": 0.0,
        }
    return {
        "mean": _safe(float(np.mean(data))),
        "median": _safe(float(np.median(data))),
        "std": _safe(float(np.std(data))),
        "min": _safe(float(np.min(data))),
        "max": _safe(float(np.max(data))),
        "p25": _safe(float(np.percentile(data, 25))),
        "p75": _safe(float(np.percentile(data, 75))),
    }


def compute_savi(red: np.ndarray, nir: np.ndarray, l: float = 0.5, eps: float = 1e-8) -> np.ndarray:
    return ((nir - red) / (nir + red + l + eps)) * (1.0 + l)


def compute_ndwi(green: np.ndarray, nir: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    return (green - nir) / (green + nir + eps)


def build_extended_metrics(
    raster_t1: RasterData,
    raster_t2: RasterData,
    valid_mask: np.ndarray,
    change_mask: np.ndarray,
    intensity: np.ndarray,
    ndvi_t1: np.ndarray,
    ndvi_t2: np.ndarray,
    spatial: SpatialAnalysisResult,
    red_idx: int,
    nir_idx: int,
    swir_idx: int,
    green_idx: int = 1,
    method: str = "baseline",
    year_t1: int | None = None,
    year_t2: int | None = None,
    eps: float = 1e-8,
) -> dict[str, Any]:
    pixel_km2 = pixel_area_km2(raster_t1.transform)
    pixel_m2 = pixel_area_m2(raster_t1.transform)
    valid_pixels = int(valid_mask.sum())
    change_bool = change_mask.astype(bool) & valid_mask
    changed_pixels = int(change_bool.sum())
    unchanged_pixels = max(valid_pixels - changed_pixels, 0)

    study_area_km2 = valid_pixels * pixel_km2
    changed_area_km2 = changed_pixels * pixel_km2
    unchanged_area_km2 = unchanged_pixels * pixel_km2
    change_percentage = (changed_area_km2 / study_area_km2 * 100.0) if study_area_km2 > 0 else 0.0

    ndvi_diff = ndvi_t2 - ndvi_t1
    veg_loss = (ndvi_diff < -0.1) & valid_mask
    veg_gain = (ndvi_diff > 0.1) & valid_mask
    veg_stable = (~veg_loss) & (~veg_gain) & valid_mask

    red_t1 = raster_t1.band(red_idx)
    red_t2 = raster_t2.band(red_idx)
    nir_t1 = raster_t1.band(nir_idx)
    nir_t2 = raster_t2.band(nir_idx)
    green_t1 = raster_t1.band(green_idx) if raster_t1.array.shape[0] > green_idx else red_t1
    green_t2 = raster_t2.band(green_idx) if raster_t2.array.shape[0] > green_idx else red_t2

    savi_t1 = compute_savi(red_t1, nir_t1, eps=eps)
    savi_t2 = compute_savi(red_t2, nir_t2, eps=eps)
    ndwi_t1 = compute_ndwi(green_t1, nir_t1, eps=eps)
    ndwi_t2 = compute_ndwi(green_t2, nir_t2, eps=eps)

    ndbi_t1 = ndbi_t2 = None
    built_gain = built_loss = np.zeros_like(valid_mask, dtype=bool)
    if raster_t1.array.shape[0] > swir_idx:
        ndbi_t1 = compute_ndbi(raster_t1.band(swir_idx), nir_t1, eps)
        ndbi_t2 = compute_ndbi(raster_t2.band(swir_idx), nir_t2, eps)
        ndbi_diff = ndbi_t2 - ndbi_t1
        built_gain = (ndbi_diff > 0.1) & valid_mask
        built_loss = (ndbi_diff < -0.1) & valid_mask

    ndvi_t1_mean = float(ndvi_t1[valid_mask].mean()) if valid_pixels else 0.0
    ndvi_t2_mean = float(ndvi_t2[valid_mask].mean()) if valid_pixels else 0.0
    if abs(ndvi_t1_mean) < 0.05:
        vegetation_change_percentage = (ndvi_t2_mean - ndvi_t1_mean) * 100.0
    else:
        vegetation_change_percentage = ((ndvi_t2_mean - ndvi_t1_mean) / abs(ndvi_t1_mean)) * 100.0

    if ndbi_t1 is not None and ndbi_t2 is not None:
        ndbi_t1_mean = float(ndbi_t1[valid_mask].mean())
        ndbi_t2_mean = float(ndbi_t2[valid_mask].mean())
        if abs(ndbi_t1_mean) < 0.05:
            built_up_change_percentage = (ndbi_t2_mean - ndbi_t1_mean) * 100.0
        else:
            built_up_change_percentage = ((ndbi_t2_mean - ndbi_t1_mean) / abs(ndbi_t1_mean)) * 100.0
    else:
        ndbi_t1_mean = ndbi_t2_mean = built_up_change_percentage = 0.0

    region_areas = [f["properties"]["area_km2"] for f in spatial.geojson.get("features", [])]
    region_scores = [f["properties"]["change_score"] for f in spatial.geojson.get("features", [])]

    west, south, east, north = raster_t1.bounds
    # Convert approximate display bounds; keep native for metadata
    return {
        "overview": {
            "detection_method": method,
            "year_t1": year_t1,
            "year_t2": year_t2,
            "time_span_years": (year_t2 - year_t1) if (year_t1 is not None and year_t2 is not None) else None,
            "crs": raster_t1.crs,
            "width_px": int(raster_t1.width),
            "height_px": int(raster_t1.height),
            "pixel_size_m": _safe(np.sqrt(pixel_m2), 2),
            "pixel_area_m2": _safe(pixel_m2, 2),
            "valid_pixels": valid_pixels,
            "changed_pixels": changed_pixels,
            "unchanged_pixels": unchanged_pixels,
            "bounds_native": [ _safe(west, 2), _safe(south, 2), _safe(east, 2), _safe(north, 2) ],
        },
        "extent": {
            "study_area_km2": _safe(study_area_km2),
            "changed_area_km2": _safe(changed_area_km2),
            "unchanged_area_km2": _safe(unchanged_area_km2),
            "change_percentage": _safe(change_percentage, 2),
            "unchanged_percentage": _safe(100.0 - change_percentage, 2),
            "vegetation_loss_km2": _safe(veg_loss.sum() * pixel_km2),
            "vegetation_gain_km2": _safe(veg_gain.sum() * pixel_km2),
            "vegetation_stable_km2": _safe(veg_stable.sum() * pixel_km2),
            "built_up_gain_km2": _safe(built_gain.sum() * pixel_km2),
            "built_up_loss_km2": _safe(built_loss.sum() * pixel_km2),
        },
        "change_summary": {
            "vegetation_change_percentage": _safe(vegetation_change_percentage, 2),
            "built_up_change_percentage": _safe(built_up_change_percentage, 2),
            "num_change_regions": spatial.num_regions,
            "mean_region_area_km2": _safe(float(np.mean(region_areas))) if region_areas else 0.0,
            "max_region_area_km2": _safe(float(np.max(region_areas))) if region_areas else 0.0,
            "min_region_area_km2": _safe(float(np.min(region_areas))) if region_areas else 0.0,
            "mean_change_score": _safe(float(np.mean(region_scores))) if region_scores else 0.0,
            "max_change_score": _safe(float(np.max(region_scores))) if region_scores else 0.0,
            "change_intensity_mean": _arr_stats(intensity, valid_mask)["mean"],
            "change_intensity_max": _arr_stats(intensity, valid_mask)["max"],
            "change_intensity_std": _arr_stats(intensity, valid_mask)["std"],
        },
        "ndvi": {
            "formula": "NDVI = (NIR - Red) / (NIR + Red)",
            "t1": _arr_stats(ndvi_t1, valid_mask),
            "t2": _arr_stats(ndvi_t2, valid_mask),
            "diff": _arr_stats(ndvi_diff, valid_mask),
            "vegetation_fraction_t1": _safe(float(((ndvi_t1 > 0.3) & valid_mask).sum() / max(valid_pixels, 1) * 100), 2),
            "vegetation_fraction_t2": _safe(float(((ndvi_t2 > 0.3) & valid_mask).sum() / max(valid_pixels, 1) * 100), 2),
        },
        "ndbi": {
            "formula": "NDBI = (SWIR - NIR) / (SWIR + NIR)",
            "t1": _arr_stats(ndbi_t1, valid_mask) if ndbi_t1 is not None else _arr_stats(np.zeros_like(ndvi_t1), valid_mask),
            "t2": _arr_stats(ndbi_t2, valid_mask) if ndbi_t2 is not None else _arr_stats(np.zeros_like(ndvi_t1), valid_mask),
            "diff": _arr_stats(ndbi_t2 - ndbi_t1, valid_mask) if ndbi_t1 is not None and ndbi_t2 is not None else _arr_stats(np.zeros_like(ndvi_t1), valid_mask),
            "built_up_fraction_t1": _safe(float(((ndbi_t1 > 0.1) & valid_mask).sum() / max(valid_pixels, 1) * 100), 2) if ndbi_t1 is not None else 0.0,
            "built_up_fraction_t2": _safe(float(((ndbi_t2 > 0.1) & valid_mask).sum() / max(valid_pixels, 1) * 100), 2) if ndbi_t2 is not None else 0.0,
        },
        "savi": {
            "formula": "SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L), L=0.5",
            "t1": _arr_stats(savi_t1, valid_mask),
            "t2": _arr_stats(savi_t2, valid_mask),
            "diff": _arr_stats(savi_t2 - savi_t1, valid_mask),
        },
        "ndwi": {
            "formula": "NDWI = (Green - NIR) / (Green + NIR)",
            "t1": _arr_stats(ndwi_t1, valid_mask),
            "t2": _arr_stats(ndwi_t2, valid_mask),
            "diff": _arr_stats(ndwi_t2 - ndwi_t1, valid_mask),
        },
        "spectral": {
            "red_t1": _arr_stats(red_t1, valid_mask),
            "red_t2": _arr_stats(red_t2, valid_mask),
            "nir_t1": _arr_stats(nir_t1, valid_mask),
            "nir_t2": _arr_stats(nir_t2, valid_mask),
            "mean_absolute_spectral_difference": _safe(float(np.mean(np.abs(nir_t2 - nir_t1)[valid_mask] + np.abs(red_t2 - red_t1)[valid_mask]))),
        },
    }
