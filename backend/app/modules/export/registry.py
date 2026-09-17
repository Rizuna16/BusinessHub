from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

from fastapi import HTTPException, status


class ExportResourceType(str, Enum):
    TABLE = "table"
    REPORT = "report"
    PLATFORM = "platform"


@dataclass
class ExportDefinition:
    resource_key: str
    resource_type: ExportResourceType
    allowed_formats: Set[str]
    required_roles: Set[str]
    description: str
    supports_pagination: bool = False
    filters: List[str] = field(default_factory=list)


EXPORT_REGISTRY: Dict[str, ExportDefinition] = {}


def register_export(definition: ExportDefinition) -> None:
    EXPORT_REGISTRY[definition.resource_key] = definition


def get_export_definition(resource_key: str) -> Optional[ExportDefinition]:
    return EXPORT_REGISTRY.get(resource_key)


def validate_resource(resource_key: str) -> ExportDefinition:
    defn = EXPORT_REGISTRY.get(resource_key)
    if defn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export resource '{resource_key}' not found.",
        )
    return defn


def validate_format(defn: ExportDefinition, export_format: str) -> None:
    if export_format not in defn.allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{export_format}' for resource '{defn.resource_key}'. Allowed: {', '.join(sorted(defn.allowed_formats))}",
        )


def validate_role(defn: ExportDefinition, user_role: str) -> None:
    if defn.required_roles and user_role not in defn.required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for exporting '{defn.resource_key}'. Required roles: {', '.join(sorted(defn.required_roles))}",
        )


def validate_filter_keys(defn: ExportDefinition, provided_keys: Set[str]) -> None:
    allowed_set = set(defn.filters)
    invalid = provided_keys - allowed_set
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid filters for '{defn.resource_key}': {', '.join(sorted(invalid))}",
        )


register_export(ExportDefinition(
    resource_key="products",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Product catalog export",
    supports_pagination=True,
    filters=["search", "category_id", "status", "product_type"],
))

register_export(ExportDefinition(
    resource_key="categories",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Product categories export",
    supports_pagination=False,
    filters=["search", "status"],
))

register_export(ExportDefinition(
    resource_key="units",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Unit of measurement export",
    supports_pagination=False,
    filters=["search", "unit_type", "status"],
))

register_export(ExportDefinition(
    resource_key="customers",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Customer list export",
    supports_pagination=True,
    filters=["search", "status"],
))

register_export(ExportDefinition(
    resource_key="suppliers",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Supplier list export",
    supports_pagination=True,
    filters=["search", "status"],
))

register_export(ExportDefinition(
    resource_key="warehouse_stock",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Inventory stock balances export",
    supports_pagination=False,
    filters=["warehouse_id", "location_id", "product_id", "variant_id"],
))

register_export(ExportDefinition(
    resource_key="purchases",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Purchase records export",
    supports_pagination=True,
    filters=["search", "status", "supplier_id", "branch_id", "date_from", "date_to"],
))

register_export(ExportDefinition(
    resource_key="sales_checkouts",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Sales checkout records export",
    supports_pagination=True,
    filters=["search", "status", "customer_id", "branch_id", "date_from", "date_to"],
))

register_export(ExportDefinition(
    resource_key="sales_orders",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Sales orders export",
    supports_pagination=True,
    filters=["search", "status", "customer_id", "branch_id"],
))

register_export(ExportDefinition(
    resource_key="delivery_notes",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Delivery notes export",
    supports_pagination=True,
    filters=["search", "status", "branch_id"],
))

register_export(ExportDefinition(
    resource_key="expenses",
    resource_type=ExportResourceType.TABLE,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN", "MEMBER"},
    description="Expense records export",
    supports_pagination=True,
    filters=["search", "status", "category_id", "branch_id", "date_from", "date_to"],
))

register_export(ExportDefinition(
    resource_key="ar_aging",
    resource_type=ExportResourceType.REPORT,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN"},
    description="Accounts receivable aging report export",
    supports_pagination=False,
    filters=["as_of_date", "customer_id", "branch_id"],
))

register_export(ExportDefinition(
    resource_key="trial_balance",
    resource_type=ExportResourceType.REPORT,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN"},
    description="Trial balance report export",
    supports_pagination=False,
    filters=[],
))

register_export(ExportDefinition(
    resource_key="profit_loss",
    resource_type=ExportResourceType.REPORT,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN"},
    description="Profit and loss report export",
    supports_pagination=False,
    filters=["period_id"],
))

register_export(ExportDefinition(
    resource_key="balance_sheet",
    resource_type=ExportResourceType.REPORT,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN"},
    description="Balance sheet report export",
    supports_pagination=False,
    filters=["period_id"],
))

register_export(ExportDefinition(
    resource_key="cash_flow",
    resource_type=ExportResourceType.REPORT,
    allowed_formats={"csv", "xlsx"},
    required_roles={"OWNER", "ADMIN"},
    description="Cash flow statement export",
    supports_pagination=False,
    filters=["period_id", "date_from", "date_to"],
))

register_export(ExportDefinition(
    resource_key="platform_businesses",
    resource_type=ExportResourceType.PLATFORM,
    allowed_formats={"csv", "xlsx"},
    required_roles={"SUPER_ADMIN"},
    description="Platform business listing export",
    supports_pagination=False,
    filters=["search", "status"],
))

register_export(ExportDefinition(
    resource_key="platform_users",
    resource_type=ExportResourceType.PLATFORM,
    allowed_formats={"csv", "xlsx"},
    required_roles={"SUPER_ADMIN"},
    description="Platform user listing export",
    supports_pagination=False,
    filters=["search"],
))
