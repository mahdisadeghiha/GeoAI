"""Health check endpoint."""

from fastapi import APIRouter

from app.core.database import check_db_connection
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok",
        database="connected" if db_ok else "unavailable",
    )
