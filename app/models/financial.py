from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customers import Customer
    from app.models.quotations import Quotation
    from app.models.tasks import Task
    from app.models.tenant import Tenant
    from app.models.user import User


class MovementType(str, enum.Enum):
    INCOME = "income"       # Ingreso
    EXPENSE = "expense"     # Egreso
    TRANSFER = "transfer"   # Transferencia interna (no afecta flujo neto)


class MovementCategory(str, enum.Enum):
    SALES = "sales"                 # Ventas
    SERVICES = "services"           # Servicios
    PRODUCTS = "products"           # Productos
    RENT = "rent"                   # Alquiler
    UTILITIES = "utilities"         # Servicios públicos
    PAYROLL = "payroll"             # Nómina
    SUPPLIES = "supplies"           # Insumos
    MARKETING = "marketing"         # Marketing
    TRANSPORT = "transport"         # Transporte
    MAINTENANCE = "maintenance"     # Mantenimiento
    TAXES = "taxes"                 # Impuestos
    LOANS = "loans"                 # Préstamos
    INVESTMENTS = "investments"     # Inversiones
    OTHER_INCOME = "other_income"   # Otros ingresos
    OTHER_EXPENSE = "other_expense" # Otros egresos


class PaymentMethod(str, enum.Enum):
    CASH = "cash"               # Efectivo
    BANK_TRANSFER = "bank_transfer"  # Transferencia bancaria
    CARD = "card"               # Tarjeta
    CHECK = "check"             # Cheque
    DIGITAL_WALLET = "digital_wallet"  # Billetera digital
    CRYPTO = "crypto"           # Criptomoneda
    OTHER = "other"             # Otro


class WeeklyPeriodStatus(str, enum.Enum):
    OPEN = "open"               # Abierto
    CLOSING = "closing"         # En proceso de cierre
    CLOSED = "closed"           # Cerrado
    ADJUSTED = "adjusted"       # Con ajustes posteriores


class CashClosureStatus(str, enum.Enum):
    PENDING = "pending"         # Pendiente
    CONFIRMED = "confirmed"     # Confirmado
    ADJUSTED = "adjusted"       # Ajustado
    DISPUTED = "disputed"       # En disputa


class AdjustmentType(str, enum.Enum):
    LATE_INCOME = "late_income"         # Ingreso tardío
    LATE_EXPENSE = "late_expense"       # Egreso tardío
    CORRECTION = "correction"           # Corrección
    DISCREPANCY = "discrepancy"         # Diferencia de caja


class FinancialMovement(Base):
    __tablename__ = "financial_movements"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Fecha real del movimiento
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Fecha de registro en el sistema
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Tipo y categoría
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, native_enum=False),
        nullable=False,
        index=True,
    )
    category: Mapped[MovementCategory] = mapped_column(
        Enum(MovementCategory, native_enum=False),
        nullable=False,
        index=True,
    )

    # Valores
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    # Método de pago
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False),
        nullable=False,
    )

    # Cuenta de dinero
    cash_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cash_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Concepto
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Referencias opcionales
    customer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quotation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Movimiento tardío
    is_late_entry: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    late_entry_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    late_entry_approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Semana a la que pertenece
    weekly_period_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("weekly_periods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Multi-tenancy
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

    # Timestamps
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
    tenant: Mapped["Tenant"] = relationship(lazy="selectin")
    creator: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
        lazy="selectin",
    )
    late_approver: Mapped["User"] = relationship(
        foreign_keys=[late_entry_approved_by],
        lazy="selectin",
    )
    cash_account: Mapped["CashAccount"] = relationship(lazy="selectin")
    customer: Mapped["Customer"] = relationship(lazy="selectin")
    task: Mapped["Task"] = relationship(lazy="selectin")
    quotation: Mapped["Quotation"] = relationship(
        foreign_keys=[quotation_id],
        lazy="selectin",
    )
    weekly_period: Mapped["WeeklyPeriod"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_movements_tenant_date", "tenant_id", "transaction_date"),
        Index("ix_movements_tenant_type_date", "tenant_id", "movement_type", "transaction_date"),
        Index("ix_movements_tenant_account_date", "tenant_id", "cash_account_id", "transaction_date"),
        Index("ix_movements_tenant_late", "tenant_id", "is_late_entry"),
    )

    def __repr__(self) -> str:
        return f"<FinancialMovement(id={self.id}, type={self.movement_type}, amount={self.amount}, date={self.transaction_date})>"


