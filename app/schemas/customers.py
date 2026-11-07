from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerType(str, Enum):
    NATURAL = "natural"
    LEGAL = "legal"


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class IdentificationType(str, Enum):
    CC = "cc"
    CE = "ce"
    PASSPORT = "passport"
    NIT = "nit"
    NIT_LEGAL = "nit_legal"
    RUT = "rut"


# ============================================================
# BASE SCHEMAS
# ============================================================

class CustomerBase(BaseModel):
    """Campos base compartidos"""
    customer_type: CustomerType = Field(..., description="Tipo de cliente")
    status: CustomerStatus = Field(default=CustomerStatus.ACTIVE, description="Estado administrativo")
    
    # Contacto
    phone: str = Field(..., min_length=5, max_length=30, description="Teléfono principal")
    phone_secondary: str | None = Field(None, max_length=30, description="Teléfono secundario")
    whatsapp: str | None = Field(None, max_length=30, description="WhatsApp")
    email: EmailStr | None = Field(None, description="Correo electrónico")
    
    # Dirección
    address: str | None = Field(None, description="Dirección")
    city: str | None = Field(None, max_length=100, description="Ciudad")
    department: str | None = Field(None, max_length=100, description="Departamento")
    country: str | None = Field(default="Colombia", max_length=100, description="País")
    postal_code: str | None = Field(None, max_length=20, description="Código postal")
    
    # Observaciones internas
    internal_notes: str | None = Field(None, description="Observaciones internas")


class CustomerNaturalBase(CustomerBase):
    """Campos específicos para persona natural"""
    customer_type: CustomerType = Field(default=CustomerType.NATURAL, frozen=True)
    
    first_name: str = Field(..., min_length=1, max_length=100, description="Nombres")
    last_name: str = Field(..., min_length=1, max_length=100, description="Apellidos")
    identification_type: IdentificationType = Field(default=IdentificationType.CC, description="Tipo de identificación")
    identification_number: str = Field(..., min_length=5, max_length=50, description="Número de identificación")


class CustomerLegalBase(CustomerBase):
    """Campos específicos para persona jurídica"""
    customer_type: CustomerType = Field(default=CustomerType.LEGAL, frozen=True)
    
    business_name: str = Field(..., min_length=1, max_length=255, description="Razón social")
    trade_name: str | None = Field(None, max_length=255, description="Nombre comercial")
    tax_id_type: IdentificationType = Field(default=IdentificationType.NIT_LEGAL, description="Tipo de identificación fiscal")
    tax_id_number: str = Field(..., min_length=5, max_length=50, description="NIT o identificación fiscal")
    verification_digit: str | None = Field(None, max_length=5, description="Dígito de verificación")
    
    legal_rep_name: str | None = Field(None, max_length=200, description="Nombre del representante legal")
    legal_rep_id: str | None = Field(None, max_length=50, description="Identificación del representante legal")
    main_contact_name: str | None = Field(None, max_length=200, description="Nombre del contacto principal")
    
    fiscal_address: str | None = Field(None, description="Dirección fiscal")
    commercial_address: str | None = Field(None, description="Dirección comercial")
    website: str | None = Field(None, max_length=500, description="Sitio web")
    economic_activity: str | None = Field(None, max_length=255, description="Actividad económica")


# ============================================================
# CREATE SCHEMAS
# ============================================================

class CustomerCreate(CustomerBase):
    """Para crear un cliente - el tipo determina campos requeridos"""


class CustomerNaturalCreate(CustomerNaturalBase):
    """Crear persona natural"""


class CustomerLegalCreate(CustomerLegalBase):
    """Crear persona jurídica"""


# ============================================================
# UPDATE SCHEMAS
# ============================================================

