"""Preprocessing pipeline orchestrator."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.config import Settings, get_settings
from app.services.preprocessing.align import align_rasters
from app.services.preprocessing.crop import (
    crop_raster_to_aoi,
    raster_bounds_wgs84,
    resolve_aoi_for_imagery,
)
from app.services.preprocessing.crs import check_crs
from app.services.preprocessing.nodata import handle_nodata
from app.services.preprocessing.reproject import reproject_raster
from app.services.preprocessing.validate import validate_raster
from app.utils.raster import RasterData


@dataclass
class PreprocessedPair:
    raster_t1: RasterData
    raster_t2: RasterData
    valid_mask: np.ndarray
    aoi_bbox_wgs84: tuple[float, float, float, float] | None = None
    aoi_note: str | None = None


class PreprocessingPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def run(
        self,
        path_t1: str | Path,
        path_t2: str | Path,
        aoi_bbox_wgs84: tuple[float, float, float, float] | None = None,
        study_bbox_wgs84: tuple[float, float, float, float] | None = None,
    ) -> PreprocessedPair:
        raster_t1 = validate_raster(path_t1)
        raster_t2 = validate_raster(path_t2)

        crs_info = check_crs(raster_t1.crs, raster_t2.crs, self.settings.target_crs)
        if crs_info["needs_reproject_a"]:
            raster_t1 = reproject_raster(raster_t1, self.settings.target_crs)
        if crs_info["needs_reproject_b"]:
            raster_t2 = reproject_raster(raster_t2, self.settings.target_crs)

        raster_t1, raster_t2 = align_rasters(raster_t1, raster_t2)

        aoi_note = None
        resolved_aoi = aoi_bbox_wgs84
        if aoi_bbox_wgs84 is not None:
            imagery_bbox = raster_bounds_wgs84(raster_t1)
            resolved_aoi, aoi_note = resolve_aoi_for_imagery(
                aoi_bbox_wgs84,
                imagery_bbox,
                study_bbox_wgs84=study_bbox_wgs84,
            )
            raster_t1 = crop_raster_to_aoi(raster_t1, resolved_aoi)
            raster_t2 = crop_raster_to_aoi(raster_t2, resolved_aoi)

        raster_t1, mask_t1 = handle_nodata(raster_t1)
        raster_t2, mask_t2 = handle_nodata(raster_t2)
        valid_mask = mask_t1 & mask_t2

        # Always expose the processed imagery footprint for map overlays
        imagery_extent = raster_bounds_wgs84(raster_t1)
        if resolved_aoi is None:
            resolved_aoi = imagery_extent

        return PreprocessedPair(
            raster_t1=raster_t1,
            raster_t2=raster_t2,
            valid_mask=valid_mask,
            aoi_bbox_wgs84=resolved_aoi,
            aoi_note=aoi_note,
        )

    @staticmethod
    def get_band_index(band_names: list[str] | None, name: str, default: int) -> int:
        if not band_names:
            return default
        for i, bn in enumerate(band_names):
            if bn.upper() == name.upper():
                return i
        return default
