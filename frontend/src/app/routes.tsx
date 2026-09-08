import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from '@/pages/Home';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
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
import { Payments } from '@/pages/Payments';
import { PaymentDetail } from '@/pages/PaymentDetail';
import { ChartOfAccounts } from '@/pages/ChartOfAccounts';
import { AccountingJournals } from '@/pages/AccountingJournals';
import { AccountingJournalDetail } from '@/pages/AccountingJournalDetail';
import { AccountingTrialBalance } from '@/pages/AccountingTrialBalance';
import { AccountingPeriods } from '@/pages/AccountingPeriods';
import { AccountingProfitAndLoss } from '@/pages/AccountingProfitAndLoss';
import { AccountingBalanceSheet } from '@/pages/AccountingBalanceSheet';
import { TaxConfiguration } from '@/pages/TaxConfiguration';
import { TaxSummary } from '@/pages/TaxSummary';
import NotFound from '@/pages/NotFound';
import { ProtectedRoute, PublicOnlyRoute } from '@/components/ProtectedRoute';

const RouteConstants = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
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
  BUSINESS_RECEIVINGS: '/businesses/:businessId/receivings',
  BUSINESS_RECEIVING_DETAIL: '/businesses/:businessId/receivings/:receivingId',
  BUSINESS_PURCHASE_RETURNS: '/businesses/:businessId/purchase-returns',
  BUSINESS_PURCHASE_RETURN_DETAIL: '/businesses/:businessId/purchase-returns/:returnId',
  BUSINESS_PAYABLES: '/businesses/:businessId/purchases/payables',
  BUSINESS_PAYABLE_DETAIL: '/businesses/:businessId/purchases/payables/:purchaseId',
  BUSINESS_SUPPLIER_CATALOG: '/businesses/:businessId/supplier-catalog',
  BUSINESS_SUPPLIER_CATALOG_DETAIL: '/businesses/:businessId/supplier-catalog/:catalogId',
  BUSINESS_SALES: '/businesses/:businessId/sales',
  BUSINESS_SALES_DETAIL: '/businesses/:businessId/sales/:salesId',
  BUSINESS_SALES_RETURNS: '/businesses/:businessId/sales-returns',
  BUSINESS_SALES_RETURN_DETAIL: '/businesses/:businessId/sales-returns/:returnId',
  BUSINESS_RECEIVABLES: '/businesses/:businessId/receivables',
  BUSINESS_RECEIVABLE_DETAIL: '/businesses/:businessId/receivables/:salesId',
  BUSINESS_CASH_ACCOUNTS: '/businesses/:businessId/cash-accounts',
  BUSINESS_CASH_ACCOUNT_DETAIL: '/businesses/:businessId/cash-accounts/:accountId',
  BUSINESS_EXPENSES: '/businesses/:businessId/expenses',
  BUSINESS_EXPENSE_DETAIL: '/businesses/:businessId/expenses/:expenseId',
  BUSINESS_PAYMENTS: '/businesses/:businessId/payments',
  BUSINESS_PAYMENT_DETAIL: '/businesses/:businessId/payments/:paymentId',
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
};

export { RouteConstants };

