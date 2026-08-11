"""SQLAlchemy ORM models for spatial analysis persistence."""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StudyArea(Base):
    __tablename__ = "study_areas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bbox: Mapped[str] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    crs: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="study_area")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_area_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("study_areas.id"))
    image_t1_path: Mapped[str | None] = mapped_column(Text)
    image_t2_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    statistics: Mapped[dict | None] = mapped_column(JSONB)
    outputs: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    study_area: Mapped[StudyArea | None] = relationship(back_populates="analysis_runs")
    change_regions: Mapped[list["ChangeRegion"]] = relationship(back_populates="analysis_run")


class ChangeRegion(Base):
    __tablename__ = "change_regions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("analysis_runs.id"))
    geom: Mapped[str] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    area_km2: Mapped[float] = mapped_column(Float)
    centroid: Mapped[str | None] = mapped_column(Geometry("POINT", srid=4326))
    bbox: Mapped[str | None] = mapped_column(Geometry("POLYGON", srid=4326))
    change_score: Mapped[float] = mapped_column(Float, default=0.0)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="change_regions")
