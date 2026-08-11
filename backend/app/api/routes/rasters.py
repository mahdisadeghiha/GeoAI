"""Static raster file serving."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings

router = APIRouter(tags=["rasters"])


@router.get("/rasters/{run_id}/{filename}")
def get_raster(run_id: uuid.UUID, filename: str) -> FileResponse:
    settings = get_settings()
    path = settings.processed_data_dir / str(run_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Raster not found: {filename}")
    return FileResponse(path, media_type="image/tiff", filename=filename)
