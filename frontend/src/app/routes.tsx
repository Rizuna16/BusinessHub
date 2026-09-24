import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from '@/pages/Home';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPassword from '@/pages/ResetPassword';
import Dashboard from '@/pages/Dashboard';
import Account from '@/pages/Account';
import Businesses from '@/pages/Businesses';
import NewBusiness from '@/pages/NewBusiness';
import BusinessDetail from '@/pages/BusinessDetail';
import BusinessMembers from '@/pages/BusinessMembers';
import Branches from '@/pages/Branches';
import Categories from '@/pages/Categories';
import Units from '@/pages/Units';
import { Products } from '@/pages/Products';
import { ProductVariants } from '@/pages/ProductVariants';
import { Barcodes } from '@/pages/Barcodes';
import { PriceLists } from '@/pages/PriceLists';
import { PriceListDetail } from '@/pages/PriceListDetail';
import BusinessConfigurationPage from '@/pages/BusinessConfiguration';
import Warehouses from '@/pages/Warehouses';
import WarehouseDetail from '@/pages/WarehouseDetail';
import { Inventory } from '@/pages/Inventory';
import StockOpnamePage from '@/pages/StockOpname';
import { StockCard } from '@/pages/StockCard';
import { Customers } from '@/pages/Customers';
import { Suppliers } from '@/pages/Suppliers';
import { Purchases } from '@/pages/Purchases';
import { PurchaseDetail } from '@/pages/PurchaseDetail';
import { PurchaseAnalytics } from '@/pages/PurchaseAnalytics';
import { Receivings } from '@/pages/Receivings';
import { ReceivingDetail } from '@/pages/ReceivingDetail';
import { PurchaseReturns } from '@/pages/PurchaseReturns';
import { PurchaseReturnDetail } from '@/pages/PurchaseReturnDetail';
import { Payables } from '@/pages/Payables';
import { PayableDetail } from '@/pages/PayableDetail';
import { SupplierCatalog } from '@/pages/SupplierCatalog';
import { SupplierCatalogDetail } from '@/pages/SupplierCatalogDetail';
import { Sales } from '@/pages/Sales';
import { SalesDetail } from '@/pages/SalesDetail';
import { SalesAnalytics } from '@/pages/SalesAnalytics';
import { SalesCheckout } from '@/pages/SalesCheckout';
import { Shifts } from '@/pages/Shifts';
import { ShiftDetail } from '@/pages/ShiftDetail';
import { SalesReturns } from '@/pages/SalesReturns';
import { SalesReturnDetail } from '@/pages/SalesReturnDetail';
import { Receivables } from '@/pages/Receivables';
import { ReceivableDetail } from '@/pages/ReceivableDetail';
import { ARAging } from '@/pages/ARAging';
import { APAging } from '@/pages/APAging';
import { CashAccounts } from '@/pages/CashAccounts';
import { CashAccountDetail } from '@/pages/CashAccountDetail';
import { Expenses } from '@/pages/Expenses';
import { ExpenseDetail } from '@/pages/ExpenseDetail';
import { ExpenseAnalytics } from '@/pages/ExpenseAnalytics';
import { Payments } from '@/pages/Payments';
import { PaymentDetail } from '@/pages/PaymentDetail';
import { PaymentAnalytics } from '@/pages/PaymentAnalytics';
import { ChartOfAccounts } from '@/pages/ChartOfAccounts';
import { AccountingJournals } from '@/pages/AccountingJournals';
import { AccountingJournalDetail } from '@/pages/AccountingJournalDetail';
import { AccountingTrialBalance } from '@/pages/AccountingTrialBalance';
import { AccountingPeriods } from '@/pages/AccountingPeriods';
import { AccountingProfitAndLoss } from '@/pages/AccountingProfitAndLoss';
import { AccountingBalanceSheet } from '@/pages/AccountingBalanceSheet';
import { TaxConfiguration } from '@/pages/TaxConfiguration';
import { TaxSummary } from '@/pages/TaxSummary';
import { ProductProfitability } from '@/pages/ProductProfitability';
import OperationalDashboard from '@/pages/OperationalDashboard';
import NotFound from '@/pages/NotFound';

