"""Reprojection and resampling utilities."""

from rasterio.enums import Resampling

from app.utils.raster import RasterData, reproject_array


def reproject_raster(raster: RasterData, target_crs: str) -> RasterData:
    if raster.crs == target_crs:
        return raster
    array, transform = reproject_array(
        raster.array,
        raster.transform,
        raster.crs,
        target_crs,
        resampling=Resampling.bilinear,
    )
    return RasterData(
        array=array,
        transform=transform,
        crs=target_crs,
        nodata=raster.nodata,
        band_names=raster.band_names,
    )


def resample_raster(raster: RasterData, target_transform, target_width: int, target_height: int) -> RasterData:
    array, transform = reproject_array(
        raster.array,
        raster.transform,
        raster.crs,
        raster.crs,
        dst_transform=target_transform,
        dst_width=target_width,
        dst_height=target_height,
        resampling=Resampling.bilinear,
    )
    return RasterData(
        array=array,
        transform=transform,
        crs=raster.crs,
        nodata=raster.nodata,
        band_names=raster.band_names,
    )
