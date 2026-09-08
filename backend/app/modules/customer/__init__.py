from app.modules.customer.router import router as customer_router
from app.modules.customer.repository import customer_repository
from app.modules.customer.service import customer_service

__all__ = ["customer_router", "customer_repository", "customer_service"]