import { PlatformProtectedRoute } from '@/components/platform/PlatformProtectedRoute';
import { PlatformShell } from '@/components/platform/PlatformShell';
import { PlatformDashboardPage } from '@/pages/platform/PlatformDashboard';
import { PlatformBusinessesPage } from '@/pages/platform/PlatformBusinesses';
import { PlatformBusinessDetailPage } from '@/pages/platform/PlatformBusinessDetail';
import { PlatformSubscriptionsPage } from '@/pages/platform/PlatformSubscriptions';
import { NotificationList } from '@/components/NotificationList';
import { PlatformUsersPage } from '@/pages/platform/PlatformUsers';
import { PlatformAuditLogsPage } from '@/pages/platform/PlatformAuditLogs';
import { DeliveryNotes } from '@/pages/DeliveryNotes';
import { DeliveryNoteDetail } from '@/pages/DeliveryNoteDetail';
import { PrintSalesCheckout } from '@/pages/print/PrintSalesCheckout';
import { PrintSalesOrder } from '@/pages/print/PrintSalesOrder';
import { PrintDeliveryNote } from '@/pages/print/PrintDeliveryNote';
import { PrintPurchase } from '@/pages/print/PrintPurchase';
import { PrintCustomerStatement } from '@/pages/print/PrintCustomerStatement';
import { PrintFinancialReport } from '@/pages/print/PrintFinancialReport';

import { ProtectedRoute, PublicOnlyRoute } from '@/components/ProtectedRoute';
import { AppShell } from '@/components/layout/AppShell';