class CustomerUpdate(BaseModel):
    """Actualización parcial de cliente"""
    status: CustomerStatus | None = None
    
    phone: str | None = Field(None, min_length=5, max_length=30)
    phone_secondary: str | None = Field(None, max_length=30)
    whatsapp: str | None = Field(None, max_length=30)
    email: EmailStr | None = None
    
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    
    internal_notes: str | None = None
    
    # Natural
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    identification_type: IdentificationType | None = None
    identification_number: str | None = Field(None, min_length=5, max_length=50)
    
    # Legal
    business_name: str | None = Field(None, min_length=1, max_length=255)
    trade_name: str | None = Field(None, max_length=255)
    tax_id_type: IdentificationType | None = None
    tax_id_number: str | None = Field(None, min_length=5, max_length=50)
    verification_digit: str | None = Field(None, max_length=5)
    
    legal_rep_name: str | None = Field(None, max_length=200)
    legal_rep_id: str | None = Field(None, max_length=50)
    main_contact_name: str | None = Field(None, max_length=200)
    
    fiscal_address: str | None = None
    commercial_address: str | None = None
    website: str | None = Field(None, max_length=500)
    economic_activity: str | None = Field(None, max_length=255)


class CustomerStatusUpdate(BaseModel):
    status: CustomerStatus = Field(..., description="Nuevo estado administrativo")


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    customer_type: CustomerType
    status: CustomerStatus
    tenant_id: UUID
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Natural fields
    first_name: str | None = None
    last_name: str | None = None
    identification_type: IdentificationType | None = None
    identification_number: str | None = None
    
    # Legal fields
    business_name: str | None = None
    trade_name: str | None = None
    tax_id_type: IdentificationType | None = None
    tax_id_number: str | None = None
    verification_digit: str | None = None
    legal_rep_name: str | None = None
    legal_rep_id: str | None = None
    main_contact_name: str | None = None
    fiscal_address: str | None = None
    commercial_address: str | None = None
    website: str | None = None
    economic_activity: str | None = None
    
    # Computed properties
    full_name: str
    display_name: str


class CustomerListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    customers: list[CustomerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# FINANCIAL SUMMARY
# ============================================================

class CustomerFinancialSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    total_contracted: Decimal = Decimal(0)
    total_invoiced: Decimal = Decimal(0)
    total_paid: Decimal = Decimal(0)
    pending_balance: Decimal = Decimal(0)
    
    jobs_count: int = 0
    active_jobs_count: int = 0
    completed_jobs_count: int = 0
    
    pending_quotes_count: int = 0
    last_transaction_at: datetime | None = None
    last_job_at: datetime | None = None


class CustomerCommercialSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    customer: CustomerResponse
    financial: CustomerFinancialSummary
    recent_jobs: list[dict] = []
    recent_quotes: list[dict] = []
    recent_payments: list[dict] = []


# ============================================================
# CUSTOMER NOTES
# ============================================================

class CustomerNoteBase(BaseModel):
    content: str = Field(..., min_length=1, description="Contenido de la nota")


class CustomerNoteCreate(CustomerNoteBase):
    pass


class CustomerNoteUpdate(BaseModel):
    content: str | None = Field(None, min_length=1)


class CustomerNoteResponse(CustomerNoteBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    customer_id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================
# AUDIT LOG
# ============================================================

class CustomerAuditAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    IDENTIFICATION_CHANGED = "identification_changed"
    STATUS_CHANGED = "status_changed"
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"
    ARCHIVED = "archived"


class CustomerAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    action: CustomerAuditAction
    old_data: dict | None = None
    new_data: dict | None = None
    changed_fields: list[str] | None = None
    customer_id: UUID
    user_id: UUID
    created_at: datetime


# ============================================================
# SEARCH & FILTERS
# ============================================================

class CustomerSearchFilters(BaseModel):
    query: str | None = Field(None, description="Búsqueda por nombre, NIT, email, teléfono")
    customer_type: CustomerType | None = None
    status: CustomerStatus | None = None
    city: str | None = None
    department: str | None = None
    country: str | None = None
    has_active_jobs: bool | None = None
    has_pending_payments: bool | None = None
    has_pending_quotes: bool | None = None
    registered_from: datetime | None = None
    registered_to: datetime | None = None


class CustomerSortOptions(str):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    BUSINESS_NAME = "business_name"
    TRADE_NAME = "trade_name"
    IDENTIFICATION_NUMBER = "identification_number"
    TAX_ID_NUMBER = "tax_id_number"
    CITY = "city"
    STATUS = "status"