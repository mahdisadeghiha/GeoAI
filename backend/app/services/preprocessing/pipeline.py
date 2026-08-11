"""Preprocessing pipeline orchestrator."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.config import Settings, get_settings
from app.services.preprocessing.align import align_rasters
from app.services.preprocessing.crs import check_crs
from app.services.preprocessing.nodata import handle_nodata
from app.services.preprocessing.reproject import reproject_raster
from app.services.preprocessing.validate import validate_raster
from app.utils.raster import RasterData, RasterLoader


@dataclass
class PreprocessedPair:
    raster_t1: RasterData
    raster_t2: RasterData
    valid_mask: np.ndarray


class PreprocessingPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def run(self, path_t1: str | Path, path_t2: str | Path) -> PreprocessedPair:
        raster_t1 = validate_raster(path_t1)
        raster_t2 = validate_raster(path_t2)

        crs_info = check_crs(raster_t1.crs, raster_t2.crs, self.settings.target_crs)
        if crs_info["needs_reproject_a"]:
            raster_t1 = reproject_raster(raster_t1, self.settings.target_crs)
        if crs_info["needs_reproject_b"]:
            raster_t2 = reproject_raster(raster_t2, self.settings.target_crs)

        raster_t1, raster_t2 = align_rasters(raster_t1, raster_t2)
        raster_t1, mask_t1 = handle_nodata(raster_t1)
        raster_t2, mask_t2 = handle_nodata(raster_t2)
        valid_mask = mask_t1 & mask_t2

        return PreprocessedPair(raster_t1=raster_t1, raster_t2=raster_t2, valid_mask=valid_mask)

    @staticmethod
    def get_band_index(band_names: list[str] | None, name: str, default: int) -> int:
        if not band_names:
            return default
        for i, bn in enumerate(band_names):
            if bn.upper() == name.upper():
                return i
        return default
