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
from app.schemas import AnalysisOutputs, AnalysisResponse, GeoJSONResponse
from app.services.analysis_service import AnalysisService
from app.utils.run_store import load_geojson, load_statistics

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


def _outputs_to_urls(run_id: uuid.UUID, outputs: dict) -> AnalysisOutputs:
    return AnalysisOutputs(
        change_mask=f"/api/rasters/{run_id}/change_mask.tif",
        change_intensity=f"/api/rasters/{run_id}/change_intensity.tif",
        ndvi_t1=f"/api/rasters/{run_id}/ndvi_t1.tif",
        ndvi_t2=f"/api/rasters/{run_id}/ndvi_t2.tif",
        ndvi_diff=f"/api/rasters/{run_id}/ndvi_diff.tif",
        rgb_t1=f"/api/rasters/{run_id}/rgb_t1.tif",
        rgb_t2=f"/api/rasters/{run_id}/rgb_t2.tif",
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
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    settings = get_settings()
    service = AnalysisService(settings)
    run_id = uuid.uuid4()
    run_dir = settings.processed_data_dir / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    if use_samples or image_t1 is None or image_t2 is None:
        path_t1 = settings.samples_data_dir / "sample_t1.tif"
        path_t2 = settings.samples_data_dir / "sample_t2.tif"
        if not path_t1.exists() or not path_t2.exists():
            raise HTTPException(
                status_code=400,
                detail="Sample rasters not found. Run scripts/generate_test_rasters.py first.",
            )
    else:
        path_t1 = run_dir / "input_t1.tif"
        path_t2 = run_dir / "input_t2.tif"
        with path_t1.open("wb") as f:
            shutil.copyfileobj(image_t1.file, f)
        with path_t2.open("wb") as f:
            shutil.copyfileobj(image_t2.file, f)

    try:
        result = service.run_analysis(path_t1, path_t2, method=method, run_id=run_id)
        try:
            service.persist_run(db, result, str(path_t1), str(path_t2))
        except Exception:
            db.rollback()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AnalysisResponse(
        run_id=result.run_id,
        status="completed",
        study_area_km2=result.study_area_km2,
        changed_area_km2=result.changed_area_km2,
        change_percentage=result.change_percentage,
        vegetation_change_percentage=result.vegetation_change_percentage,
        built_up_change_percentage=result.built_up_change_percentage,
        num_change_regions=result.num_change_regions,
        outputs=_outputs_to_urls(result.run_id, result.outputs),
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
    except SQLAlchemyError as exc:
        logger.warning("Database unavailable for changes lookup: %s", exc)
        db.rollback()

    geojson = load_geojson(run_id)
    if geojson:
        return GeoJSONResponse(**geojson)

    raise HTTPException(status_code=404, detail="No change regions found")