const RouteConstants = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  APP: '/app',
  ACCOUNT: '/account',
  BUSINESSES: '/businesses',
  BUSINESSES_NEW: '/businesses/new',
  BUSINESS_DETAIL: '/businesses/:businessId',
  BUSINESS_MEMBERS: '/businesses/:businessId/members',
  BUSINESS_BRANCHES: '/businesses/:businessId/branches',
  BUSINESS_CATEGORIES: '/businesses/:businessId/categories',
  BUSINESS_UNITS: '/businesses/:businessId/units',
  BUSINESS_PRODUCTS: '/businesses/:businessId/products',
  BUSINESS_PRODUCT_VARIANTS: '/businesses/:businessId/products/:productId/variants',
  BUSINESS_BARCODES: '/businesses/:businessId/barcodes',
  BUSINESS_PRICE_LISTS: '/businesses/:businessId/price-lists',
  BUSINESS_PRICE_LIST_DETAIL: '/businesses/:businessId/price-lists/:priceListId',
  BUSINESS_CONFIGURATION: '/businesses/:businessId/configuration',
  BUSINESS_WAREHOUSES: '/businesses/:businessId/warehouses',
  BUSINESS_WAREHOUSE_DETAIL: '/businesses/:businessId/warehouses/:warehouseId',
  BUSINESS_INVENTORY: '/businesses/:businessId/inventory',
  BUSINESS_STOCK_OPNAME: '/businesses/:businessId/inventory/stock-opnames',
  BUSINESS_STOCK_CARD: '/businesses/:businessId/inventory/stock-cards',
  BUSINESS_CUSTOMERS: '/businesses/:businessId/customers',
  BUSINESS_SUPPLIERS: '/businesses/:businessId/suppliers',
  BUSINESS_PURCHASES: '/businesses/:businessId/purchases',
  BUSINESS_PURCHASE_DETAIL: '/businesses/:businessId/purchases/:purchaseId',
  BUSINESS_PURCHASE_ANALYTICS: '/businesses/:businessId/purchases/analytics',
  BUSINESS_RECEIVINGS: '/businesses/:businessId/receivings',
  BUSINESS_RECEIVING_DETAIL: '/businesses/:businessId/receivings/:receivingId',
  BUSINESS_PURCHASE_RETURNS: '/businesses/:businessId/purchase-returns',
  BUSINESS_PURCHASE_RETURN_DETAIL: '/businesses/:businessId/purchase-returns/:returnId',
  BUSINESS_PAYABLES: '/businesses/:businessId/purchases/payables',
  BUSINESS_PAYABLE_DETAIL: '/businesses/:businessId/purchases/payables/:purchaseId',
  BUSINESS_SUPPLIER_CATALOG: '/businesses/:businessId/supplier-catalog',
  BUSINESS_SUPPLIER_CATALOG_DETAIL: '/businesses/:businessId/supplier-catalog/:catalogId',
  BUSINESS_SALES: '/businesses/:businessId/sales',
  BUSINESS_CHECKOUT: '/businesses/:businessId/checkout',
  BUSINESS_SALES_DETAIL: '/businesses/:businessId/sales/:salesId',
  BUSINESS_SALES_ANALYTICS: '/businesses/:businessId/sales/analytics',
  BUSINESS_SALES_RETURNS: '/businesses/:businessId/sales-returns',
  BUSINESS_SALES_RETURN_DETAIL: '/businesses/:businessId/sales-returns/:returnId',
  BUSINESS_RECEIVABLES: '/businesses/:businessId/receivables',
  BUSINESS_RECEIVABLE_DETAIL: '/businesses/:businessId/receivables/:salesId',
  BUSINESS_CASH_ACCOUNTS: '/businesses/:businessId/cash-accounts',
  BUSINESS_CASH_ACCOUNT_DETAIL: '/businesses/:businessId/cash-accounts/:accountId',
  BUSINESS_EXPENSES: '/businesses/:businessId/expenses',
  BUSINESS_EXPENSE_DETAIL: '/businesses/:businessId/expenses/:expenseId',
  BUSINESS_EXPENSE_ANALYTICS: '/businesses/:businessId/expenses/analytics',
  BUSINESS_PAYMENTS: '/businesses/:businessId/payments',
  BUSINESS_PAYMENT_DETAIL: '/businesses/:businessId/payments/:paymentId',
  BUSINESS_PAYMENT_ANALYTICS: '/businesses/:businessId/payments/analytics',
  BUSINESS_ACCOUNTING_COA: '/businesses/:businessId/accounting/chart-of-accounts',
  BUSINESS_ACCOUNTING_JOURNALS: '/businesses/:businessId/accounting/journals',
  BUSINESS_ACCOUNTING_JOURNAL_DETAIL: '/businesses/:businessId/accounting/journals/:journalId',
  BUSINESS_ACCOUNTING_TRIAL_BALANCE: '/businesses/:businessId/accounting/trial-balance',
  BUSINESS_ACCOUNTING_PERIODS: '/businesses/:businessId/accounting/periods',
  BUSINESS_ACCOUNTING_REPORT_PNL: '/businesses/:businessId/accounting/reports/profit-and-loss',
  BUSINESS_ACCOUNTING_REPORT_BS: '/businesses/:businessId/accounting/reports/balance-sheet',
  BUSINESS_TAX_CONFIGURATION: '/businesses/:businessId/tax/configuration',
  BUSINESS_TAX_SUMMARY: '/businesses/:businessId/tax/summary',
  BUSINESS_AR_AGING: '/businesses/:businessId/receivables/aging',
  BUSINESS_AP_AGING: '/businesses/:businessId/purchases/payables/aging',
  BUSINESS_PRODUCT_PROFITABILITY: '/businesses/:businessId/reports/product-profitability',
  BUSINESS_OPERATIONAL_DASHBOARD: '/businesses/:businessId/dashboard/operational',
  
  PLATFORM: '/platform',
  PLATFORM_DASHBOARD: '/platform/dashboard',
  PLATFORM_BUSINESSES: '/platform/businesses',
  PLATFORM_BUSINESS_DETAIL: '/platform/businesses/:businessId',
  PLATFORM_SUBSCRIPTIONS: '/platform/subscriptions',
  PLATFORM_USERS: '/platform/users',
  PLATFORM_AUDIT_LOGS: '/platform/audit-logs',
};

