import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Text, Boolean, DateTime, Numeric, Integer, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BusinessTemplateInDB(Base):
    __tablename__ = "business_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    business_type: Mapped[str] = mapped_column(String(50))
    preset_code: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(20))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    modules: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    features: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    menus: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    dashboard_widgets: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    default_configuration: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BusinessConfigurationRecord(Base):
    __tablename__ = "business_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    template_id: Mapped[str] = mapped_column(String(36))
    template_code: Mapped[str] = mapped_column(String(50))
    template_version: Mapped[str] = mapped_column(String(20))
    preset_code: Mapped[str] = mapped_column(String(50))
    configuration: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    module_overrides: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    feature_overrides: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    menu_overrides: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    widget_overrides: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
