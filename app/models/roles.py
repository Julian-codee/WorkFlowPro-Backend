from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.tenant import Tenant


class UserRole(str, enum.Enum):
    """Roles de usuario dentro de un tenant"""
    ADMIN = "admin"           # Acceso total al tenant
    OPERATOR = "operator"     # Gestión operativa (tasks, proyectos)
    COMMERCIAL = "commercial" # Ventas, clientes, cotizaciones
    VIEWER = "viewer"         # Solo lectura


class Permission(str, enum.Enum):
    """Permisos granulares"""
    # Users
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    
    # Tenants
    TENANTS_CREATE = "tenants:create"
    TENANTS_READ = "tenants:read"
    TENANTS_UPDATE = "tenants:update"
    TENANTS_DELETE = "tenants:delete"
    
    # Tasks
    TASKS_CREATE = "tasks:create"
    TASKS_READ = "tasks:read"
    TASKS_UPDATE = "tasks:update"
    TASKS_DELETE = "tasks:delete"
    TASKS_ASSIGN = "tasks:assign"
    TASKS_STATUS = "tasks:status"
    TASKS_PRIORITY = "tasks:priority"
    
    # Roles
    ROLES_MANAGE = "roles:manage"
    
    # Reports
    REPORTS_READ = "reports:read"
    REPORTS_EXPORT = "reports:export"


# Mapeo Role -> Permissions
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        Permission.USERS_CREATE, Permission.USERS_READ, Permission.USERS_UPDATE, Permission.USERS_DELETE,
        Permission.TENANTS_CREATE, Permission.TENANTS_READ, Permission.TENANTS_UPDATE, Permission.TENANTS_DELETE,
        Permission.TASKS_CREATE, Permission.TASKS_READ, Permission.TASKS_UPDATE, Permission.TASKS_DELETE,
        Permission.TASKS_ASSIGN, Permission.TASKS_STATUS, Permission.TASKS_PRIORITY,
        Permission.ROLES_MANAGE,
        Permission.REPORTS_READ, Permission.REPORTS_EXPORT,
    },
    UserRole.OPERATOR: {
        Permission.USERS_READ,
        Permission.TASKS_CREATE, Permission.TASKS_READ, Permission.TASKS_UPDATE,
        Permission.TASKS_ASSIGN, Permission.TASKS_STATUS, Permission.TASKS_PRIORITY,
        Permission.REPORTS_READ,
    },
    UserRole.COMMERCIAL: {
        Permission.USERS_READ,
        Permission.TASKS_READ, Permission.TASKS_UPDATE,
        Permission.TASKS_STATUS,
        Permission.REPORTS_READ, Permission.REPORTS_EXPORT,
    },
    UserRole.VIEWER: {
        Permission.USERS_READ,
        Permission.TASKS_READ,
        Permission.REPORTS_READ,
    },
}


def get_permissions_for_role(role: UserRole) -> set[Permission]:
    """Obtener permisos para un rol"""
    return ROLE_PERMISSIONS.get(role, set())


def user_has_permission(user_roles: list[UserRole], permission: Permission) -> bool:
    """Verificar si el usuario tiene un permiso (cualquiera de sus roles)"""
    for role in user_roles:
        if permission in ROLE_PERMISSIONS.get(role, set()):
            return True
    return False