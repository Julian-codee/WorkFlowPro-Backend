from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    MessageResponse,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# Dependency to get current user from token
async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    service = AuthService(db)
    try:
        user = await service.get_current_user(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse.model_validate(user)


# Dependency to get current user ID and tenant ID
async def get_current_user_id(
    current_user: UserResponse = Depends(get_current_user),
) -> UUID:
    return current_user.id


async def get_current_tenant_id(
    current_user: UserResponse = Depends(get_current_user),
) -> UUID:
    return current_user.tenant_id


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Registrar un nuevo usuario y crear tenant si no existe."""
    service = AuthService(db)
    try:
        _, _, token = await service.register(user_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return token


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión",
)
async def login(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Autenticar usuario y obtener tokens de acceso."""
    service = AuthService(db)
    try:
        token = await service.login(user_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.post(
    "/refresh",
    response_model=Token,
    summary="Renovar access token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Obtener nuevo access token usando refresh token."""
    service = AuthService(db)
    try:
        token = await service.refresh_token(request.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener usuario actual",
)
async def get_me(
    current_user: UserResponse = Depends(get_current_user),
):
    """Obtener información del usuario autenticado."""
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Actualizar perfil",
)
async def update_me(
    user_in: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar información del usuario autenticado."""
    service = AuthService(db)
    # Get the full user object from DB
    from app.repositories.auth import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.id, current_user.tenant_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    try:
        updated_user = await service.update_me(user, user_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return updated_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Cerrar sesión",
)
async def logout():
    """
    Cerrar sesión (el cliente debe descartar los tokens).
    En una implementación completa, se invalidaría el refresh token en una blocklist.
    """
    return MessageResponse(message="Sesión cerrada correctamente")


# Dependencies for other routers to use
__all__ = ["get_current_tenant_id", "get_current_user", "get_current_user_id", "router"]