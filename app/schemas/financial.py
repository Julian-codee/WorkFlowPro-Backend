from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================
# ENUMS
# ============================================================

class MovementType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class MovementCategory(str, Enum):
    SALES = "sales"
    SERVICES = "services"
    PRODUCTS = "products"
    RENT = "rent"
    UTILITIES = "utilities"
    PAYROLL = "payroll"
    SUPPLIES = "supplies"
    MARKETING = "marketing"
    TRANSPORT = "transport"
    MAINTENANCE = "maintenance"
    TAXES = "taxes"
    LOANS = "loans"
    INVESTMENTS = "investments"
    OTHER_INCOME = "other_income"
    OTHER_EXPENSE = "other_expense"


class PaymentMethod(str, Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    CHECK = "check"
    DIGITAL_WALLET = "digital_wallet"
    CRYPTO = "crypto"
    OTHER = "other"


class WeeklyPeriodStatus(str, Enum):
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    ADJUSTED = "adjusted"


class CashClosureStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ADJUSTED = "adjusted"
    DISPUTED = "disputed"


class AdjustmentType(str, Enum):
    LATE_INCOME = "late_income"
    LATE_EXPENSE = "late_expense"
    CORRECTION = "correction"
    DISCREPANCY = "discrepancy"


# ============================================================
# CASH ACCOUNT SCHEMAS
# ============================================================

class CashAccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la cuenta")
    code: str = Field(..., min_length=1, max_length=20, description="Código único")
    description: str | None = Field(None, description="Descripción")
    account_type: str = Field(default="cash", max_length=50, description="Tipo de cuenta")
    currency: str = Field(default="COP", max_length=3, description="Moneda")
    is_active: bool = Field(default=True)


class CashAccountCreate(CashAccountBase):
    pass


class CashAccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    account_type: str | None = Field(None, max_length=50)
    currency: str | None = Field(None, max_length=3)
    is_active: bool | None = None


class CashAccountResponse(CashAccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    current_balance: Decimal
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================
# FINANCIAL MOVEMENT SCHEMAS
# ============================================================

class FinancialMovementBase(BaseModel):
    transaction_date: datetime = Field(..., description="Fecha real del movimiento")
    movement_type: MovementType = Field(..., description="Tipo de movimiento")
    category: MovementCategory = Field(..., description="Categoría")
    amount: Decimal = Field(..., gt=Decimal(0), description="Monto")
    payment_method: PaymentMethod = Field(..., description="Método de pago")
    cash_account_id: UUID = Field(..., description="ID de la cuenta de dinero")
    concept: str = Field(..., min_length=1, max_length=255, description="Concepto")
    description: str | None = Field(None, description="Descripción")
    customer_id: UUID | None = Field(None, description="ID del cliente")
    task_id: UUID | None = Field(None, description="ID de la tarea")
    quotation_id: UUID | None = Field(None, description="ID de la cotización")
    is_late_entry: bool = Field(default=False, description="Es registro tardío")
    late_entry_reason: str | None = Field(None, description="Justificación de registro tardío")


class FinancialMovementCreate(FinancialMovementBase):
    pass


class FinancialMovementUpdate(BaseModel):
    transaction_date: datetime | None = None
    movement_type: MovementType | None = None
    category: MovementCategory | None = None
    amount: Decimal | None = Field(None, gt=Decimal(0))
    payment_method: PaymentMethod | None = None
    cash_account_id: UUID | None = None
    concept: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    customer_id: UUID | None = None
    task_id: UUID | None = None
    quotation_id: UUID | None = None
    is_late_entry: bool | None = None
    late_entry_reason: str | None = None


class FinancialMovementResponse(FinancialMovementBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recorded_at: datetime
    is_late_entry: bool
    late_entry_reason: str | None = None
    late_entry_approved_by: UUID | None = None
    weekly_period_id: UUID | None = None
    tenant_id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime


class FinancialMovementListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movements: list[FinancialMovementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# CASH ACCOUNT SCHEMAS
# ============================================================

class CashAccountListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    accounts: list[CashAccountResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# WEEKLY PERIOD SCHEMAS
# ============================================================

class WeeklyPeriodBase(BaseModel):
    week_number: int = Field(..., ge=1, le=53, description="Número de semana (1-53)")
    year: int = Field(..., ge=2020, le=2100, description="Año")
    start_date: datetime = Field(..., description="Fecha de inicio")
    end_date: datetime = Field(..., description="Fecha de fin")
    cash_account_id: UUID = Field(..., description="ID de la cuenta de dinero")


class WeeklyPeriodCreate(WeeklyPeriodBase):
    opening_balance: Decimal = Field(default=Decimal(0), description="Saldo de apertura")


class WeeklyPeriodUpdate(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str | None = None
    opening_balance: Decimal | None = None
    total_income: Decimal | None = None
    total_expense: Decimal | None = None
    net_flow: Decimal | None = None
    expected_balance: Decimal | None = None


class WeeklyPeriodResponse(WeeklyPeriodBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    net_flow: Decimal
    expected_balance: Decimal
    closed_at: datetime | None = None
    closed_by_id: UUID | None = None
    tenant_id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime


class WeeklyPeriodListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    periods: list[WeeklyPeriodResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# CASH CLOSURE SCHEMAS
# ============================================================

class CashClosureBase(BaseModel):
    weekly_period_id: UUID = Field(..., description="ID del período semanal")
    cash_account_id: UUID = Field(..., description="ID de la cuenta de dinero")
    opening_balance: Decimal = Field(..., description="Saldo de apertura")
    total_income: Decimal = Field(default=Decimal(0), description="Total de ingresos")
    total_expense: Decimal = Field(default=Decimal(0), description="Total de egresos")
    net_flow: Decimal = Field(default=Decimal(0), description="Flujo neto")
    expected_balance: Decimal = Field(..., description="Saldo esperado")
    physical_balance: Decimal = Field(..., description="Saldo físico contado")
    discrepancy: Decimal = Field(default=Decimal(0), description="Diferencia")
    observations: str | None = None
    discrepancy_explanation: str | None = None


class CashClosureCreate(CashClosureBase):
    pass


class CashClosureUpdate(BaseModel):
    physical_balance: Decimal | None = None
    discrepancy_explanation: str | None = None
    observations: str | None = None


class CashClosureResponse(CashClosureBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    net_flow: Decimal
    expected_balance: Decimal
    discrepancy: Decimal
    status: str
    closed_by_id: UUID
    confirmed_at: datetime
    adjustment_count: int
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class CashClosureListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    closures: list[CashClosureResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# CLOSURE ADJUSTMENT SCHEMAS
# ============================================================

class ClosureAdjustmentBase(BaseModel):
    cash_closure_id: UUID = Field(..., description="ID del cierre afectado")
    movement_id: UUID = Field(..., description="ID del movimiento causante")
    adjustment_type: str = Field(..., description="Tipo de ajuste")
    amount: Decimal = Field(..., description="Monto del ajuste")
    impact_on_balance: Decimal = Field(..., description="Impacto en el saldo")
    reason: str = Field(..., min_length=1, description="Justificación")
    resolution: str | None = None


class ClosureAdjustmentCreate(ClosureAdjustmentBase):
    pass


class ClosureAdjustmentUpdate(BaseModel):
    resolution: str | None = None
    resolved_by_id: UUID | None = None


class ClosureAdjustmentResponse(ClosureAdjustmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resolved_by_id: UUID | None = None
    resolved_at: datetime | None = None
    tenant_id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================
# CALENDAR & DAILY SUMMARY SCHEMAS
# ============================================================

class DailySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: datetime
    total_income: Decimal
    total_expense: Decimal
    net_flow: Decimal
    movement_count: int
    weekly_period_id: UUID | None = None
    weekly_period_status: str | None = None


class MonthlyCalendarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int
    month: int
    days: list[DailySummary]
    total_income: Decimal
    total_expense: Decimal
    net_flow: Decimal
    total_movements: int


class WeeklyPeriodSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: WeeklyPeriodResponse
    cash_closure: dict | None = None
    total_adjustments: int = 0
    daily_summaries: list[DailySummary]


# ============================================================
# SEARCH & FILTER SCHEMAS
# ============================================================

class FinancialSearchFilters(BaseModel):
    query: str | None = Field(None, description="Búsqueda por concepto, cliente")
    movement_type: str | None = None
    category: str | None = None
    payment_method: str | None = None
    cash_account_id: UUID | None = None
    customer_id: UUID | None = None
    task_id: UUID | None = None
    transaction_from: datetime | None = None
    transaction_to: datetime | None = None
    recorded_from: datetime | None = None
    recorded_to: datetime | None = None
    is_late_entry: bool | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None


class WeeklyPeriodSearchFilters(BaseModel):
    status: str | None = None
    cash_account_id: UUID | None = None
    year: int | None = None
    week_number: int | None = None
    start_from: datetime | None = None
    start_to: datetime | None = None
    end_from: datetime | None = None
    end_to: datetime | None = None


class CashClosureSearchFilters(BaseModel):
    status: str | None = None
    cash_account_id: UUID | None = None
    closed_from: datetime | None = None
    closed_to: datetime | None = None
    discrepancy_from: Decimal | None = None
    discrepancy_to: Decimal | None = None


class AdjustmentSearchFilters(BaseModel):
    adjustment_type: str | None = None
    cash_closure_id: UUID | None = None
    movement_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None