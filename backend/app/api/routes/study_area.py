"""Study area metadata endpoint."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas import StudyAreaResponse

router = APIRouter(tags=["study-area"])


@router.get("/study-area", response_model=StudyAreaResponse)
def get_study_area() -> StudyAreaResponse:
    settings = get_settings()
    return StudyAreaResponse(
        name=settings.study_area_name,
        bbox=list(settings.study_area_bbox),
        crs=settings.target_crs,
        description=(
            "Urban change detection study area over Muscat, Oman. "
            "Sentinel-2 L2A dry-season composites for 2020 and 2025."
        ),
    )
