"""Static raster / preview file serving."""

import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings

router = APIRouter(tags=["rasters"])

_MEDIA = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".json": "application/json",
    ".geojson": "application/geo+json",
}


@router.get("/rasters/{run_id}/{filename}")
def get_raster(run_id: uuid.UUID, filename: str) -> FileResponse:
    settings = get_settings()
    # Prevent path traversal
    safe_name = Path(filename).name
    path = settings.processed_data_dir / str(run_id) / safe_name
    if not path.exists():
        # Fall back: if .png missing, try .tif (older runs)
        if safe_name.endswith(".png"):
            alt = path.with_suffix(".tif")
            if alt.exists():
                path = alt
                safe_name = alt.name
            else:
                raise HTTPException(status_code=404, detail=f"Raster not found: {filename}")
        else:
            raise HTTPException(status_code=404, detail=f"Raster not found: {filename}")
    media = _MEDIA.get(path.suffix.lower()) or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=safe_name)
