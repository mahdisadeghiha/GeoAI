"""Resolve local GeoTIFF paths for study areas and years."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, get_settings


def _candidate_paths(settings: Settings, area_id: str, year: int) -> list[Path]:
    raw = settings.raw_data_dir
    samples = settings.samples_data_dir
    return [
        raw / f"{area_id}_{year}.tif",
        raw / f"{area_id}_{year}.tiff",
        samples / f"{area_id}_{year}.tif",
        samples / f"sample_{area_id}_{year}.tif",
    ]


def resolve_raster_pair(
    area_id: str,
    year_t1: int,
    year_t2: int,
    settings: Settings | None = None,
) -> tuple[Path, Path] | None:
    """Return (t1, t2) paths if both years exist for the study area."""
    settings = settings or get_settings()
    path_t1 = next((p for p in _candidate_paths(settings, area_id, year_t1) if p.exists()), None)
    path_t2 = next((p for p in _candidate_paths(settings, area_id, year_t2) if p.exists()), None)
    if path_t1 and path_t2:
        return path_t1, path_t2
    return None


def list_available_rasters(settings: Settings | None = None) -> list[dict]:
    settings = settings or get_settings()
    found: list[dict] = []
    for folder in (settings.raw_data_dir, settings.samples_data_dir):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.tif")):
            stem = path.stem
            parts = stem.rsplit("_", 1)
            year = None
            area_id = stem
            if len(parts) == 2 and parts[1].isdigit():
                area_id, year = parts[0], int(parts[1])
            found.append(
                {
                    "path": str(path),
                    "area_id": area_id,
                    "year": year,
                    "size_mb": round(path.stat().st_size / 1e6, 2),
                }
            )
    return found
