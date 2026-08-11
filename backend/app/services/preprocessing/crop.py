"""Crop rasters to a user-selected AOI bounding box."""

from __future__ import annotations

import numpy as np
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds

from app.utils.raster import RasterData, reproject_array


def normalize_bbox(bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    west, south, east, north = bbox
    return (min(west, east), min(south, north), max(west, east), max(south, north))


def raster_bounds_wgs84(raster: RasterData) -> tuple[float, float, float, float]:
    return transform_bounds(raster.crs, "EPSG:4326", *raster.bounds, densify_pts=21)


def intersect_bboxes(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float] | None:
    west = max(a[0], b[0])
    south = max(a[1], b[1])
    east = min(a[2], b[2])
    north = min(a[3], b[3])
    if west >= east or south >= north:
        return None
    return (west, south, east, north)


def map_bbox_between_areas(
    aoi: tuple[float, float, float, float],
    from_bbox: tuple[float, float, float, float],
    to_bbox: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Map an AOI drawn in one study-area frame into another imagery frame."""
    aoi = normalize_bbox(aoi)
    from_bbox = normalize_bbox(from_bbox)
    to_bbox = normalize_bbox(to_bbox)

    fw, fs, fe, fn = from_bbox
    tw, ts, te, tn = to_bbox
    width = max(fe - fw, 1e-12)
    height = max(fn - fs, 1e-12)

    x0 = (aoi[0] - fw) / width
    y0 = (aoi[1] - fs) / height
    x1 = (aoi[2] - fw) / width
    y1 = (aoi[3] - fs) / height

    x0, x1 = sorted((max(0.0, min(1.0, x0)), max(0.0, min(1.0, x1))))
    y0, y1 = sorted((max(0.0, min(1.0, y0)), max(0.0, min(1.0, y1))))
    if x1 - x0 < 0.02:
        x1 = min(1.0, x0 + 0.02)
    if y1 - y0 < 0.02:
        y1 = min(1.0, y0 + 0.02)

    return (
        tw + x0 * (te - tw),
        ts + y0 * (tn - ts),
        tw + x1 * (te - tw),
        ts + y1 * (tn - ts),
    )


def resolve_aoi_for_imagery(
    aoi_bbox_wgs84: tuple[float, float, float, float],
    imagery_bbox_wgs84: tuple[float, float, float, float],
    study_bbox_wgs84: tuple[float, float, float, float] | None = None,
) -> tuple[tuple[float, float, float, float], str | None]:
    """
    Ensure AOI intersects imagery.

    If the user drew outside imagery (e.g. another Oman city while using Muscat
    sample rasters), remap the AOI relatively from the study-area frame into the
    imagery frame.
    """
    aoi = normalize_bbox(aoi_bbox_wgs84)
    imagery = normalize_bbox(imagery_bbox_wgs84)
    intersection = intersect_bboxes(aoi, imagery)
    if intersection is not None:
        return intersection, None

    if study_bbox_wgs84 is not None:
        mapped = map_bbox_between_areas(aoi, study_bbox_wgs84, imagery)
        mapped_intersection = intersect_bboxes(mapped, imagery)
        if mapped_intersection is not None:
            return mapped_intersection, (
                "AOI was outside available imagery and was remapped into the sample "
                f"imagery footprint {[round(v, 4) for v in imagery]}."
            )

    raise ValueError(
        "Selected AOI does not intersect the available imagery. "
        f"Draw inside {[round(v, 4) for v in imagery]} (WGS84 west,south,east,north)."
    )


def crop_raster_to_aoi(
    raster: RasterData,
    aoi_bbox_wgs84: tuple[float, float, float, float],
) -> RasterData:
    """Crop a raster to an AOI already resolved in WGS84 (west, south, east, north)."""
    west, south, east, north = normalize_bbox(aoi_bbox_wgs84)
    if east <= west or north <= south:
        raise ValueError("AOI bbox is invalid")

    aoi_in_raster_crs = transform_bounds("EPSG:4326", raster.crs, west, south, east, north, densify_pts=21)
    aoi_west, aoi_south, aoi_east, aoi_north = aoi_in_raster_crs

    raster_west, raster_south, raster_east, raster_north = raster.bounds
    crop_west = max(aoi_west, raster_west)
    crop_south = max(aoi_south, raster_south)
    crop_east = min(aoi_east, raster_east)
    crop_north = min(aoi_north, raster_north)

    if crop_west >= crop_east or crop_south >= crop_north:
        imagery_wgs84 = raster_bounds_wgs84(raster)
        raise ValueError(
            "Selected AOI does not intersect the available imagery. "
            f"Imagery footprint (WGS84): {[round(v, 4) for v in imagery_wgs84]}"
        )

    res_x = abs(raster.transform.a)
    res_y = abs(raster.transform.e)
    width = max(1, int(round((crop_east - crop_west) / res_x)))
    height = max(1, int(round((crop_north - crop_south) / res_y)))
    dst_transform = from_bounds(crop_west, crop_south, crop_east, crop_north, width, height)

    array, out_transform = reproject_array(
        raster.array,
        raster.transform,
        raster.crs,
        raster.crs,
        dst_transform=dst_transform,
        dst_width=width,
        dst_height=height,
    )
    return RasterData(
        array=array.astype(np.float32),
        transform=out_transform,
        crs=raster.crs,
        nodata=raster.nodata,
        band_names=raster.band_names,
    )