class CashAccount(Base):
    __tablename__ = "cash_accounts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tipo de cuenta
    account_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cash")

    # Saldo actual (se actualiza con cada movimiento)
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )

    # Moneda
    currency: Mapped[str] = mapped_column(String(3), default="COP", nullable=False)

    # Estado
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Multi-tenancy
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    tenant: Mapped["Tenant"] = relationship(lazy="selectin")
    movements: Mapped[list["FinancialMovement"]] = relationship(
        back_populates="cash_account", lazy="dynamic", cascade="all, delete-orphan"
    )
    weekly_periods: Mapped[list["WeeklyPeriod"]] = relationship(
        back_populates="cash_account", lazy="dynamic", cascade="all, delete-orphan"
    )
    cash_closures: Mapped[list["CashClosure"]] = relationship(
        back_populates="cash_account", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_cash_accounts_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<CashAccount(id={self.id}, name={self.name}, code={self.code}, balance={self.current_balance})>"


class WeeklyPeriod(Base):
    __tablename__ = "weekly_periods"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Número de semana (1-53)
    week_number: Mapped[int] = mapped_column(nullable=False)

    # Año
    year: Mapped[int] = mapped_column(nullable=False)

    # Fechas
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Estado
    status: Mapped[WeeklyPeriodStatus] = mapped_column(
        Enum(WeeklyPeriodStatus, native_enum=False),
        default=WeeklyPeriodStatus.OPEN,
        nullable=False,
        index=True,
    )

    # Saldos
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )
    total_income: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )
    total_expense: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )
    net_flow: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )
    expected_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )

    # Cierre
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Cuenta de dinero
    cash_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cash_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Multi-tenancy
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

    # Timestamps
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
    tenant: Mapped["Tenant"] = relationship(lazy="selectin")
    creator: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
        lazy="selectin",
    )
    closer: Mapped["User"] = relationship(
        foreign_keys=[closed_by_id],
        lazy="selectin",
    )
    cash_account: Mapped["CashAccount"] = relationship(lazy="selectin")
    movements: Mapped[list["FinancialMovement"]] = relationship(
        back_populates="weekly_period", lazy="dynamic"
    )
    cash_closure: Mapped["CashClosure"] = relationship(
        back_populates="weekly_period", lazy="selectin", uselist=False
    )

    __table_args__ = (
        Index("ix_weekly_periods_tenant_dates", "tenant_id", "start_date", "end_date"),
        Index("ix_weekly_periods_tenant_status", "tenant_id", "status"),
        Index("ix_weekly_periods_tenant_account", "tenant_id", "cash_account_id"),
    )

    def __repr__(self) -> str:
        return f"<WeeklyPeriod(id={self.id}, week={self.week_number}/{self.year}, status={self.status})>"


class CashClosure(Base):
    __tablename__ = "cash_closures"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Referencia a la semana
    weekly_period_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("weekly_periods.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Cuenta de dinero
    cash_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cash_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Valores del cierre
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )
    total_income: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )
    total_expense: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )
    net_flow: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )
    expected_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )
    physical_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )
    discrepancy: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal(0),
        nullable=False,
    )

    # Estado
    status: Mapped[CashClosureStatus] = mapped_column(
        Enum(CashClosureStatus, native_enum=False),
        default=CashClosureStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Observaciones
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    discrepancy_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Responsable
    closed_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Ajustes posteriores
    adjustment_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Multi-tenancy
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    tenant: Mapped["Tenant"] = relationship(lazy="selectin")
    weekly_period: Mapped["WeeklyPeriod"] = relationship(back_populates="cash_closure", lazy="selectin")
    cash_account: Mapped["CashAccount"] = relationship(lazy="selectin")
    closer: Mapped["User"] = relationship(lazy="selectin")
    adjustments: Mapped[list["ClosureAdjustment"]] = relationship(
        back_populates="cash_closure", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_cash_closures_tenant_account", "tenant_id", "cash_account_id"),
        Index("ix_cash_closures_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<CashClosure(id={self.id}, period={self.weekly_period_id}, status={self.status})>"


class ClosureAdjustment(Base):
    __tablename__ = "closure_adjustments"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Cierre afectado
    cash_closure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cash_closures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Movimiento que causó el ajuste
    movement_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_movements.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Tipo de ajuste
    adjustment_type: Mapped[AdjustmentType] = mapped_column(
        Enum(AdjustmentType, native_enum=False),
        nullable=False,
        index=True,
    )

    # Valores
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )
    impact_on_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    # Justificación
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Responsable
    created_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Multi-tenancy
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    tenant: Mapped["Tenant"] = relationship(lazy="selectin")
    cash_closure: Mapped["CashClosure"] = relationship(back_populates="adjustments", lazy="selectin")
    movement: Mapped["FinancialMovement"] = relationship(lazy="selectin")
    creator: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
        lazy="selectin",
    )
    resolver: Mapped["User"] = relationship(
        foreign_keys=[resolved_by_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_adjustments_tenant_closure", "tenant_id", "cash_closure_id"),
        Index("ix_adjustments_tenant_movement", "tenant_id", "movement_id"),
    )

    def __repr__(self) -> str:
        return f"<ClosureAdjustment(id={self.id}, type={self.adjustment_type}, amount={self.amount})>"