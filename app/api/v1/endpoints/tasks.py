from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_tenant_id, get_current_user_id
from app.db.session import get_db
from app.models.tasks import TaskPriority, TaskStatus
from app.schemas.tasks import (
    TaskCreate,
    TaskDeleteResponse,
    TaskListResponse,
    TaskPriorityUpdate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.tasks_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tareas"])


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva tarea",
)
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear una nueva tarea en el tenant actual."""
    service = TaskService(db)
    return await service.create_task(
        task_in=task_in,
        tenant_id=tenant_id,
        created_by_id=user_id,
    )


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="Listar tareas con filtros y paginación",
)
async def list_tasks(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    status: TaskStatus | None = Query(None, description="Filtrar por estado"),
    priority: TaskPriority | None = Query(None, description="Filtrar por prioridad"),
    assignee_id: UUID | None = Query(None, description="Filtrar por asignado"),
    search: str | None = Query(None, description="Buscar en título y descripción"),
    sort_by: str = Query("created_at", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Orden"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de tareas con filtros opcionales."""
    service = TaskService(db)
    return await service.get_tasks(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Obtener una tarea por ID",
)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener detalles de una tarea específica."""
    service = TaskService(db)
    task = await service.get_task(task_id, tenant_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Actualizar una tarea (parcial)",
)
async def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Actualizar campos de una tarea (solo los campos enviados)."""
    service = TaskService(db)
    task = await service.update_task(task_id, tenant_id, task_in)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )
    return task


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
    summary="Cambiar estado de una tarea",
)
async def update_task_status(
    task_id: UUID,
    status_in: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Cambiar el estado de una tarea (pending, in_progress, in_review, completed, cancelled)."""
    service = TaskService(db)
    task = await service.update_task_status(task_id, tenant_id, status_in)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )
    return task


@router.patch(
    "/{task_id}/priority",
    response_model=TaskResponse,
    summary="Cambiar prioridad de una tarea",
)
async def update_task_priority(
    task_id: UUID,
    priority_in: TaskPriorityUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Cambiar la prioridad de una tarea (low, medium, high, urgent)."""
    service = TaskService(db)
    task = await service.update_task_priority(task_id, tenant_id, priority_in)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )
    return task


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
    summary="Eliminar una tarea",
)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Eliminar una tarea permanentemente."""
    service = TaskService(db)
    deleted = await service.delete_task(task_id, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )
    return TaskDeleteResponse(id=task_id)