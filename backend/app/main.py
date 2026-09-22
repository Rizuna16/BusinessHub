from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import setup_exception_handlers
from app.modules.health.router import router as health_router
from app.modules.authentication.router import router as auth_router
from app.modules.authentication.service import AuthenticationService, auth_service
from app.modules.account.router import router as account_router
from app.modules.business.router import router as business_router
from app.modules.business_membership.router import router as business_membership_router
from app.modules.branch.router import router as branch_router
from app.modules.business_template.router import router as business_template_router
from app.modules.category.router import router as category_router
from app.modules.unit.router import router as unit_router
from app.modules.product.router import router as product_router
from app.modules.product_variant.router import router as product_variant_router
from app.modules.barcode.router import router as barcode_router
from app.modules.pricing.router import router as pricing_router
from app.modules.warehouse.router import router as warehouse_router
from app.modules.inventory.router import router as inventory_router
from app.modules.stock_opname.router import router as stock_opname_router
from app.modules.customer.router import router as customer_router
from app.modules.supplier.router import router as supplier_router
from app.modules.supplier_catalog.router import router as supplier_catalog_router
from app.modules.purchase.router import router as purchase_router
from app.modules.receiving.router import router as receiving_router
from app.modules.purchase_return.router import router as purchase_return_router
from app.modules.purchase_payable.router import router as purchase_payable_router
from app.modules.sales.router import router as sales_router
from app.modules.sales_payment.router import router as sales_payment_router
from app.modules.sales_return.router import router as sales_return_router
from app.modules.sales_receivable.router import router as sales_receivable_router
from app.modules.cash_account.router import router as cash_account_router
from app.modules.expense.router import router as expense_router
from app.modules.payment.router import router as payment_router
from app.modules.accounting.router import router as accounting_router
from app.modules.profitability.router import router as profitability_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.cashier_shift.router import router as cashier_shift_router
from app.modules.platform_admin.router import router as platform_admin_router
from app.modules.subscription.router import router as subscription_router
from app.modules.subscription.router import plans_router as subscription_plans_router
from app.modules.sales_order.router import quotation_router as quotation_router
from app.modules.sales_order.router import sales_order_router as sales_order_router
from app.modules.sales_order.router import availability_router as availability_router
from app.modules.delivery_note.router import delivery_note_router as delivery_note_router
from app.modules.notification.router import router as notification_router
from app.modules.export.router import router as export_router
from app.modules.transfer.router import router as transfer_router
from app.modules.customer_credit.router import router as customer_credit_router
from app.modules.inventory_batch.router import router as inventory_batch_router
from app.modules.product_image.router import router as product_image_router
from app.shared.utils import log_startup, format_datetime_iso

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database is reachable
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"Startup database check failed: {e}")
    yield
    # Shutdown: dispose engine
    await engine.dispose()


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
        lifespan=lifespan,
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
    app.include_router(
        auth_router,
    )

    app.include_router(
        account_router,
    )
    app.include_router(
        business_router,
    )
    app.include_router(
        business_membership_router,
    )
    app.include_router(
        branch_router,
    )
    app.include_router(
        business_template_router,
    )
    app.include_router(
        category_router,
    )
    app.include_router(
        unit_router,
    )

    app.include_router(
        product_router,
    )
    app.include_router(
        product_variant_router,
    )
    app.include_router(
        barcode_router,
    )
    app.include_router(
        pricing_router,
    )
    app.include_router(
        warehouse_router,
    )
    app.include_router(
        inventory_router,
    )
    app.include_router(
        stock_opname_router,
    )
    app.include_router(
        customer_router,
    )
    app.include_router(
        supplier_router,
    )
    app.include_router(
        supplier_catalog_router,
    )
    app.include_router(
        purchase_payable_router,
    )
    app.include_router(
        purchase_router,
    )
    app.include_router(
        receiving_router,
    )
    app.include_router(
        purchase_return_router,
    )
    app.include_router(
        sales_router,
    )
    app.include_router(
        sales_payment_router,
    )
    app.include_router(
        sales_return_router,
    )
    app.include_router(
        sales_receivable_router,
    )
    app.include_router(
        payment_router,
    )
    app.include_router(
        cash_account_router,
    )
    app.include_router(
        expense_router,
    )
    app.include_router(
        accounting_router,
    )
    app.include_router(
        profitability_router,
    )
    app.include_router(
        dashboard_router,
    )
    app.include_router(
        cashier_shift_router,
    )
    app.include_router(
        platform_admin_router,
    )
    app.include_router(
        subscription_router,
    )
    app.include_router(
        subscription_plans_router,
    )
    app.include_router(
        quotation_router,
    )
    app.include_router(
        sales_order_router,
    )
    app.include_router(
        availability_router,
    )
    app.include_router(
        delivery_note_router,
    )
    app.include_router(
        notification_router,
    )
    app.include_router(
        export_router,
    )
    app.include_router(
        transfer_router,
    )
    app.include_router(
        customer_credit_router,
    )
    app.include_router(
        inventory_batch_router,
    )
    app.include_router(
        product_image_router,
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

    # Development bootstrap: seed initial dev user and platform super admin on startup
    if settings.app_env != "production":
        @app.on_event("startup")
        async def seed_development_user():
            await InMemoryUserRepository.seed_development_user(
                email=settings.dev_seed_email,
                plain_password=settings.dev_seed_password,
                full_name=settings.dev_seed_name,
            )
            await InMemoryUserRepository.seed_development_superadmin(
                email=settings.dev_seed_superadmin_email,
                plain_password=settings.dev_seed_superadmin_password,
                full_name=settings.dev_seed_superadmin_name,
            )

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