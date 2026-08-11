"""Raster alignment utilities."""

import numpy as np
from rasterio.transform import from_bounds

from app.utils.raster import RasterData, reproject_array


def _union_bounds(a: tuple[float, float, float, float], b: tuple[float, float, float, float]):
    return (
        min(a[0], b[0]),
        min(a[1], b[1]),
        max(a[2], b[2]),
        max(a[3], b[3]),
    )


def _intersection_bounds(a: tuple[float, float, float, float], b: tuple[float, float, float, float]):
    west = max(a[0], b[0])
    south = max(a[1], b[1])
    east = min(a[2], b[2])
    north = min(a[3], b[3])
    if west >= east or south >= north:
        raise ValueError("Rasters do not overlap")
    return west, south, east, north


def align_rasters(raster_a: RasterData, raster_b: RasterData) -> tuple[RasterData, RasterData]:
    """Align two rasters to a common grid using the finer resolution."""
    res_x = min(abs(raster_a.transform.a), abs(raster_b.transform.a))
    res_y = min(abs(raster_a.transform.e), abs(raster_b.transform.e))
    # Guard against degenerate transforms
    res_x = res_x if res_x > 0 else abs(raster_a.transform.a) or 1.0
    res_y = res_y if res_y > 0 else abs(raster_a.transform.e) or res_x

    bounds = _intersection_bounds(raster_a.bounds, raster_b.bounds)
    width = max(1, int(round((bounds[2] - bounds[0]) / res_x)))
    height = max(1, int(round((bounds[3] - bounds[1]) / res_y)))
    transform = from_bounds(*bounds, width, height)

    def _warp(r: RasterData) -> RasterData:
        array, out_transform = reproject_array(
            r.array,
            r.transform,
            r.crs,
            r.crs,
            dst_transform=transform,
            dst_width=width,
            dst_height=height,
        )
        return RasterData(
            array=array,
            transform=out_transform,
            crs=r.crs,
            nodata=r.nodata,
            band_names=r.band_names,
        )

    return _warp(raster_a), _warp(raster_b)


def crop_to_common_extent(raster_a: RasterData, raster_b: RasterData) -> tuple[RasterData, RasterData]:
    """Crop both rasters to their intersection extent."""
    return align_rasters(raster_a, raster_b)