export const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
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
        <Route
          path={RouteConstants.BUSINESS_DETAIL}
          element={
            <ProtectedRoute>
              <BusinessDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_MEMBERS}
          element={
            <ProtectedRoute>
              <BusinessMembers />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_BRANCHES}
          element={
            <ProtectedRoute>
              <Branches />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_CATEGORIES}
          element={
            <ProtectedRoute>
              <Categories />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_UNITS}
          element={
            <ProtectedRoute>
              <Units />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PRODUCTS}
          element={
            <ProtectedRoute>
              <Products />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PRODUCT_VARIANTS}
          element={
            <ProtectedRoute>
              <ProductVariants />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_BARCODES}
          element={
            <ProtectedRoute>
              <Barcodes />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PRICE_LISTS}
          element={
            <ProtectedRoute>
              <PriceLists />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PRICE_LIST_DETAIL}
          element={
            <ProtectedRoute>
              <PriceListDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_CONFIGURATION}
          element={
            <ProtectedRoute>
              <BusinessConfigurationPage />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_WAREHOUSES}
          element={
            <ProtectedRoute>
              <Warehouses />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_WAREHOUSE_DETAIL}
          element={
            <ProtectedRoute>
              <WarehouseDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_INVENTORY}
          element={
            <ProtectedRoute>
              <Inventory />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_STOCK_OPNAME}
          element={
            <ProtectedRoute>
              <StockOpnamePage />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_STOCK_CARD}
          element={
            <ProtectedRoute>
              <StockCard />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_CUSTOMERS}
          element={
            <ProtectedRoute>
              <Customers />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_SUPPLIERS}
          element={
            <ProtectedRoute>
              <Suppliers />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PURCHASES}
          element={
            <ProtectedRoute>
              <Purchases />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PURCHASE_DETAIL}
          element={
            <ProtectedRoute>
              <PurchaseDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_RECEIVINGS}
          element={
            <ProtectedRoute>
              <Receivings />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_RECEIVING_DETAIL}
          element={
            <ProtectedRoute>
              <ReceivingDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PURCHASE_RETURNS}
          element={
            <ProtectedRoute>
              <PurchaseReturns />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PURCHASE_RETURN_DETAIL}
          element={
            <ProtectedRoute>
              <PurchaseReturnDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PAYABLES}
          element={
            <ProtectedRoute>
              <Payables />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PAYABLE_DETAIL}
          element={
            <ProtectedRoute>
              <PayableDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_SUPPLIER_CATALOG}
          element={
            <ProtectedRoute>
              <SupplierCatalog />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_SUPPLIER_CATALOG_DETAIL}
          element={
            <ProtectedRoute>
              <SupplierCatalogDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_SALES}
          element={
            <ProtectedRoute>
              <Sales />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_SALES_DETAIL}
          element={
            <ProtectedRoute>
              <SalesDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_SALES_RETURNS}
          element={
            <ProtectedRoute>
              <SalesReturns />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_SALES_RETURN_DETAIL}
          element={
            <ProtectedRoute>
              <SalesReturnDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_RECEIVABLES}
          element={
            <ProtectedRoute>
              <Receivables />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_RECEIVABLE_DETAIL}
          element={
            <ProtectedRoute>
              <ReceivableDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_CASH_ACCOUNTS}
          element={
            <ProtectedRoute>
              <CashAccounts />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_CASH_ACCOUNT_DETAIL}
          element={
            <ProtectedRoute>
              <CashAccountDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_EXPENSES}
          element={
            <ProtectedRoute>
              <Expenses />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_EXPENSE_DETAIL}
          element={
            <ProtectedRoute>
              <ExpenseDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PAYMENTS}
          element={
            <ProtectedRoute>
              <Payments />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_PAYMENT_DETAIL}
          element={
            <ProtectedRoute>
              <PaymentDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_ACCOUNTING_COA}
          element={
            <ProtectedRoute>
              <ChartOfAccounts />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_ACCOUNTING_JOURNALS}
          element={
            <ProtectedRoute>
              <AccountingJournals />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_ACCOUNTING_JOURNAL_DETAIL}
          element={
            <ProtectedRoute>
              <AccountingJournalDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_ACCOUNTING_TRIAL_BALANCE}
          element={
            <ProtectedRoute>
              <AccountingTrialBalance />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_ACCOUNTING_PERIODS}
          element={
            <ProtectedRoute>
              <AccountingPeriods />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_ACCOUNTING_REPORT_PNL}
          element={
            <ProtectedRoute>
              <AccountingProfitAndLoss />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_ACCOUNTING_REPORT_BS}
          element={
            <ProtectedRoute>
              <AccountingBalanceSheet />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_TAX_CONFIGURATION}
          element={
            <ProtectedRoute>
              <TaxConfiguration />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_TAX_SUMMARY}
          element={
            <ProtectedRoute>
              <TaxSummary />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_AR_AGING}
          element={
            <ProtectedRoute>
              <ARAging />
            </ProtectedRoute>
          }
        />
        <Route
          path={RouteConstants.BUSINESS_AP_AGING}
          element={
            <ProtectedRoute>
              <APAging />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
};
