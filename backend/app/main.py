import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.modules.health.router import router as health_router
from app.shared.utils import log_startup, format_datetime_iso


def create_app() -> FastAPI:
    """Application factory pattern untuk FastAPI modular monolith."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "BusinessHub Backend - SaaS Multi-Tenant Management Platform. "
            "Platform manajemen bisnis multi-tenant untuk berbagai jenis usaha."
        ),
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # API versioning prefix
    app.include_router(
        health_router,
        prefix=settings.api_v1_prefix,
        tags=["Health"],
    )

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "message": f"BusinessHub API v{settings.app_version}",
            "status": "running",
            "environment": settings.app_env,
            "timestamp": format_datetime_iso(),
            "docs": "/docs" if settings.app_env != "production" else None,
        }

    return app


app = create_app()

if __name__ == "__main__":
    log_startup(settings.app_name, settings.app_env)
    uvicorn.run(
        app="app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
    )