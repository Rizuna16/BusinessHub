from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.shared.utils import format_datetime_iso, log_health_check


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    timestamp: str


class ReadyResponse(BaseModel):
    status: str
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


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe — verifies DB connectivity")
async def readiness_check() -> JSONResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=ReadyResponse(
                status="ready",
                timestamp=format_datetime_iso(),
            ).model_dump(),
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ReadyResponse(
                status="not_ready",
                timestamp=format_datetime_iso(),
            ).model_dump(),
        )