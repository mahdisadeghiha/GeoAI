"""Raster normalization utilities."""

import numpy as np

from app.utils.raster import RasterData


def normalize_raster(raster: RasterData, method: str = "percentile") -> RasterData:
    array = raster.array.copy()
    if array.ndim == 2:
        bands = [array]
    else:
        bands = [array[i] for i in range(array.shape[0])]

    normalized = []
    for band in bands:
        valid = band[np.isfinite(band)]
        if valid.size == 0:
            normalized.append(band)
            continue
        if method == "percentile":
            lo, hi = np.percentile(valid, [2, 98])
        else:
            lo, hi = valid.min(), valid.max()
        if hi - lo < 1e-6:
            normalized.append(np.zeros_like(band))
        else:
            scaled = (band - lo) / (hi - lo)
            normalized.append(np.clip(scaled, 0, 1))

    out = normalized[0] if len(normalized) == 1 else np.stack(normalized, axis=0)
    return RasterData(
        array=out.astype(np.float32),
        transform=raster.transform,
        crs=raster.crs,
        nodata=raster.nodata,
        band_names=raster.band_names,
    )
