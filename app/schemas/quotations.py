from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuotationStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class QuotationItemType(str, Enum):
    PRODUCT = "product"
    SERVICE = "service"
    LABOR = "labor"
    EXPENSE = "expense"


# ============================================================
# ITEM SCHEMAS
# ============================================================

class QuotationItemBase(BaseModel):
    item_type: QuotationItemType = Field(..., description="Tipo de ítem")
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del ítem")
    description: str | None = Field(None, description="Descripción")
    sku: str | None = Field(None, max_length=100, description="SKU/Código")
    quantity: Decimal = Field(default=Decimal(1), ge=Decimal("0.001"), description="Cantidad")
    unit: str = Field(default="unidad", max_length=50, description="Unidad de medida")
    unit_cost: Decimal = Field(default=Decimal(0), ge=Decimal(0), description="Costo unitario")
    unit_price: Decimal = Field(default=Decimal(0), ge=Decimal(0), description="Precio unitario de venta")
    discount_percent: Decimal = Field(default=Decimal(0), ge=Decimal(0), le=Decimal(100), description="Descuento %")
    extra_data: dict = Field(default_factory=dict, description="Metadatos adicionales")


class QuotationItemCreate(QuotationItemBase):
    sort_order: int = Field(default=0, ge=0)


class QuotationItemUpdate(BaseModel):
    item_type: QuotationItemType | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    sku: str | None = Field(None, max_length=100)
    quantity: Decimal | None = Field(None, ge=Decimal("0.001"))
    unit: str | None = Field(None, max_length=50)
    unit_cost: Decimal | None = Field(None, ge=Decimal(0))
    unit_price: Decimal | None = Field(None, ge=Decimal(0))
    discount_percent: Decimal | None = Field(None, ge=Decimal(0), le=Decimal(100))
    extra_data: dict | None = None
    sort_order: int | None = Field(None, ge=0)


class QuotationItemResponse(QuotationItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    quotation_id: UUID
    sort_order: int
    discount_amount: Decimal
    line_subtotal: Decimal
    line_total: Decimal
    created_at: datetime
    updated_at: datetime


# ============================================================
# QUOTATION SCHEMAS
# ============================================================

class QuotationBase(BaseModel):
    customer_id: UUID = Field(..., description="ID del cliente")
    issue_date: datetime = Field(default_factory=datetime.utcnow, description="Fecha de emisión")
    expiry_date: datetime = Field(..., description="Fecha de vencimiento")
    title: str = Field(..., min_length=1, max_length=255, description="Título del proyecto")
    description: str | None = None
    observations: str | None = None
    payment_terms: str | None = Field(None, max_length=500)
    delivery_terms: str | None = Field(None, max_length=500)
    warranty_terms: str | None = Field(None, max_length=500)
    profit_margin: Decimal = Field(default=Decimal(0), ge=Decimal(0), le=Decimal(100))


class QuotationCreate(QuotationBase):
    items: list["QuotationItemCreate"] = Field(default_factory=list, description="Ítems de la cotización")


class QuotationUpdate(BaseModel):
    customer_id: UUID | None = None
    issue_date: datetime | None = None
    expiry_date: datetime | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    observations: str | None = None
    payment_terms: str | None = Field(None, max_length=500)
    delivery_terms: str | None = Field(None, max_length=500)
    warranty_terms: str | None = Field(None, max_length=500)
    profit_margin: Decimal | None = Field(None, ge=Decimal(0), le=Decimal(100))
    status: Optional["QuotationStatus"] = None


class QuotationStatusUpdate(BaseModel):
    status: QuotationStatus = Field(..., description="Nuevo estado")


class QuotationDuplicateRequest(BaseModel):
    new_customer_id: UUID | None = None
    new_expiry_date: datetime | None = None
    new_title: str | None = None


class QuotationConvertToTaskRequest(BaseModel):
    task_title: str | None = None
    task_description: str | None = None
    task_priority: str | None = "medium"
    assignee_id: UUID | None = None


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class QuotationResponse(QuotationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    quotation_number: str
    status: QuotationStatus
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    tenant_id: UUID
    created_by_id: UUID
    converted_task_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    
    # Relaciones opcionales
    customer: Optional["CustomerResponse"] = None
    creator: Optional["UserResponse"] = None
    items: list["QuotationItemResponse"] = Field(default_factory=list)
    converted_task: Optional["TaskResponse"] = None


class QuotationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    quotations: list[QuotationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class QuotationCalculationsResponse(BaseModel):
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    profit_margin: Decimal
    items_count: int
    total_cost: Decimal
    gross_profit: Decimal


# ============================================================
# CALCULATION SCHEMAS
# ============================================================

class QuotationCalculationRequest(BaseModel):
    items: list[QuotationItemCreate]
    profit_margin: Decimal = Field(default=Decimal(0), ge=Decimal(0), le=Decimal(100))
    tax_rate: Decimal = Field(default=Decimal(19), ge=Decimal(0), le=Decimal(100))
    discount_amount: Decimal = Field(default=Decimal(0), ge=Decimal(0))


# Forward references for circular imports
from app.schemas.auth import UserResponse
from app.schemas.customers import CustomerResponse
from app.schemas.tasks import TaskResponse

QuotationCreate.model_rebuild()
QuotationResponse.model_rebuild()