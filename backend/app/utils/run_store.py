"""File-based persistence for analysis runs when PostGIS is unavailable."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.core.config import Settings, get_settings


def _run_dir(settings: Settings, run_id: uuid.UUID) -> Path:
    return settings.processed_data_dir / str(run_id)


def save_run_artifacts(run_id: uuid.UUID, statistics: dict, outputs: dict, geojson: dict) -> None:
    settings = get_settings()
    run_dir = _run_dir(settings, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "statistics.json").write_text(json.dumps(statistics, indent=2), encoding="utf-8")
    (run_dir / "outputs.json").write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    (run_dir / "change_regions.geojson").write_text(json.dumps(geojson), encoding="utf-8")


def load_statistics(run_id: uuid.UUID | None = None) -> dict | None:
    settings = get_settings()
    if run_id:
        path = _run_dir(settings, run_id) / "statistics.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    run_dirs = sorted(settings.processed_data_dir.glob("*/statistics.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_dirs:
        return None
    return json.loads(run_dirs[0].read_text(encoding="utf-8"))


def load_geojson(run_id: uuid.UUID | None = None) -> dict | None:
    settings = get_settings()
    if run_id:
        path = _run_dir(settings, run_id) / "change_regions.geojson"
    else:
        run_dirs = sorted(settings.processed_data_dir.glob("*/change_regions.geojson"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not run_dirs:
            return None
        path = run_dirs[0]

    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def resolve_run_id(run_id: uuid.UUID | None = None) -> uuid.UUID | None:
    if run_id:
        return run_id
    settings = get_settings()
    run_dirs = sorted(settings.processed_data_dir.glob("*/statistics.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_dirs:
        return None
    return uuid.UUID(run_dirs[0].parent.name)
