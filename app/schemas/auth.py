from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email del usuario")
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$", description="Nombre de usuario")
    full_name: str | None = Field(None, max_length=255, description="Nombre completo")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña")
    tenant_slug: str | None = Field(None, description="Slug del tenant (opcional, crea uno nuevo si no existe)")


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., description="Contraseña")


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    full_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    avatar_url: str | None = Field(None, max_length=500)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_superuser: bool
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del tenant")
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$", description="Slug único")
    description: str | None = None


class TenantCreate(TenantBase):
    pass


class TenantResponse(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    settings: dict
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    sub: UUID  # user_id
    tenant_id: UUID
    username: str
    is_superuser: bool
    exp: int
    type: str  # "access" or "refresh"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class MessageResponse(BaseModel):
    message: str