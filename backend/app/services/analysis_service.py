"""Full analysis pipeline orchestration."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, box
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import AnalysisRun, ChangeRegion, StudyArea
from app.services.change_detection.baseline import detect_changes_baseline
from app.services.change_detection.cva import detect_changes_cva
from app.services.metrics import build_extended_metrics
from app.services.ndvi.ndvi_service import analyze_ndvi, save_ndvi_outputs
from app.services.preprocessing.pipeline import PreprocessingPipeline
from app.services.spatial_analysis.polygonize import polygonize_changes
from app.utils.preview_png import save_change_mask_png, save_ndvi_diff_png, save_rgb_png
from app.utils.raster import RasterData, RasterLoader
from app.utils.run_store import save_run_artifacts

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    run_id: uuid.UUID
    study_area_km2: float
    changed_area_km2: float
    change_percentage: float
    vegetation_change_percentage: float
    built_up_change_percentage: float
    num_change_regions: int
    outputs: dict
    geojson: dict
    statistics: dict
    aoi_bbox_wgs84: tuple[float, float, float, float] | None = None
    aoi_note: str | None = None


class AnalysisService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.preprocessor = PreprocessingPipeline(self.settings)

    def run_analysis(
        self,
        path_t1: str | Path,
        path_t2: str | Path,
        method: str = "baseline",
        run_id: uuid.UUID | None = None,
        aoi_bbox_wgs84: tuple[float, float, float, float] | None = None,
        study_bbox_wgs84: tuple[float, float, float, float] | None = None,
        year_t1: int | None = None,
        year_t2: int | None = None,
    ) -> AnalysisResult:
        run_id = run_id or uuid.uuid4()
        output_dir = self.settings.processed_data_dir / str(run_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Starting analysis run %s", run_id)
        preprocessed = self.preprocessor.run(
            path_t1,
            path_t2,
            aoi_bbox_wgs84=aoi_bbox_wgs84,
            study_bbox_wgs84=study_bbox_wgs84,
        )
        raster_t1 = preprocessed.raster_t1
        raster_t2 = preprocessed.raster_t2
        valid_mask = preprocessed.valid_mask

        red_idx = PreprocessingPipeline.get_band_index(raster_t1.band_names, "B04", 2)
        green_idx = PreprocessingPipeline.get_band_index(raster_t1.band_names, "B03", 1)
        nir_idx = PreprocessingPipeline.get_band_index(raster_t1.band_names, "B08", 3)
        swir_idx = PreprocessingPipeline.get_band_index(raster_t1.band_names, "B11", 4)

        ndvi_result = analyze_ndvi(raster_t1, raster_t2, valid_mask, red_idx, nir_idx, self.settings)
        ndvi_paths = save_ndvi_outputs(ndvi_result, output_dir)

        if method == "cva":
            change_result = detect_changes_cva(
                raster_t1, raster_t2, valid_mask, red_idx, nir_idx, swir_idx, self.settings
            )
        else:
            change_result = detect_changes_baseline(
                raster_t1, raster_t2, valid_mask, red_idx, nir_idx, swir_idx, self.settings
            )

        change_mask_path = RasterLoader.save(change_result.change_mask, output_dir / "change_mask.tif")
        intensity_path = RasterLoader.save(change_result.change_intensity, output_dir / "change_intensity.tif")

        spatial = polygonize_changes(
            change_result.change_mask,
            change_result.change_intensity,
            valid_mask,
            self.settings.min_change_region_area_m2,
            self.settings,
        )

        geojson_path = output_dir / "change_regions.geojson"
        geojson_path.write_text(json.dumps(spatial.geojson), encoding="utf-8")

        rgb_t1 = self._save_rgb(raster_t1, output_dir / "rgb_t1.tif")
        rgb_t2 = self._save_rgb(raster_t2, output_dir / "rgb_t2.tif")

        # Leaflet ImageOverlay needs PNG (browsers cannot render GeoTIFF)
        rgb_arr_t1 = raster_t1.array[:3] if raster_t1.array.ndim == 3 else raster_t1.array
        rgb_arr_t2 = raster_t2.array[:3] if raster_t2.array.ndim == 3 else raster_t2.array
        # Prefer true-color order B04,B03,B02 when available
        if raster_t1.array.shape[0] >= 3:
            rgb_arr_t1 = np.stack(
                [
                    raster_t1.array[red_idx],
                    raster_t1.array[green_idx],
                    raster_t1.array[PreprocessingPipeline.get_band_index(raster_t1.band_names, "B02", 0)],
                ]
            )
            rgb_arr_t2 = np.stack(
                [
                    raster_t2.array[red_idx],
                    raster_t2.array[green_idx],
                    raster_t2.array[PreprocessingPipeline.get_band_index(raster_t2.band_names, "B02", 0)],
                ]
            )

        rgb_t1_png = save_rgb_png(rgb_arr_t1, output_dir / "rgb_t1.png")
        rgb_t2_png = save_rgb_png(rgb_arr_t2, output_dir / "rgb_t2.png")
        change_mask_png = save_change_mask_png(change_result.change_mask.array, output_dir / "change_mask.png")
        ndvi_diff_png = save_ndvi_diff_png(ndvi_result.ndvi_diff.array, output_dir / "ndvi_diff.png")

        outputs = {
            "change_mask": str(change_mask_path),
            "change_intensity": str(intensity_path),
            "ndvi_t1": ndvi_paths["ndvi_t1"],
            "ndvi_t2": ndvi_paths["ndvi_t2"],
            "ndvi_diff": ndvi_paths["ndvi_diff"],
            "rgb_t1": str(rgb_t1),
            "rgb_t2": str(rgb_t2),
            "change_geojson": str(geojson_path),
            "method": change_result.method,
            # Browser-ready map overlays
            "rgb_t1_png": str(rgb_t1_png),
            "rgb_t2_png": str(rgb_t2_png),
            "change_mask_png": str(change_mask_png),
            "ndvi_diff_png": str(ndvi_diff_png),
        }

        metrics = build_extended_metrics(
            raster_t1=raster_t1,
            raster_t2=raster_t2,
            valid_mask=valid_mask,
            change_mask=change_result.change_mask.array,
            intensity=change_result.change_intensity.array,
            ndvi_t1=ndvi_result.ndvi_t1.array,
            ndvi_t2=ndvi_result.ndvi_t2.array,
            spatial=spatial,
            red_idx=red_idx,
            nir_idx=nir_idx,
            swir_idx=swir_idx,
            green_idx=green_idx,
            method=change_result.method,
            year_t1=year_t1,
            year_t2=year_t2,
            eps=self.settings.ndvi_eps,
        )

        statistics = {
            "study_area_km2": metrics["extent"]["study_area_km2"],
            "changed_area_km2": metrics["extent"]["changed_area_km2"],
            "change_percentage": metrics["extent"]["change_percentage"],
            "vegetation_change_percentage": metrics["change_summary"]["vegetation_change_percentage"],
            "built_up_change_percentage": metrics["change_summary"]["built_up_change_percentage"],
            "num_change_regions": metrics["change_summary"]["num_change_regions"],
            "ndvi_t1_mean": metrics["ndvi"]["t1"]["mean"],
            "ndvi_t2_mean": metrics["ndvi"]["t2"]["mean"],
            "metrics": metrics,
        }

        save_run_artifacts(run_id, statistics, outputs, spatial.geojson)

        return AnalysisResult(
            run_id=run_id,
            study_area_km2=statistics["study_area_km2"],
            changed_area_km2=statistics["changed_area_km2"],
            change_percentage=statistics["change_percentage"],
            vegetation_change_percentage=statistics["vegetation_change_percentage"],
            built_up_change_percentage=statistics["built_up_change_percentage"],
            num_change_regions=statistics["num_change_regions"],
            outputs=outputs,
            geojson=spatial.geojson,
            statistics=statistics,
            aoi_bbox_wgs84=preprocessed.aoi_bbox_wgs84,
            aoi_note=preprocessed.aoi_note,
        )

    def _save_rgb(self, raster: RasterData, path: Path) -> Path:
        if raster.array.shape[0] >= 3:
            rgb = raster.array[:3]
        else:
            band = raster.array if raster.array.ndim == 2 else raster.array[0]
            rgb = np.stack([band, band, band])
        rgb_raster = RasterData(rgb, raster.transform, raster.crs, band_names=["R", "G", "B"])
        return RasterLoader.save(rgb_raster, path)

    def persist_run(self, db: Session, result: AnalysisResult, path_t1: str, path_t2: str) -> AnalysisRun:
        west, south, east, north = self.settings.study_area_bbox
        study_area = db.query(StudyArea).filter(StudyArea.name == self.settings.study_area_name).first()
        if not study_area:
            study_area = StudyArea(
                name=self.settings.study_area_name,
                bbox=from_shape(box(west, south, east, north), srid=4326),
                crs=self.settings.target_crs,
            )
            db.add(study_area)
            db.flush()

        run = AnalysisRun(
            id=result.run_id,
            study_area_id=study_area.id,
            image_t1_path=path_t1,
            image_t2_path=path_t2,
            status="completed",
            statistics=result.statistics,
            outputs=result.outputs,
            created_at=datetime.utcnow(),
        )
        db.add(run)

        for region in result.geojson.get("features", []):
            props = region["properties"]
            from shapely.geometry import MultiPolygon, shape as shapely_shape

            geom = shapely_shape(region["geometry"])
            if geom.geom_type == "Polygon":
                geom = MultiPolygon([geom])
            centroid = geom.centroid
            db.add(
                ChangeRegion(
                    analysis_run_id=result.run_id,
                    geom=from_shape(geom, srid=4326),
                    area_km2=props["area_km2"],
                    centroid=from_shape(Point(centroid.x, centroid.y), srid=4326),
                    bbox=from_shape(box(*geom.bounds), srid=4326),
                    change_score=props["change_score"],
                )
            )

        db.commit()
        db.refresh(run)
        return run

    def get_latest_run(self, db: Session) -> AnalysisRun | None:
        return db.query(AnalysisRun).filter(AnalysisRun.status == "completed").order_by(AnalysisRun.created_at.desc()).first()

    def get_run(self, db: Session, run_id: uuid.UUID) -> AnalysisRun | None:
        return db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
