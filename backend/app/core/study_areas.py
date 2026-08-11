"""Predefined study areas covering Oman for the GeoAI dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import get_settings

# Imagery footprints match download script AOIs
STUDY_AREAS: list[dict[str, Any]] = [
    {
        "id": "oman",
        "name": "Oman (National)",
        "bbox": [52.0, 16.6, 59.9, 26.5],
        "crs": "EPSG:4326",
        "description": "Nationwide Oman footprint for regional change screening (~500 m Sentinel-2 composites).",
        "has_sample_data": False,
        "imagery_bbox": [52.0, 16.6, 59.9, 26.5],
    },
    {
        "id": "muscat",
        "name": "Muscat, Oman",
        "bbox": [58.20, 23.45, 58.75, 23.75],
        "crs": "EPSG:32640",
        "description": "Muscat capital region — primary urban growth corridor.",
        "has_sample_data": True,
        "imagery_bbox": [58.20, 23.45, 58.75, 23.75],
    },
    {
        "id": "sohar",
        "name": "Sohar, Oman",
        "bbox": [56.55, 24.20, 56.95, 24.55],
        "crs": "EPSG:32640",
        "description": "Sohar industrial port and northern Batinah coast.",
        "has_sample_data": False,
        "imagery_bbox": [56.55, 24.20, 56.95, 24.55],
    },
    {
        "id": "salalah",
        "name": "Salalah, Oman",
        "bbox": [53.90, 16.90, 54.30, 17.15],
        "crs": "EPSG:32640",
        "description": "Salalah coastal plain in Dhofar governorate.",
        "has_sample_data": False,
        "imagery_bbox": [53.90, 16.90, 54.30, 17.15],
    },
    {
        "id": "nizwa",
        "name": "Nizwa, Oman",
        "bbox": [57.40, 22.85, 57.70, 23.05],
        "crs": "EPSG:32640",
        "description": "Nizwa and interior Ad Dakhiliyah urban fringe.",
        "has_sample_data": False,
        "imagery_bbox": [57.40, 22.85, 57.70, 23.05],
    },
    {
        "id": "duqm",
        "name": "Duqm, Oman",
        "bbox": [57.45, 19.50, 57.85, 19.85],
        "crs": "EPSG:32640",
        "description": "Duqm special economic zone and port development.",
        "has_sample_data": False,
        "imagery_bbox": [57.45, 19.50, 57.85, 19.85],
    },
    {
        "id": "sur",
        "name": "Sur, Oman",
        "bbox": [59.40, 22.45, 59.65, 22.70],
        "crs": "EPSG:32640",
        "description": "Sur coastal city in Ash Sharqiyah South.",
        "has_sample_data": False,
        "imagery_bbox": [59.40, 22.45, 59.65, 22.70],
    },
]


AVAILABLE_YEARS = list(range(2018, 2026))


def _has_local_pair(area_id: str) -> bool:
    settings = get_settings()
    for year_a in AVAILABLE_YEARS:
        for year_b in AVAILABLE_YEARS:
            if year_b <= year_a:
                continue
            t1 = settings.raw_data_dir / f"{area_id}_{year_a}.tif"
            t2 = settings.raw_data_dir / f"{area_id}_{year_b}.tif"
            if t1.exists() and t2.exists():
                return True
            s1 = settings.samples_data_dir / f"{area_id}_{year_a}.tif"
            s2 = settings.samples_data_dir / f"{area_id}_{year_b}.tif"
            if s1.exists() and s2.exists():
                return True
    # Legacy Muscat samples
    if area_id == "muscat":
        samples = settings.samples_data_dir
        return (samples / "sample_t1.tif").exists() and (samples / "sample_t2.tif").exists()
    return False


def get_study_area(area_id: str) -> dict[str, Any] | None:
    for area in STUDY_AREAS:
        if area["id"] == area_id:
            enriched = dict(area)
            enriched["has_sample_data"] = bool(area.get("has_sample_data")) or _has_local_pair(area_id)
            return enriched
    return None


def list_study_areas() -> list[dict[str, Any]]:
    return [get_study_area(area["id"]) for area in STUDY_AREAS]  # type: ignore[misc]
