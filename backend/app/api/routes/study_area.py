"""Study area metadata endpoints."""

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.study_areas import AVAILABLE_YEARS, get_study_area, list_study_areas as _list_study_areas
from app.schemas import StudyAreaResponse, StudyAreasListResponse

router = APIRouter(tags=["study-area"])


@router.get("/study-areas", response_model=StudyAreasListResponse)
def list_study_areas() -> StudyAreasListResponse:
    return StudyAreasListResponse(
        areas=[StudyAreaResponse(**area) for area in _list_study_areas()],
        available_years=AVAILABLE_YEARS,
    )


@router.get("/study-area", response_model=StudyAreaResponse)
def get_default_study_area(area_id: str = "muscat") -> StudyAreaResponse:
    area = get_study_area(area_id)
    if area is None:
        settings = get_settings()
        return StudyAreaResponse(
            id="muscat",
            name=settings.study_area_name,
            bbox=list(settings.study_area_bbox),
            crs=settings.target_crs,
            description=(
                "Urban change detection study area over Muscat, Oman. "
                "Sentinel-2 L2A dry-season composites for 2020 and 2025."
            ),
            has_sample_data=True,
        )
    return StudyAreaResponse(**area)


@router.get("/study-areas/{area_id}", response_model=StudyAreaResponse)
def get_study_area_by_id(area_id: str) -> StudyAreaResponse:
    area = get_study_area(area_id)
    if area is None:
        raise HTTPException(status_code=404, detail=f"Unknown study area: {area_id}")
    return StudyAreaResponse(**area)
