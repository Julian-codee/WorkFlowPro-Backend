from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.roles import Permission, UserRole, user_has_permission
from app.repositories.auth import UserRepository
from app.schemas.auth import UserResponse
from app.services.auth_service import AuthService, decode_token


# ============================================================
# JWT Token Dependencies
# ============================================================

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Extraer y validar el usuario actual desde el token JWT."""
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


async def get_current_user_id(
    current_user: UserResponse = Depends(get_current_user),
) -> UUID:
    """Obtener el ID del usuario actual."""
    return current_user.id


async def get_current_tenant_id(
    current_user: UserResponse = Depends(get_current_user),
) -> UUID:
    """Obtener el tenant_id del usuario actual."""
    return current_user.tenant_id


async def get_current_user_roles(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserRole]:
    """Obtener los roles del usuario en su tenant actual."""
    from app.models.user import User
    from app.models.user_tenant_role import UserTenantRole
    from sqlalchemy import select
    
    # Cargar usuario con sus roles
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.id, current_user.tenant_id)
    
    if not user:
        return []
    
    return user.get_roles_in_tenant(current_user.tenant_id)


# ============================================================
# Permission Dependencies
# ============================================================

class RequirePermission:
    """
    Dependency para requerir un permiso específico.
    
    Uso:
        @router.get("/tasks/", dependencies=[Depends(RequirePermission(Permission.TASKS_READ))])
        async def list_tasks(...):
            ...
    """
    
    def __init__(self, permission: Permission):
        self.permission = permission
    
    async def __call__(
        self,
        current_user: UserResponse = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserResponse:
        from app.models.user import User
        from app.models.user_tenant_role import UserTenantRole
        from sqlalchemy import select
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(current_user.id, current_user.tenant_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Superuser bypass
        if user.is_superuser:
            return current_user
        
        roles = user.get_roles_in_tenant(current_user.tenant_id)
        
        if not user_has_permission(roles, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.permission.value} required",
            )
        
        return current_user


class RequireRole:
    """
    Dependency para requerir uno de los roles especificados.
    
    Uso:
        @router.delete("/users/{id}", dependencies=[Depends(RequireRole(UserRole.ADMIN))])
        async def delete_user(...):
            ...
    """
    
    def __init__(self, *roles: UserRole):
        self.roles = set(roles)
    
    async def __call__(
        self,
        current_user: UserResponse = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserResponse:
        from app.models.user import User
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(current_user.id, current_user.tenant_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Superuser bypass
        if user.is_superuser:
            return current_user
        
        user_roles = set(user.get_roles_in_tenant(current_user.tenant_id))
        
        if not user_roles.intersection(self.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: one of {[r.value for r in self.roles]}",
            )
        
        return current_user


# ============================================================
# RLS Context Dependency (sets app.current_tenant_id, etc.)
# ============================================================

async def set_rls_context(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Configurar el contexto RLS para la sesión de base de datos actual.
    Debe llamarse en endpoints que necesiten aislamiento multi-tenant.
    """
    # Use set_config function which supports parameters
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :val, true)"),
        {"val": str(current_user.tenant_id)}
    )
    await db.execute(
        text("SELECT set_config('app.current_user_id', :val, true)"),
        {"val": str(current_user.id)}
    )
    await db.execute(
        text("SELECT set_config('app.current_is_superuser', :val, true)"),
        {"val": str(current_user.is_superuser).lower()}
    )
    return current_user

# ============================================================
# Convenience dependencies
# ============================================================

# Common permission dependencies
RequireTasksRead = RequirePermission(Permission.TASKS_READ)
RequireTasksCreate = RequirePermission(Permission.TASKS_CREATE)
RequireTasksUpdate = RequirePermission(Permission.TASKS_UPDATE)
RequireTasksDelete = RequirePermission(Permission.TASKS_DELETE)
RequireTasksAssign = RequirePermission(Permission.TASKS_ASSIGN)
RequireTasksStatus = RequirePermission(Permission.TASKS_STATUS)
RequireTasksPriority = RequirePermission(Permission.TASKS_PRIORITY)

RequireUsersRead = RequirePermission(Permission.USERS_READ)
RequireUsersCreate = RequirePermission(Permission.USERS_CREATE)
RequireUsersUpdate = RequirePermission(Permission.USERS_UPDATE)
RequireUsersDelete = RequirePermission(Permission.USERS_DELETE)

RequireTenantsRead = RequirePermission(Permission.TENANTS_READ)
RequireTenantsCreate = RequirePermission(Permission.TENANTS_CREATE)
RequireTenantsUpdate = RequirePermission(Permission.TENANTS_UPDATE)
RequireTenantsDelete = RequirePermission(Permission.TENANTS_DELETE)

RequireRolesManage = RequirePermission(Permission.ROLES_MANAGE)

RequireReportsRead = RequirePermission(Permission.REPORTS_READ)
RequireReportsExport = RequirePermission(Permission.REPORTS_EXPORT)

# Role-based dependencies
RequireAdmin = RequireRole(UserRole.ADMIN)
RequireOperatorOrAdmin = RequireRole(UserRole.OPERATOR, UserRole.ADMIN)
RequireCommercialOrAdmin = RequireRole(UserRole.COMMERCIAL, UserRole.ADMIN)
RequireAnyRole = RequireRole(UserRole.ADMIN, UserRole.OPERATOR, UserRole.COMMERCIAL, UserRole.VIEWER)