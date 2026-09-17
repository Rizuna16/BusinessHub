from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


class ExportMode(str, Enum):
    CURRENT_PAGE = "current_page"
    ALL_MATCHING = "all_matching"


class ExportRequest(BaseModel):
    format: ExportFormat = ExportFormat.CSV
    export_mode: ExportMode = ExportMode.ALL_MATCHING
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")


class ExportTableFilters(BaseModel):
    search: Optional[str] = None
    category_id: Optional[str] = None
    product_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    location_id: Optional[str] = None
    supplier_id: Optional[str] = None
    customer_id: Optional[str] = None
    branch_id: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    as_of_date: Optional[str] = None
    unit_type: Optional[str] = None


class ExportTableRequest(BaseModel):
    format: ExportFormat = ExportFormat.CSV
    export_mode: ExportMode = ExportMode.ALL_MATCHING
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")
    filters: Optional[ExportTableFilters] = None


class ExportTableQueryParams(BaseModel):
    format: ExportFormat = ExportFormat.CSV
    export_mode: ExportMode = ExportMode.ALL_MATCHING
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(default="desc")
    search: Optional[str] = None
    category_id: Optional[str] = None
    product_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    location_id: Optional[str] = None
    supplier_id: Optional[str] = None
    customer_id: Optional[str] = None
    branch_id: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    as_of_date: Optional[str] = None
    unit_type: Optional[str] = None


class ExportInfo(BaseModel):
    resource: str
    format: ExportFormat
    export_mode: ExportMode
    total_rows: int
    exported_rows: int
    filename: str
