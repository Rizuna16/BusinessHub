import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("businesshub")


def get_logger() -> logging.Logger:
    return logger


def format_datetime_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_api_response(
    success: bool,
    data: Any = None,
    message: Optional[str] = None,
    errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "success": success,
        "timestamp": format_datetime_iso(),
    }
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    if errors:
        response["errors"] = errors
    return response


def log_startup(app_name: str, environment: str) -> None:
    logger.info(
        f"{app_name} started | env={environment} | timestamp={format_datetime_iso()}"
    )


def log_health_check(status: str, version: str) -> None:
    logger.debug(f"Health check: status={status} version={version}")


def log_error(error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    logger.error(f"Error: type={error_type} message={message} details={details or {}}")