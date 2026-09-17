import re
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from app.modules.export.registry import (
    ExportDefinition,
    ExportResourceType,
    get_export_definition,
    validate_resource,
    validate_format,
    validate_role,
    validate_filter_keys,
)
from app.modules.export.formatters import generate_csv, generate_xlsx

MAX_EXPORT_ROWS = 5000
SOURCE_PAGE_SIZE = 100


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", value.strip().lower())[:50]


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date format: '{value}'. Use YYYY-MM-DD.",
        )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime format: '{value}'. Use ISO 8601.",
        )


def _parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid integer: '{value}'.",
        )


def _sanitize_business_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", name.strip().lower())[:30]


def _build_filename(business_slug: str, resource: str, fmt: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> str:
    parts = [_sanitize_business_name(business_slug), resource]
    if date_from:
        parts.append(date_from)
    if date_to:
        parts.append(date_to)
    return "_".join(parts) + f".{fmt}"


class ExportService:
    def __init__(self) -> None:
        pass

    async def _fetch_all_paginated(self, fetch_fn, **kwargs) -> Tuple[list, bool]:
        """Fetch all pages up to MAX_EXPORT_ROWS.
        Returns (items, has_more) where has_more=True means source has >MAX_EXPORT_ROWS."""
        all_items = []
        page = 1
        while True:
            result = await fetch_fn(page=page, page_size=SOURCE_PAGE_SIZE, **kwargs)
            if hasattr(result, "items"):
                items = result.items
            elif isinstance(result, list):
                items = result
            else:
                break
            if not items:
                break
            all_items.extend(items)
            if len(all_items) >= MAX_EXPORT_ROWS:
                return all_items, True
            if len(items) < SOURCE_PAGE_SIZE:
                break
            page += 1
        return all_items, False

    def _serialize_model(self, model: Any) -> Dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="python", exclude_none=False)
        if hasattr(model, "dict"):
            return model.dict()
        return dict(model) if model else {}

    def _serialize_list(self, items: list) -> List[Dict[str, Any]]:
        return [self._serialize_model(item) for item in items]

    def _resolve_columns(self, rows: List[Dict[str, Any]]) -> List[str]:
        if not rows:
            return []
        all_keys: List[str] = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    all_keys.append(key)
                    seen.add(key)
        return all_keys

    def _paginate_rows(self, rows: list, page: int, page_size: int) -> Tuple[list, int]:
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        return rows[start:end], total

    def _format_response(self, content: bytes, fmt: str, filename: str) -> Tuple[bytes, str, str]:
        if fmt == "csv":
            content_type = "text/csv; charset=utf-8"
        elif fmt == "xlsx":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {fmt}",
            )
        return content, content_type, filename

    async def export_table(
        self,
        resource_key: str,
        business_id: str,
        user_id: str,
        user_role: str,
        fmt: str,
        export_mode: str,
        page: int,
        page_size: int,
        filters: Optional[Dict[str, Any]] = None,
        business_slug: str = "business",
    ) -> Tuple[bytes, str, str]:
        defn = validate_resource(resource_key)
        validate_format(defn, fmt)
        validate_role(defn, user_role)

        if filters:
            filter_keys = set(filters.keys()) - {"export_mode", "format", "page", "page_size"}
            validate_filter_keys(defn, filter_keys)

        data, columns = await self._fetch_data(
            defn, business_id, user_id, filters or {}
        )

        if export_mode == "current_page":
            data, total = self._paginate_rows(data, page, page_size)
        else:
            total = len(data)
            if total > MAX_EXPORT_ROWS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Export limit exceeded: maximum {MAX_EXPORT_ROWS} rows allowed. Found {total} rows. Please use filters to narrow your export.",
                )

        if not columns:
            columns = self._resolve_columns(data)

        rows = self._serialize_list(data) if data else []
        headers = columns if columns else (list(rows[0].keys()) if rows else [])

        date_from = (filters or {}).get("date_from")
        date_to = (filters or {}).get("date_to")
        filename = _build_filename(business_slug, resource_key, fmt, date_from, date_to)

        if fmt == "csv":
            content = generate_csv(headers, rows)
        else:
            content = generate_xlsx(headers, rows, sheet_name=resource_key[:31])

        return self._format_response(content, fmt, filename)

    async def export_report(
        self,
        resource_key: str,
        business_id: str,
        user_id: str,
        user_role: str,
        fmt: str,
        filters: Optional[Dict[str, Any]] = None,
        business_slug: str = "business",
    ) -> Tuple[bytes, str, str]:
        defn = validate_resource(resource_key)
        validate_format(defn, fmt)
        validate_role(defn, user_role)

        data, columns = await self._fetch_report_data(
            defn, business_id, user_id, filters or {}
        )

        rows = self._serialize_list(data) if data else []
        headers = columns if columns else (list(rows[0].keys()) if rows else [])

        filename = _build_filename(business_slug, resource_key, fmt)

        if fmt == "csv":
            content = generate_csv(headers, rows)
        else:
            content = generate_xlsx(headers, rows, sheet_name=resource_key[:31])

        return self._format_response(content, fmt, filename)

    async def export_platform(
        self,
        resource_key: str,
        user_id: str,
        user_role: str,
        fmt: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bytes, str, str]:
        defn = validate_resource(resource_key)
        validate_format(defn, fmt)
        validate_role(defn, user_role)

        data, columns = await self._fetch_platform_data(
            defn, user_id, filters or {}
        )

        rows = self._serialize_list(data) if data else []
        headers = columns if columns else (list(rows[0].keys()) if rows else [])

        filename = _build_filename("platform", resource_key, fmt)

        if fmt == "csv":
            content = generate_csv(headers, rows)
        else:
            content = generate_xlsx(headers, rows, sheet_name=resource_key[:31])

        return self._format_response(content, fmt, filename)

    async def _fetch_data(
        self,
        defn: ExportDefinition,
        business_id: str,
        user_id: str,
        filters: Dict[str, Any],
    ) -> Tuple[list, List[str]]:
        rk = defn.resource_key
        f = filters

        if rk == "products":
            from app.modules.product.service import product_service
            result = await product_service.list_products(
                business_id=business_id,
                user_id=user_id,
                search=f.get("search"),
                category_id=f.get("category_id"),
                page=1,
                page_size=MAX_EXPORT_ROWS,
            )
            return result.items, [
                "id", "sku", "name", "description", "product_type",
                "category_id", "unit_id", "status", "created_at", "updated_at",
            ]

        elif rk == "categories":
            from app.modules.category.service import category_service
            items = await category_service.list_categories(
                business_id=business_id,
                user_id=user_id,
            )
            if f.get("search"):
                q = f["search"].lower()
                items = [i for i in items if q in (i.name or "").lower() or q in (i.description or "").lower()]
            return items, [
                "id", "name", "description", "parent_id", "status", "created_at", "updated_at",
            ]

        elif rk == "units":
            from app.modules.unit.service import unit_service
            items = await unit_service.list_units(
                business_id=business_id,
                user_id=user_id,
            )
            if f.get("search"):
                q = f["search"].lower()
                items = [i for i in items if q in (i.name or "").lower()]
            return items, [
                "id", "name", "abbreviation", "unit_type", "status", "created_at", "updated_at",
            ]

        elif rk == "customers":
            from app.modules.customer.service import customer_service
            items, has_more = await self._fetch_all_paginated(
                lambda **kw: customer_service.list_customers(
                    business_id=business_id,
                    user_id=user_id,
                    search=f.get("search"),
                    page=kw["page"],
                    page_size=kw["page_size"],
                ),
            )
            if has_more:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Export limit exceeded: maximum {MAX_EXPORT_ROWS} rows allowed. Please use filters to narrow your export.",
                )
            return items, [
                "id", "code", "name", "email", "phone", "address",
                "customer_type", "status", "created_at", "updated_at",
            ]

        elif rk == "suppliers":
            from app.modules.supplier.service import supplier_service
            items, has_more = await self._fetch_all_paginated(
                lambda **kw: supplier_service.list_suppliers(
                    business_id=business_id,
                    user_id=user_id,
                    search=f.get("search"),
                    page=kw["page"],
                    page_size=kw["page_size"],
                ),
            )
            if has_more:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Export limit exceeded: maximum {MAX_EXPORT_ROWS} rows allowed. Please use filters to narrow your export.",
                )
            return items, [
                "id", "code", "name", "email", "phone", "address",
                "supplier_type", "status", "created_at", "updated_at",
            ]

        elif rk == "warehouse_stock":
            from app.modules.inventory.service import inventory_service
            items = await inventory_service.list_stock_balances(
                business_id=business_id,
                user_id=user_id,
                inventory_location_id=f.get("location_id"),
                product_id=f.get("product_id"),
                variant_id=f.get("variant_id"),
            )
            return items, [
                "id", "business_id", "inventory_location_id", "product_id",
                "variant_id", "quantity", "created_at", "updated_at",
            ]

        elif rk == "purchases":
            from app.modules.purchase.service import purchase_service
            from datetime import datetime as dt_mod
            result = await purchase_service.list_purchases(
                business_id=business_id,
                user_id=user_id,
                status_filter=f.get("status"),
                supplier_id=f.get("supplier_id"),
                branch_id=f.get("branch_id"),
                search=f.get("search"),
                page=1,
                page_size=MAX_EXPORT_ROWS,
            )
            items = result.items
            if f.get("date_from") or f.get("date_to"):
                df = _parse_date(f.get("date_from"))
                dt = _parse_date(f.get("date_to"))
                filtered = []
                for item in items:
                    item_date = getattr(item, "purchase_date", None) or getattr(item, "created_at", None)
                    if isinstance(item_date, datetime):
                        item_date = item_date.date()
                    if item_date is None:
                        filtered.append(item)
                        continue
                    if df and item_date < df:
                        continue
                    if dt and item_date > dt:
                        continue
                    filtered.append(item)
                items = filtered
            return items, [
                "id", "purchase_number", "supplier_id", "branch_id",
                "purchase_date", "status", "subtotal", "tax_amount",
                "total_amount", "notes", "created_at", "updated_at",
            ]

        elif rk == "sales_checkouts":
            from app.modules.sales.service import sales_service
            result = await sales_service.list_sales(
                business_id=business_id,
                user_id=user_id,
                status=f.get("status"),
                customer_id=f.get("customer_id"),
                branch_id=f.get("branch_id"),
                search=f.get("search"),
                date_from=_parse_datetime(f.get("date_from")),
                date_to=_parse_datetime(f.get("date_to")),
                page=1,
                page_size=MAX_EXPORT_ROWS,
            )
            return result.items, [
                "id", "sales_number", "customer_id", "branch_id",
                "sales_date", "status", "subtotal", "tax_amount",
                "discount_amount", "total_amount", "amount_paid",
                "change_amount", "notes", "created_at", "updated_at",
            ]

        elif rk == "sales_orders":
            from app.modules.sales_order.order_service import sales_order_service
            result = await sales_order_service.list_orders(
                business_id=business_id,
                user_id=user_id,
                status=f.get("status"),
                customer_id=f.get("customer_id"),
                branch_id=f.get("branch_id"),
                search=f.get("search"),
                page=1,
                page_size=MAX_EXPORT_ROWS,
            )
            return result.items, [
                "id", "order_number", "customer_id", "branch_id",
                "order_date", "status", "subtotal", "tax_amount",
                "total_amount", "notes", "created_at", "updated_at",
            ]

        elif rk == "delivery_notes":
            from app.modules.delivery_note.service import delivery_note_service
            result = await delivery_note_service.list_delivery_notes(
                business_id=business_id,
                user_id=user_id,
                status=f.get("status"),
                search=f.get("search"),
                page=1,
                page_size=MAX_EXPORT_ROWS,
            )
            return result.items, [
                "id", "note_number", "sales_order_id", "customer_id",
                "branch_id", "delivery_date", "status", "notes",
                "created_at", "updated_at",
            ]

        elif rk == "expenses":
            from app.modules.expense.service import expense_service
            result = await expense_service.list_expenses(
                business_id=business_id,
                user_id=user_id,
                category_id=f.get("category_id"),
                search=f.get("search"),
                date_from=_parse_datetime(f.get("date_from")),
                date_to=_parse_datetime(f.get("date_to")),
                page=1,
                page_size=MAX_EXPORT_ROWS,
            )
            return result.items, [
                "id", "expense_number", "category_id", "amount",
                "description", "expense_date", "status", "created_at", "updated_at",
            ]

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table resource '{rk}' data source not implemented.",
        )

    async def _fetch_report_data(
        self,
        defn: ExportDefinition,
        business_id: str,
        user_id: str,
        filters: Dict[str, Any],
    ) -> Tuple[list, List[str]]:
        rk = defn.resource_key
        f = filters

        if rk == "trial_balance":
            from app.modules.accounting.service import accounting_service
            result = await accounting_service.get_trial_balance(
                business_id=business_id,
                user_id=user_id,
            )
            rows = []
            for item in result.items:
                rows.append({
                    "account_code": item.account_code,
                    "account_name": item.account_name,
                    "account_type": item.account_type,
                    "normal_balance": item.normal_balance,
                    "debit_balance": item.debit_balance,
                    "credit_balance": item.credit_balance,
                })
            rows.append({
                "account_code": "TOTAL",
                "account_name": "",
                "account_type": "",
                "normal_balance": "",
                "debit_balance": result.total_debit,
                "credit_balance": result.total_credit,
            })
            return rows, [
                "account_code", "account_name", "account_type",
                "normal_balance", "debit_balance", "credit_balance",
            ]

        elif rk == "profit_loss":
            from app.modules.accounting.service import accounting_service
            period_id = f.get("period_id")
            if not period_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="period_id is required for profit_loss export.",
                )
            result = await accounting_service.get_profit_and_loss(
                business_id=business_id,
                period_id=period_id,
                user_id=user_id,
            )
            rows = []
            for item in result.revenue_items:
                rows.append({
                    "section": "Revenue",
                    "account_code": item.account_code,
                    "account_name": item.account_name,
                    "amount": item.amount,
                })
            rows.append({
                "section": "Revenue Total",
                "account_code": "",
                "account_name": "",
                "amount": result.total_revenue,
            })
            for item in result.expense_items:
                rows.append({
                    "section": "Expense",
                    "account_code": item.account_code,
                    "account_name": item.account_name,
                    "amount": item.amount,
                })
            rows.append({
                "section": "Expense Total",
                "account_code": "",
                "account_name": "",
                "amount": result.total_expense,
            })
            rows.append({
                "section": "Net Profit",
                "account_code": "",
                "account_name": "",
                "amount": result.net_profit,
            })
            return rows, ["section", "account_code", "account_name", "amount"]

        elif rk == "balance_sheet":
            from app.modules.accounting.service import accounting_service
            period_id = f.get("period_id")
            if not period_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="period_id is required for balance_sheet export.",
                )
            result = await accounting_service.get_balance_sheet(
                business_id=business_id,
                period_id=period_id,
                user_id=user_id,
            )
            rows = []
            for item in result.asset_items:
                rows.append({
                    "section": "Assets",
                    "account_code": item.account_code,
                    "account_name": item.account_name,
                    "balance": item.balance,
                })
            rows.append({
                "section": "Total Assets",
                "account_code": "",
                "account_name": "",
                "balance": result.total_assets,
            })
            for item in result.liability_items:
                rows.append({
                    "section": "Liabilities",
                    "account_code": item.account_code,
                    "account_name": item.account_name,
                    "balance": item.balance,
                })
            rows.append({
                "section": "Total Liabilities",
                "account_code": "",
                "account_name": "",
                "balance": result.total_liabilities,
            })
            for item in result.equity_items:
                rows.append({
                    "section": "Equity",
                    "account_code": item.account_code,
                    "account_name": item.account_name,
                    "balance": item.balance,
                })
            rows.append({
                "section": "Total Equity",
                "account_code": "",
                "account_name": "",
                "balance": result.total_equity,
            })
            rows.append({
                "section": "Net Profit (Current Period)",
                "account_code": "",
                "account_name": "",
                "balance": result.net_profit_current_period,
            })
            return rows, ["section", "account_code", "account_name", "balance"]

        elif rk == "cash_flow":
            from app.modules.accounting.service import accounting_service
            from datetime import date as date_type
            date_from = _parse_date(f.get("date_from"))
            date_to = _parse_date(f.get("date_to"))
            period_id = f.get("period_id")
            if not date_from or not date_to:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="date_from and date_to are required for cash_flow export.",
                )
            result = await accounting_service.get_cash_flow_statement(
                business_id=business_id,
                user_id=user_id,
                period_id=period_id,
                date_from=date_from,
                date_to=date_to,
            )
            rows = [
                {"line_item": "Opening Cash Balance", "amount": result.opening_cash_balance},
                {"line_item": "Cash Received from Customers", "amount": result.operating_activities.cash_received_from_customers},
                {"line_item": "Cash Paid to Suppliers", "amount": result.operating_activities.cash_paid_to_suppliers},
                {"line_item": "Cash Paid for Expenses", "amount": result.operating_activities.cash_paid_for_expenses},
                {"line_item": "Net Cash from Operating Activities", "amount": result.operating_activities.net_cash_from_operating},
                {"line_item": "Net Cash from Investing Activities", "amount": result.investing_activities.net_cash_from_investing},
                {"line_item": "Net Cash from Financing Activities", "amount": result.financing_activities.net_cash_from_financing},
                {"line_item": "Net Increase in Cash", "amount": result.net_increase_in_cash},
                {"line_item": "Closing Cash Balance", "amount": result.closing_cash_balance},
            ]
            return rows, ["line_item", "amount"]

        elif rk == "ar_aging":
            from app.modules.aging.service import aging_service
            from datetime import datetime as dt_mod
            as_of = _parse_datetime(f.get("as_of_date"))
            result = await aging_service.get_ar_aging(
                business_id=business_id,
                user_id=user_id,
                as_of_date=as_of,
                customer_id=f.get("customer_id"),
                branch_id=f.get("branch_id"),
            )
            rows = []
            for cust_item in result.customer_aging:
                row = {
                    "customer_id": cust_item.customer_id,
                    "customer_name": cust_item.customer_name,
                    "total_outstanding": cust_item.total_outstanding,
                }
                for bucket_name in ["current", "days_1_30", "days_31_60", "days_61_90", "days_91_120", "over_120"]:
                    setattr(cust_item, bucket_name, getattr(cust_item, bucket_name, None))
                    row[bucket_name] = getattr(cust_item, bucket_name, None) or Decimal("0")
                rows.append(row)
            return rows, [
                "customer_id", "customer_name", "total_outstanding",
                "current", "days_1_30", "days_31_60", "days_61_90", "days_91_120", "over_120",
            ]

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report resource '{rk}' data source not implemented.",
        )

    async def _fetch_platform_data(
        self,
        defn: ExportDefinition,
        user_id: str,
        filters: Dict[str, Any],
    ) -> Tuple[list, List[str]]:
        from app.modules.platform_admin.service import platform_admin_service
        from app.modules.authentication.schemas import PlatformRole
        from app.modules.authentication.repository import user_repository

        user = await user_repository.get_by_id(user_id)
        if not user or user.platform_role != PlatformRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform Super Admin authority required.",
            )

        rk = defn.resource_key
        f = filters

        if rk == "platform_businesses":
            from app.modules.business.schemas import BusinessStatus
            status_filter = None
            if f.get("status"):
                try:
                    status_filter = BusinessStatus(f["status"])
                except ValueError:
                    pass
            items = await platform_admin_service.list_businesses(
                superadmin=user,
                status_filter=status_filter,
                search=f.get("search"),
            )
            return items, [
                "id", "name", "slug", "business_type", "status",
                "owner_email", "owner_name", "membership_count",
                "branch_count", "subscription_status",
                "subscription_plan_name", "created_at", "updated_at",
            ]

        elif rk == "platform_users":
            items = await platform_admin_service.list_users(
                superadmin=user,
                search=f.get("search"),
            )
            return items, [
                "id", "email", "full_name", "platform_role",
                "is_active", "created_at",
            ]

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform resource '{rk}' data source not implemented.",
        )


export_service = ExportService()
