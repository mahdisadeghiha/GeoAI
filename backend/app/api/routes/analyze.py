"""Analysis and statistics endpoints."""

import json
import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.study_areas import get_study_area
from app.schemas import AnalysisOutputs, AnalysisResponse, GeoJSONResponse
from app.services.analysis_service import AnalysisService
from app.utils.raster_catalog import resolve_raster_pair
from app.utils.run_store import load_geojson, load_statistics, save_run_artifacts

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


def _outputs_to_urls(run_id: uuid.UUID, outputs: dict) -> AnalysisOutputs:
    """Prefer PNG overlays for the map; keep GeoTIFF URLs available for download."""
    return AnalysisOutputs(
        change_mask=f"/api/rasters/{run_id}/change_mask.png",
        change_intensity=f"/api/rasters/{run_id}/change_intensity.tif",
        ndvi_t1=f"/api/rasters/{run_id}/ndvi_t1.tif",
        ndvi_t2=f"/api/rasters/{run_id}/ndvi_t2.tif",
        ndvi_diff=f"/api/rasters/{run_id}/ndvi_diff.png",
        rgb_t1=f"/api/rasters/{run_id}/rgb_t1.png",
        rgb_t2=f"/api/rasters/{run_id}/rgb_t2.png",
        change_geojson=f"/api/changes?run_id={run_id}",
    )


