from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings
from app.shared.utils import format_datetime_iso, log_health_check


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    timestamp: str


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse, summary="Health check endpoint")
async def health_check() -> HealthResponse:
    response = HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=format_datetime_iso(),
    )
    log_health_check(response.status, response.version)
    return response