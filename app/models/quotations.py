from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customers import Customer
    from app.models.financial import FinancialMovement
    from app.models.tasks import Task
    from app.models.tenant import Tenant
    from app.models.user import User


class QuotationStatus(str, enum.Enum):
    DRAFT = "draft"           # Borrador
    SENT = "sent"             # Enviada
    ACCEPTED = "accepted"     # Aceptada
    REJECTED = "rejected"     # Rechazada


class QuotationItemType(str, enum.Enum):
    PRODUCT = "product"       # Producto (material, papel, etc.)
    SERVICE = "service"       # Servicio (impresión, acabado, etc.)
    LABOR = "labor"           # Mano de obra
    EXPENSE = "expense"       # Gasto adicional (transporte, etc.)


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Número único de cotización (formato: COT-YYYY-NNNNN)
    quotation_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Estado
    status: Mapped[QuotationStatus] = mapped_column(
        Enum(QuotationStatus, native_enum=False),
        default=QuotationStatus.DRAFT,
        nullable=False,
        index=True,
    )
    
    # Fechas
    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expiry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Información del proyecto
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Condiciones comerciales
    payment_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)
    warranty_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Precios calculados
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    
    # Margen de utilidad (porcentaje)
    profit_margin: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=0,
        nullable=False,
    )
    
    # Relaciones
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    converted_task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relaciones
    customer: Mapped["Customer"] = relationship(back_populates="quotations", lazy="selectin")
    tenant: Mapped["Tenant"] = relationship(back_populates="quotations", lazy="selectin")
    creator: Mapped["User"] = relationship(back_populates="created_quotations", lazy="selectin")
    converted_task: Mapped["Task"] = relationship(lazy="selectin")
    items: Mapped[list["QuotationItem"]] = relationship(
        back_populates="quotation",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="QuotationItem.sort_order",
    )
    financial_movements: Mapped[list["FinancialMovement"]] = relationship(
        back_populates="quotation", lazy="dynamic", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("ix_quotations_tenant_status", "tenant_id", "status"),
        Index("ix_quotations_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_quotations_tenant_dates", "tenant_id", "issue_date"),
    )
    
    def __repr__(self) -> str:
        return f"<Quotation(id={self.id}, number={self.quotation_number}, status={self.status}, total={self.total})>"


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    quotation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Orden de visualización
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    
    # Tipo de ítem
    item_type: Mapped[QuotationItemType] = mapped_column(
        Enum(QuotationItemType, native_enum=False),
        nullable=False,
    )
    
    # Descripción
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Cantidad y unidades
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        default=1,
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(String(50), default="unidad", nullable=False)
    
    # Precios
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    
    # Descuento por ítem
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=0,
        nullable=False,
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    
    # Totales calculados
    line_subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=0,
        nullable=False,
    )
    
    # Metadatos adicionales (proveedor, especificaciones técnicas, etc.)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relación
    quotation: Mapped["Quotation"] = relationship(back_populates="items", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<QuotationItem(id={self.id}, name={self.name}, qty={self.quantity}, total={self.line_total})>"


# Agregar las relaciones inversas a Customer, Tenant, User
# (se harán en los respectivos archivos de modelos)