def _statistics_from_db(db: Session, run_id: uuid.UUID | None) -> dict | None:
    service = AnalysisService()
    try:
        run = service.get_run(db, run_id) if run_id else service.get_latest_run(db)
        if run and run.statistics:
            return run.statistics
    except SQLAlchemyError as exc:
        logger.warning("Database unavailable for statistics lookup: %s", exc)
        db.rollback()
    return None


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    image_t1: UploadFile | None = File(None),
    image_t2: UploadFile | None = File(None),
    use_samples: bool = Form(True),
    method: str = Form("baseline"),
    study_area_id: str = Form("muscat"),
    year_t1: int = Form(2020),
    year_t2: int = Form(2025),
    bbox_west: float | None = Form(None),
    bbox_south: float | None = Form(None),
    bbox_east: float | None = Form(None),
    bbox_north: float | None = Form(None),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if year_t2 <= year_t1:
        raise HTTPException(status_code=400, detail="year_t2 must be greater than year_t1")

    area = get_study_area(study_area_id)
    if area is None:
        raise HTTPException(status_code=400, detail=f"Unknown study area: {study_area_id}")

    aoi_bbox = None
    bbox_values = [bbox_west, bbox_south, bbox_east, bbox_north]
    if any(v is not None for v in bbox_values):
        if any(v is None for v in bbox_values):
            raise HTTPException(status_code=400, detail="Provide all four AOI bbox values or none")
        aoi_bbox = (bbox_west, bbox_south, bbox_east, bbox_north)  # type: ignore[assignment]
        if aoi_bbox[2] <= aoi_bbox[0] or aoi_bbox[3] <= aoi_bbox[1]:
            raise HTTPException(status_code=400, detail="Invalid AOI bbox")

    settings = get_settings()
    service = AnalysisService(settings)
    run_id = uuid.uuid4()
    run_dir = settings.processed_data_dir / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    note = None
    if use_samples or image_t1 is None or image_t2 is None:
        local_pair = resolve_raster_pair(study_area_id, year_t1, year_t2, settings)
        if local_pair is not None:
            path_t1, path_t2 = local_pair
            note = (
                f"Using local composites for {area['name']} "
                f"({year_t1} → {year_t2}): {path_t1.name} / {path_t2.name}."
            )
        else:
            path_t1 = settings.samples_data_dir / "sample_t1.tif"
            path_t2 = settings.samples_data_dir / "sample_t2.tif"
            if not path_t1.exists() or not path_t2.exists():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No rasters for {study_area_id} {year_t1}/{year_t2}. "
                        "Run scripts/download_oman.py or scripts/generate_test_rasters.py."
                    ),
                )
            note = (
                f"No local Sentinel-2 rasters for {area['name']} ({year_t1}/{year_t2}) yet. "
                "Analysis ran on Muscat sample rasters; map extent uses the selected study area. "
                "Download via: python scripts/download_oman.py "
                f"--regions {study_area_id} --years {year_t1} {year_t2}"
            )
    else:
        path_t1 = run_dir / "input_t1.tif"
        path_t2 = run_dir / "input_t2.tif"
        with path_t1.open("wb") as f:
            shutil.copyfileobj(image_t1.file, f)
        with path_t2.open("wb") as f:
            shutil.copyfileobj(image_t2.file, f)
        note = f"Analysis for {area['name']} ({year_t1} → {year_t2}) using uploaded GeoTIFFs."

    if aoi_bbox is not None:
        note = (note or "") + f" AOI crop applied: {[round(v, 5) for v in aoi_bbox]}."

    try:
        result = service.run_analysis(
            path_t1,
            path_t2,
            method=method,
            run_id=run_id,
            aoi_bbox_wgs84=aoi_bbox,
            study_bbox_wgs84=tuple(area["bbox"]),
            year_t1=year_t1,
            year_t2=year_t2,
        )
        resolved_aoi = result.aoi_bbox_wgs84
        if result.aoi_note:
            note = (note or "") + " " + result.aoi_note
        result.statistics.update(
            {
                "study_area_id": study_area_id,
                "study_area_name": area["name"],
                "year_t1": year_t1,
                "year_t2": year_t2,
                "aoi_bbox": list(resolved_aoi) if resolved_aoi else None,
            }
        )
        save_run_artifacts(result.run_id, result.statistics, result.outputs, result.geojson)
        try:
            service.persist_run(db, result, str(path_t1), str(path_t2))
        except Exception as persist_exc:
            logger.warning("Skipping PostGIS persistence: %s", persist_exc)
            try:
                db.rollback()
            except Exception:
                pass
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(exc) or exc.__class__.__name__) from exc

    return AnalysisResponse(
        run_id=result.run_id,
        status="completed",
        study_area_id=study_area_id,
        study_area_name=area["name"],
        year_t1=year_t1,
        year_t2=year_t2,
        aoi_bbox=list(result.aoi_bbox_wgs84) if result.aoi_bbox_wgs84 else None,
        study_area_km2=result.study_area_km2,
        changed_area_km2=result.changed_area_km2,
        change_percentage=result.change_percentage,
        vegetation_change_percentage=result.vegetation_change_percentage,
        built_up_change_percentage=result.built_up_change_percentage,
        num_change_regions=result.num_change_regions,
        outputs=_outputs_to_urls(result.run_id, result.outputs),
        metrics=result.statistics.get("metrics"),
        change_geojson=result.geojson,
        note=note,
    )


@router.get("/statistics")
def get_statistics(run_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> dict:
    stats = _statistics_from_db(db, run_id)
    if stats:
        return stats

    stats = load_statistics(run_id)
    if stats:
        return stats

    raise HTTPException(status_code=404, detail="No analysis statistics found")


@router.get("/changes", response_model=GeoJSONResponse)
def get_changes(run_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> GeoJSONResponse:
    settings = get_settings()
    service = AnalysisService()

    try:
        run = service.get_run(db, run_id) if run_id else service.get_latest_run(db)
        if run and run.outputs and run.outputs.get("change_geojson"):
            geojson_path = Path(run.outputs["change_geojson"])
            if geojson_path.exists():
                return GeoJSONResponse(**json.loads(geojson_path.read_text(encoding="utf-8")))

        if run:
            geojson_path = settings.processed_data_dir / str(run.id) / "change_regions.geojson"
            if geojson_path.exists():
                return GeoJSONResponse(**json.loads(geojson_path.read_text(encoding="utf-8")))
    except Exception as exc:
        logger.warning("Database unavailable for changes lookup: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass

    geojson = load_geojson(run_id)
    if geojson:
        return GeoJSONResponse(**geojson)

    raise HTTPException(status_code=404, detail="No change regions found")
