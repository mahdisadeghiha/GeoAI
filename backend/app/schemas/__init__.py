"""Pydantic schemas for API request and response models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "0.1.0"


class StudyAreaResponse(BaseModel):
    id: str | None = None
    name: str
    bbox: list[float]
    crs: str
    description: str
    has_sample_data: bool = False
    imagery_bbox: list[float] | None = None


class StudyAreasListResponse(BaseModel):
    areas: list[StudyAreaResponse]
    available_years: list[int]


class AnalysisStatistics(BaseModel):
    study_area_km2: float
    changed_area_km2: float
    change_percentage: float
    vegetation_change_percentage: float
    built_up_change_percentage: float
    num_change_regions: int


class AnalysisOutputs(BaseModel):
    change_mask: str | None = None
    change_intensity: str | None = None
    ndvi_t1: str | None = None
    ndvi_t2: str | None = None
    ndvi_diff: str | None = None
    rgb_t1: str | None = None
    rgb_t2: str | None = None
    change_geojson: str | None = None


class AnalysisResponse(BaseModel):
    run_id: UUID
    status: str
    study_area_id: str | None = None
    study_area_name: str | None = None
    year_t1: int | None = None
    year_t2: int | None = None
    aoi_bbox: list[float] | None = None
    study_area_km2: float
    changed_area_km2: float
    change_percentage: float
    vegetation_change_percentage: float
    built_up_change_percentage: float
    num_change_regions: int
    outputs: AnalysisOutputs
    metrics: dict[str, Any] | None = None
    change_geojson: dict[str, Any] | None = None
    note: str | None = None
    created_at: datetime | None = None


class NDVIResponse(BaseModel):
    run_id: UUID | None = None
    ndvi_t1_mean: float | None = None
    ndvi_t2_mean: float | None = None
    ndvi_diff_mean: float | None = None
    vegetation_change_percentage: float | None = None
    raster_urls: dict[str, str | None] = Field(default_factory=dict)


class ChangeFeatureProperties(BaseModel):
    region_id: int
    area_km2: float
    change_score: float
    centroid_lon: float
    centroid_lat: float


class GeoJSONResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict[str, Any]]
