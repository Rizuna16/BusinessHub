"""
Request-scoped RepositoryContainer connecting all 43 SQLAlchemy repositories to an AsyncSession.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.account.sqla_repository import SQLAlchemyAccountRepository
from app.modules.accounting.sqla_repository import SQLAlchemyAccountingRepository
from app.modules.authentication.sqla_repository import SQLAlchemyUserRepository
from app.modules.barcode.sqla_repository import SQLAlchemyBarcodeRepository
from app.modules.branch.sqla_repository import SQLAlchemyBranchRepository
from app.modules.business.sqla_repository import SQLAlchemyBusinessRepository
from app.modules.business_membership.sqla_repository import SQLAlchemyBusinessMembershipRepository
from app.modules.business_template.sqla_repository import (
    SQLAlchemyBusinessTemplateRepository,
    SQLAlchemyBusinessConfigurationRepository,
)
from app.modules.cash_account.sqla_repository import SQLAlchemyCashAccountRepository
from app.modules.cashier_shift.sqla_repository import SQLAlchemyCashierShiftRepository
from app.modules.category.sqla_repository import SQLAlchemyCategoryRepository
from app.modules.customer.sqla_repository import SQLAlchemyCustomerRepository
from app.modules.customer_credit.sqla_repository import SQLAlchemyStoreCreditLedgerRepository
from app.modules.delivery_note.sqla_repository import SQLAlchemyDeliveryNoteRepository
from app.modules.expense.sqla_repository import SQLAlchemyExpenseRepository
from app.modules.inventory.sqla_repository import (
    SQLAlchemyStockBalanceRepository,
    SQLAlchemyStockMovementRepository,
    SQLAlchemyInventoryCostRepository,
)
from app.modules.notification.sqla_repository import SQLAlchemyNotificationRepository
from app.modules.payment.sqla_repository import SQLAlchemyPaymentRepository
from app.modules.platform_admin.sqla_repository import SQLAlchemyPlatformAuditRepository
from app.modules.pricing.sqla_repository import (
    SQLAlchemyPriceListRepository,
    SQLAlchemyPriceEntryRepository,
)
from app.modules.product.sqla_repository import SQLAlchemyProductRepository
from app.modules.product_variant.sqla_repository import SQLAlchemyProductVariantRepository
from app.modules.purchase.sqla_repository import SQLAlchemyPurchaseRepository
from app.modules.purchase_return.sqla_repository import SQLAlchemyPurchaseReturnRepository
from app.modules.receiving.sqla_repository import SQLAlchemyReceivingRepository
from app.modules.sales.sqla_repository import SQLAlchemySalesRepository
from app.modules.sales_order.sqla_repository import (
    SQLAlchemyQuotationRepository,
    SQLAlchemySalesOrderRepository,
    SQLAlchemyReservationRepository,
)
from app.modules.sales_payment.sqla_repository import SQLAlchemySalesPaymentRepository
from app.modules.sales_return.sqla_repository import SQLAlchemySalesReturnRepository
from app.modules.stock_opname.sqla_repository import SQLAlchemyStockOpnameRepository
from app.modules.subscription.sqla_repository import SQLAlchemySubscriptionRepository
from app.modules.supplier.sqla_repository import SQLAlchemySupplierRepository
from app.modules.supplier_catalog.sqla_repository import SQLAlchemySupplierCatalogRepository
from app.modules.transfer.sqla_repository import SQLAlchemyTransferRepository
from app.modules.unit.sqla_repository import SQLAlchemyUnitRepository
from app.modules.warehouse.sqla_repository import (
    SQLAlchemyWarehouseRepository,
    SQLAlchemyInventoryLocationRepository,
)


class RepositoryContainer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.account = SQLAlchemyAccountRepository(session)
        self.accounting = SQLAlchemyAccountingRepository(session)
        self.user = SQLAlchemyUserRepository(session)
        self.barcode = SQLAlchemyBarcodeRepository(session)
        self.branch = SQLAlchemyBranchRepository(session)
        self.business = SQLAlchemyBusinessRepository(session)
        self.business_membership = SQLAlchemyBusinessMembershipRepository(session)
        self.business_template = SQLAlchemyBusinessTemplateRepository(session)
        self.business_configuration = SQLAlchemyBusinessConfigurationRepository(session)
        self.cash_account = SQLAlchemyCashAccountRepository(session)
        self.cashier_shift = SQLAlchemyCashierShiftRepository(session)
        self.category = SQLAlchemyCategoryRepository(session)
        self.customer = SQLAlchemyCustomerRepository(session)
        self.store_credit_ledger = SQLAlchemyStoreCreditLedgerRepository(session)
        self.delivery_note = SQLAlchemyDeliveryNoteRepository(session)
        self.expense = SQLAlchemyExpenseRepository(session)
        self.stock_balance = SQLAlchemyStockBalanceRepository(session)
        self.stock_movement = SQLAlchemyStockMovementRepository(session)
        self.inventory_cost = SQLAlchemyInventoryCostRepository(session)
        self.notification = SQLAlchemyNotificationRepository(session)
        self.payment = SQLAlchemyPaymentRepository(session)
        self.platform_audit = SQLAlchemyPlatformAuditRepository(session)
        self.price_list = SQLAlchemyPriceListRepository(session)
        self.price_entry = SQLAlchemyPriceEntryRepository(session)
        self.product = SQLAlchemyProductRepository(session)
        self.product_variant = SQLAlchemyProductVariantRepository(session)
        self.purchase = SQLAlchemyPurchaseRepository(session)
        self.purchase_return = SQLAlchemyPurchaseReturnRepository(session)
        self.receiving = SQLAlchemyReceivingRepository(session)
        self.sales = SQLAlchemySalesRepository(session)
        self.quotation = SQLAlchemyQuotationRepository(session)
        self.sales_order = SQLAlchemySalesOrderRepository(session)
        self.reservation = SQLAlchemyReservationRepository(session)
        self.sales_payment = SQLAlchemySalesPaymentRepository(session)
        self.sales_return = SQLAlchemySalesReturnRepository(session)
        self.stock_opname = SQLAlchemyStockOpnameRepository(session)
        self.subscription = SQLAlchemySubscriptionRepository(session)
        self.supplier = SQLAlchemySupplierRepository(session)
        self.supplier_catalog = SQLAlchemySupplierCatalogRepository(session)
        self.transfer = SQLAlchemyTransferRepository(session)
        self.unit = SQLAlchemyUnitRepository(session)
        self.warehouse = SQLAlchemyWarehouseRepository(session)
        self.inventory_location = SQLAlchemyInventoryLocationRepository(session)


def get_repositories(session: AsyncSession = None) -> RepositoryContainer:
    """Helper to get container given session."""
    return RepositoryContainer(session)
