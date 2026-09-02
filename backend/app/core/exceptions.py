from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any

from app.shared.utils import create_api_response, log_error


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    log_error(
        "HTTPException",
        str(exc.detail),
        {"status_code": exc.status_code, "path": str(request.url)},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_api_response(
            success=False,
            message=str(exc.detail),
            errors=[str(exc.detail)] if exc.detail else None,
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    log_error(
        "ValidationError",
        "Request validation failed",
        {"path": str(request.url), "errors": exc.errors()},
    )
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        formatted_errors.append(f"{loc}: {error['msg']}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_api_response(
            success=False,
            message="Validasi gagal",
            errors=formatted_errors,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_error(
        "UnhandledException",
        str(exc),
        {"path": str(request.url), "type": type(exc).__name__},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_api_response(
            success=False,
            message="Terjadi kesalahan internal server",
            errors=["Internal Server Error"],
        ),
    )


def setup_exception_handlers(app: Any) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)