export { RouteConstants };

export const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public & User-level standalone routes (no AppShell) */}
        <Route path={RouteConstants.HOME} element={<Home />} />
        <Route
          path={RouteConstants.LOGIN}
          element={
            <PublicOnlyRoute>
              <Login />
            </PublicOnlyRoute>
          }
        />
        <Route
          path={RouteConstants.REGISTER}
          element={
            <PublicOnlyRoute>
              <Register />
            </PublicOnlyRoute>
          }
        />
        <Route path={RouteConstants.FORGOT_PASSWORD} element={<ForgotPassword />} />
        <Route path={RouteConstants.RESET_PASSWORD} element={<ResetPassword />} />
        <Route
          path={RouteConstants.APP}
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.ACCOUNT}
          element={
            <ProtectedRoute>
              <Account />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESSES}
          element={
            <ProtectedRoute>
              <Businesses />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESSES_NEW}
          element={
            <ProtectedRoute>
              <NewBusiness />
            </ProtectedRoute>
          }
        />

        {/* Business-scoped routes — wrapped in AppShell (Sidebar + Topbar + BusinessContext) */}
        <Route
          path="/businesses/:businessId"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<BusinessDetail />} />
          <Route path="members" element={<BusinessMembers />} />
          <Route path="branches" element={<Branches />} />
          <Route path="categories" element={<Categories />} />
          <Route path="units" element={<Units />} />
          <Route path="products" element={<Products />} />
          <Route path="products/:productId/variants" element={<ProductVariants />} />
          <Route path="barcodes" element={<Barcodes />} />
          <Route path="price-lists" element={<PriceLists />} />
          <Route path="price-lists/:priceListId" element={<PriceListDetail />} />
          <Route path="configuration" element={<BusinessConfigurationPage />} />
          <Route path="warehouses" element={<Warehouses />} />
          <Route path="warehouses/:warehouseId" element={<WarehouseDetail />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="inventory/stock-opnames" element={<StockOpnamePage />} />
          <Route path="inventory/stock-cards" element={<StockCard />} />
          <Route path="customers" element={<Customers />} />
          <Route path="suppliers" element={<Suppliers />} />
          <Route path="purchases" element={<Purchases />} />
          <Route path="purchases/:purchaseId" element={<PurchaseDetail />} />
          <Route path="purchases/analytics" element={<PurchaseAnalytics />} />
          <Route path="receivings" element={<Receivings />} />
          <Route path="receivings/:receivingId" element={<ReceivingDetail />} />
          <Route path="purchase-returns" element={<PurchaseReturns />} />
          <Route path="purchase-returns/:returnId" element={<PurchaseReturnDetail />} />
          <Route path="purchases/payables" element={<Payables />} />
          <Route path="purchases/payables/:purchaseId" element={<PayableDetail />} />
          <Route path="purchases/payables/aging" element={<APAging />} />
          <Route path="supplier-catalog" element={<SupplierCatalog />} />
          <Route path="supplier-catalog/:catalogId" element={<SupplierCatalogDetail />} />
          <Route path="checkout" element={<SalesCheckout />} />
          <Route path="shifts" element={<Shifts />} />
          <Route path="shifts/:shiftId" element={<ShiftDetail />} />
          <Route path="sales" element={<Sales />} />
          <Route path="sales/:salesId" element={<SalesDetail />} />
          <Route path="sales/analytics" element={<SalesAnalytics />} />
          <Route path="sales-returns" element={<SalesReturns />} />
          <Route path="sales-returns/:returnId" element={<SalesReturnDetail />} />
          <Route path="receivables" element={<Receivables />} />
          <Route path="receivables/:salesId" element={<ReceivableDetail />} />
          <Route path="receivables/aging" element={<ARAging />} />
          <Route path="cash-accounts" element={<CashAccounts />} />
          <Route path="cash-accounts/:accountId" element={<CashAccountDetail />} />
          <Route path="expenses" element={<Expenses />} />
          <Route path="expenses/:expenseId" element={<ExpenseDetail />} />
          <Route path="expenses/analytics" element={<ExpenseAnalytics />} />
          <Route path="payments" element={<Payments />} />
          <Route path="payments/:paymentId" element={<PaymentDetail />} />
          <Route path="payments/analytics" element={<PaymentAnalytics />} />
          <Route path="accounting/chart-of-accounts" element={<ChartOfAccounts />} />
          <Route path="accounting/journals" element={<AccountingJournals />} />
          <Route path="accounting/journals/:journalId" element={<AccountingJournalDetail />} />
          <Route path="accounting/trial-balance" element={<AccountingTrialBalance />} />
          <Route path="accounting/periods" element={<AccountingPeriods />} />
          <Route path="accounting/reports/profit-and-loss" element={<AccountingProfitAndLoss />} />
          <Route path="accounting/reports/balance-sheet" element={<AccountingBalanceSheet />} />
          <Route path="tax/configuration" element={<TaxConfiguration />} />
          <Route path="tax/summary" element={<TaxSummary />} />
          <Route path="reports/product-profitability" element={<ProductProfitability />} />
          <Route path="dashboard/operational" element={<OperationalDashboard />} />
          <Route path="delivery-notes" element={<DeliveryNotes />} />
          <Route path="delivery-notes/:deliveryNoteId" element={<DeliveryNoteDetail />} />
        </Route>

        {/* Print-only views — standalone, outside AppShell for clean printing */}
        <Route
          path="/businesses/:businessId/print/sales-checkout/:id"
          element={<ProtectedRoute><PrintSalesCheckout /></ProtectedRoute>}
        />
        <Route
          path="/businesses/:businessId/print/sales-order/:id"
          element={<ProtectedRoute><PrintSalesOrder /></ProtectedRoute>}
        />
        <Route
          path="/businesses/:businessId/print/delivery-note/:id"
          element={<ProtectedRoute><PrintDeliveryNote /></ProtectedRoute>}
        />
        <Route
          path="/businesses/:businessId/print/purchase/:id"
          element={<ProtectedRoute><PrintPurchase /></ProtectedRoute>}
        />
        <Route
          path="/businesses/:businessId/print/customer-statement/:customerId"
          element={<ProtectedRoute><PrintCustomerStatement /></ProtectedRoute>}
        />
        <Route
          path="/businesses/:businessId/print/financial-report/:reportType"
          element={<ProtectedRoute><PrintFinancialReport /></ProtectedRoute>}
        />

        {/* Notification List Route (Tenant) */}
        <Route
          path="/app/notifications"
          element={
            <ProtectedRoute>
              <NotificationList scope="tenant" />
            </ProtectedRoute>
          }
        />

        {/* Platform Administration Routes */}
        <Route
          path="/platform"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <PlatformDashboardPage />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />
        <Route
          path="/platform/dashboard"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <PlatformDashboardPage />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />
        <Route
          path="/platform/businesses"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <PlatformBusinessesPage />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />
        <Route
          path="/platform/businesses/:businessId"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <PlatformBusinessDetailPage />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />
        <Route
          path="/platform/subscriptions"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <PlatformSubscriptionsPage />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />
        <Route
          path="/platform/users"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <PlatformUsersPage />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />
        <Route
          path="/platform/audit-logs"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <PlatformAuditLogsPage />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />
        <Route
          path="/platform/notifications"
          element={
            <PlatformProtectedRoute>
              <PlatformShell>
                <NotificationList scope="platform" />
              </PlatformShell>
            </PlatformProtectedRoute>
          }
        />

        {/* Global catch-all */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
};
