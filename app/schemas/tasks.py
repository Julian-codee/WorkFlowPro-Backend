from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    NO_PAYMENTS = "no_payments"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Título de la tarea")
    description: str | None = Field(None, description="Descripción detallada")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Prioridad")
    due_date: datetime | None = Field(None, description="Fecha límite (UTC)")
    assignee_id: UUID | None = Field(None, description="ID del usuario asignado")
    customer_id: UUID | None = Field(None, description="ID del cliente")
    # Información financiera
    total_price: Decimal | None = Field(None, ge=Decimal(0), description="Precio total del trabajo")
    total_paid: Decimal = Field(default=Decimal(0), ge=Decimal(0), description="Total abonado")
    pending_balance: Decimal = Field(default=Decimal(0), ge=Decimal(0), description="Saldo pendiente")
    payment_status: PaymentStatus = Field(default=PaymentStatus.NO_PAYMENTS, description="Estado del pago")
    last_payment_date: datetime | None = Field(None, description="Fecha del último pago")


class TaskCreate(TaskBase):
    # Campos para abono inicial (opcional)
    initial_payment_amount: Decimal | None = Field(None, ge=Decimal(0), description="Monto del abono inicial")
    initial_payment_date: datetime | None = Field(None, description="Fecha del abono inicial")
    initial_payment_method: str | None = Field(None, description="Método de pago inicial")
    initial_payment_account_id: UUID | None = Field(None, description="ID de la cuenta financiera receptora")
    initial_payment_reference: str | None = Field(None, description="Referencia o comprobante del pago inicial")
    initial_payment_notes: str | None = Field(None, description="Observaciones del pago inicial")


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    assignee_id: UUID | None = None
    customer_id: UUID | None = None
    total_price: Decimal | None = Field(None, ge=Decimal(0), description="Precio total del trabajo")


class TaskStatusUpdate(BaseModel):
    status: TaskStatus = Field(..., description="Nuevo estado de la tarea")


class TaskPriorityUpdate(BaseModel):
    priority: TaskPriority = Field(..., description="Nueva prioridad")


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: TaskStatus
    tenant_id: UUID
    created_by_id: UUID
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Indicadores financieros adicionales para el frontend
    has_pending_balance: bool = Field(default=False, description="Indica si tiene saldo pendiente > 0")


class TaskListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskDeleteResponse(BaseModel):
    message: str = "Tarea eliminada correctamente"
    id: UUID


# ============================================================
# TASK PAYMENT SCHEMAS
# ============================================================

class TaskPaymentCreate(BaseModel):
    """Registrar un nuevo abono/pago a una tarea"""
    amount: Decimal = Field(..., gt=Decimal(0), description="Monto del pago")
    transaction_date: datetime = Field(..., description="Fecha real del pago")
    cash_account_id: UUID = Field(..., description="ID de la cuenta financiera receptora")
    payment_method: str = Field(..., description="Método de pago")
    reference: str | None = Field(None, max_length=255, description="Referencia o comprobante")
    notes: str | None = Field(None, description="Observaciones")


class TaskPaymentResponse(BaseModel):
    """Respuesta de un pago de tarea (basado en movimiento financiero)"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    amount: Decimal
    transaction_date: datetime
    recorded_at: datetime
    cash_account_id: UUID
    cash_account_name: str | None = None
    payment_method: str
    concept: str
    description: str | None = None
    reference: str | None = None
    created_by_id: UUID
    created_by_name: str | None = None
    is_late_entry: bool
    status: str


class TaskPaymentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payments: list[TaskPaymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# PENDING PAYMENTS SCHEMAS
# ============================================================

class PendingPaymentTaskResponse(BaseModel):
    """Tarea con saldo pendiente para la vista de Pagos Pendientes"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None = None
    # Información del cliente
    customer_id: UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    # Información financiera
    total_price: Decimal | None
    total_paid: Decimal
    pending_balance: Decimal
    payment_status: PaymentStatus
    last_payment_date: datetime | None = None
    # Fechas
    created_at: datetime
    completed_at: datetime | None = None
    updated_at: datetime


class PendingPaymentsFilters(BaseModel):
    customer_id: UUID | None = None
    status: TaskStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    min_pending_balance: Decimal | None = None
    max_pending_balance: Decimal | None = None
    only_active: bool = Field(default=False, description="Solo tareas no finalizadas")
    only_completed: bool = Field(default=False, description="Solo tareas finalizadas")
    search: str | None = None


class PendingPaymentsListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tasks: list[PendingPaymentTaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int