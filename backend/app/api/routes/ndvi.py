"""NDVI endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import NDVIResponse
from app.services.analysis_service import AnalysisService
from app.utils.run_store import load_statistics, resolve_run_id

router = APIRouter(tags=["ndvi"])


@router.get("/ndvi", response_model=NDVIResponse)
def get_ndvi(run_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> NDVIResponse:
    stats = None
    rid = run_id

    service = AnalysisService()
    try:
        run = service.get_run(db, run_id) if run_id else service.get_latest_run(db)
        if run and run.statistics:
            stats = run.statistics
            rid = run.id
    except SQLAlchemyError:
        db.rollback()

    if not stats:
        stats = load_statistics(run_id)
        rid = run_id or resolve_run_id()

    if not stats:
        raise HTTPException(status_code=404, detail="No NDVI results found")

    return NDVIResponse(
        run_id=rid,
        ndvi_t1_mean=stats.get("ndvi_t1_mean"),
        ndvi_t2_mean=stats.get("ndvi_t2_mean"),
        ndvi_diff_mean=round(stats.get("ndvi_t2_mean", 0) - stats.get("ndvi_t1_mean", 0), 4),
        vegetation_change_percentage=stats.get("vegetation_change_percentage"),
        raster_urls={
            "ndvi_t1": f"/api/rasters/{rid}/ndvi_t1.tif",
            "ndvi_t2": f"/api/rasters/{rid}/ndvi_t2.tif",
            "ndvi_diff": f"/api/rasters/{rid}/ndvi_diff.tif",
        },
    )
