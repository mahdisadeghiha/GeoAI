"""NoData handling utilities."""

import numpy as np

from app.utils.raster import RasterData


def handle_nodata(raster: RasterData, fill_value: float = 0.0) -> tuple[RasterData, np.ndarray]:
    """Replace nodata/invalid values and return a valid pixel mask."""
    array = raster.array.copy()
    mask = np.ones(array.shape[-2:], dtype=bool)

    if raster.nodata is not None:
        if array.ndim == 2:
            invalid = ~np.isfinite(array) | (array == raster.nodata)
            array[invalid] = fill_value
            mask = ~invalid
        else:
            invalid = ~np.isfinite(array).all(axis=0)
            for i in range(array.shape[0]):
                band_invalid = array[i] == raster.nodata
                array[i][band_invalid] = fill_value
                invalid |= band_invalid
            mask = ~invalid
    else:
        if array.ndim == 2:
            invalid = ~np.isfinite(array)
        else:
            invalid = ~np.isfinite(array).all(axis=0)
        mask = ~invalid

    cleaned = RasterData(
        array=array,
        transform=raster.transform,
        crs=raster.crs,
        nodata=raster.nodata,
        band_names=raster.band_names,
    )
    return cleaned, mask
