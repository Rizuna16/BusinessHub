from datetime import date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ProductProfitabilityPeriodInfo(BaseModel):
    date_from: date
    date_to: date
    period_name: Optional[str] = None


class ProductProfitabilityItem(BaseModel):
    group_id: str
    group_name: str
    group_code: Optional[str] = None
    category_name: Optional[str] = None
    customer_name: Optional[str] = None
    branch_name: Optional[str] = None
    net_revenue: Decimal
    total_discount: Decimal
    total_tax: Decimal
    gross_sales: Decimal
    cogs: Decimal
    gross_profit: Decimal
    gross_margin_percentage: Optional[Decimal] = None
    units_sold: Decimal
    units_returned: Decimal
    sales_count: int
    return_count: int


class ProductProfitabilitySummary(BaseModel):
    total_net_revenue: Decimal
    total_cogs: Decimal
    total_gross_profit: Decimal
    overall_gross_margin_percentage: Optional[Decimal] = None
    total_sales_count: int
    total_return_count: int
    total_units_sold: Decimal
    total_units_returned: Decimal


class ProductProfitabilityResponse(BaseModel):
    period: ProductProfitabilityPeriodInfo
    summary: ProductProfitabilitySummary
    items: List[ProductProfitabilityItem]
