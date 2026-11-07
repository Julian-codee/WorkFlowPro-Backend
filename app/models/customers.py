from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class CustomerType(str, enum.Enum):
    NATURAL = "natural"      # Persona natural
    LEGAL = "legal"          # Persona jurídica


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class IdentificationType(str, enum.Enum):
    # Persona natural
    CC = "cc"                # Cédula de ciudadanía
    CE = "ce"                # Cédula de extranjería
    PASSPORT = "passport"    # Pasaporte
    NIT = "nit"              # NIT (para personas naturales que lo tengan)
    # Persona jurídica
    NIT_LEGAL = "nit_legal"  # NIT empresa
    RUT = "rut"              # RUT (Colombia)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Tipo de cliente
    customer_type: Mapped[CustomerType] = mapped_column(
        Enum(CustomerType, native_enum=False),
        nullable=False,
        index=True,
    )
    
    # Estado administrativo
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, native_enum=False),
        default=CustomerStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    
    # ========== DATOS COMUNES ==========
    # Contacto principal
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(30), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    # Dirección
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, default="Colombia")
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Observaciones internas
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # ========== PERSONA NATURAL ==========
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    identification_type: Mapped[IdentificationType | None] = mapped_column(
        Enum(IdentificationType, native_enum=False), nullable=True
    )
    identification_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    
    # ========== PERSONA JURÍDICA ==========
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)  # Razón social
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)     # Nombre comercial
    tax_id_type: Mapped[IdentificationType | None] = mapped_column(
        Enum(IdentificationType, native_enum=False), nullable=True
    )
    tax_id_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)   # NIT
    verification_digit: Mapped[str | None] = mapped_column(String(5), nullable=True)           # DV
    
    legal_rep_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    legal_rep_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    main_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    fiscal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    commercial_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    economic_activity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # ========== DATOS DE SISTEMA ==========
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
    
    # ========== RELACIONES ==========
    tenant: Mapped["Tenant"] = relationship(back_populates="customers", lazy="selectin")
    creator: Mapped["User"] = relationship(back_populates="created_customers", lazy="selectin")
    notes: Mapped[list["CustomerNote"]] = relationship(
        back_populates="customer", lazy="dynamic", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["CustomerAuditLog"]] = relationship(
        back_populates="customer", lazy="dynamic", cascade="all, delete-orphan"
    )
    
    # Datos calculados (propiedades no persistidas)
    @property
    def full_name(self) -> str:
        if self.customer_type == CustomerType.NATURAL:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.business_name or self.trade_name or ""
    
    @property
    def display_name(self) -> str:
        if self.customer_type == CustomerType.NATURAL:
            name = self.full_name
            if self.identification_number:
                name += f" ({self.identification_number})"
            return name
        name = self.business_name or self.trade_name or ""
        if self.tax_id_number:
            name += f" ({self.tax_id_number})"
        return name

    __table_args__ = (
        Index("ix_customers_tenant_status", "tenant_id", "status"),
        Index("ix_customers_tenant_type", "tenant_id", "customer_type"),
        Index("ix_customers_tenant_email", "tenant_id", "email"),
        Index("ix_customers_tenant_phone", "tenant_id", "phone"),
        Index("ix_customers_tenant_identification", "tenant_id", "identification_number"),
        Index("ix_customers_tenant_tax_id", "tenant_id", "tax_id_number"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, type={self.customer_type}, name={self.display_name}, status={self.status})>"


class CustomerNote(Base):
    __tablename__ = "customer_notes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
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
    customer: Mapped["Customer"] = relationship(back_populates="notes", lazy="selectin")
    author: Mapped["User"] = relationship(lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<CustomerNote(id={self.id}, customer_id={self.customer_id})>"


class CustomerAuditAction(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    IDENTIFICATION_CHANGED = "identification_changed"
    STATUS_CHANGED = "status_changed"
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"
    ARCHIVED = "archived"


class CustomerAuditLog(Base):
    __tablename__ = "customer_audit_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    action: Mapped[CustomerAuditAction] = mapped_column(
        Enum(CustomerAuditAction, native_enum=False),
        nullable=False,
        index=True,
    )
    
    # Datos antes/después (JSON)
    old_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Campos específicos que cambiaron
    changed_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=True, default=list)
    
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    # Relaciones
    customer: Mapped["Customer"] = relationship(back_populates="audit_logs", lazy="selectin")
    user: Mapped["User"] = relationship(lazy="selectin")
    
    __table_args__ = (
        Index("ix_customer_audit_customer_created", "customer_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CustomerAuditLog(id={self.id}, action={self.action}, customer_id={self.customer_id})>"