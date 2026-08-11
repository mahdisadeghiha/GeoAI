"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the GeoAI change detection service."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GeoAI Urban Change Detection"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg2://geoai:geoai@localhost:5432/geoai_change"

    data_dir: Path = Path("./data")
    raw_data_dir: Path = Path("./data/raw")
    processed_data_dir: Path = Path("./data/processed")
    samples_data_dir: Path = Path("./data/samples")

    study_area_name: str = "Muscat, Oman"
    study_area_bbox: tuple[float, float, float, float] = (58.35, 23.50, 58.65, 23.65)
    target_crs: str = "EPSG:32640"

    change_threshold_sigma: float = 2.0
    min_change_region_area_m2: float = 1000.0
    ndvi_eps: float = 1e-8

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("study_area_bbox", mode="before")
    @classmethod
    def parse_bbox(cls, value: str | tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        if isinstance(value, str):
            parts = [float(v.strip()) for v in value.split(",")]
            if len(parts) != 4:
                raise ValueError("STUDY_AREA_BBOX must contain four comma-separated values")
            return (parts[0], parts[1], parts[2], parts[3])
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def _project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def resolve_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return (self._project_root() / path).resolve()

    def ensure_directories(self) -> None:
        """Create data directories if they do not exist."""
        for name in ("data_dir", "raw_data_dir", "processed_data_dir", "samples_data_dir"):
            resolved = self.resolve_path(getattr(self, name))
            resolved.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self, name, resolved)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for name in ("data_dir", "raw_data_dir", "processed_data_dir", "samples_data_dir"):
        object.__setattr__(settings, name, settings.resolve_path(getattr(settings, name)))
    settings.ensure_directories()
    return settings
