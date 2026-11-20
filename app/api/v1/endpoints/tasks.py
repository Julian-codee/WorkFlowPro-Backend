from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import (
    RequireTasksCreate,
    RequireTasksDelete,
    RequireTasksPriority,
    RequireTasksRead,
    RequireTasksStatus,
    RequireTasksUpdate,
    set_rls_context,
)
from app.db.session import get_db
from app.models.tasks import TaskPriority, TaskStatus
from app.schemas.tasks import (
    PendingPaymentsFilters,
    PendingPaymentsListResponse,
    TaskCreate,
    TaskDeleteResponse,
    TaskListResponse,
    TaskPaymentCreate,
    TaskPaymentListResponse,
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
    dependencies=[Depends(RequireTasksCreate), Depends(set_rls_context)],
)
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva tarea en el tenant actual.
    
    Permite establecer precio total y registrar un abono inicial opcional.
    """
    service = TaskService(db)
    try:
        return await service.create_task(task_in=task_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="Listar tareas con filtros y paginación",
    dependencies=[Depends(RequireTasksRead), Depends(set_rls_context)],
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
):
    """Obtener lista paginada de tareas con filtros opcionales.
    
    Incluye información financiera: precio total, total abonado, saldo pendiente, estado de pago.
    """
    service = TaskService(db)
    return await service.get_tasks(
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
    dependencies=[Depends(RequireTasksRead), Depends(set_rls_context)],
)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtener detalles de una tarea específica con información financiera completa."""
    service = TaskService(db)
    task = await service.get_task(task_id)
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
    dependencies=[Depends(RequireTasksUpdate), Depends(set_rls_context)],
)
async def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Actualizar campos de una tarea (solo los campos enviados).
    
    Permite modificar el precio total con validaciones:
    - No puede ser inferior al total pagado
    - Recalcula automáticamente saldo pendiente y estado de pago
    """
    service = TaskService(db)
    try:
        task = await service.update_task(task_id, task_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
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
    dependencies=[Depends(RequireTasksStatus), Depends(set_rls_context)],
)
async def update_task_status(
    task_id: UUID,
    status_in: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Cambiar el estado de una tarea (pending, in_progress, in_review, completed, cancelled).
    
    El estado operativo y el estado financiero son independientes.
    Finalizar una tarea no genera ingresos ni cancela deudas.
    """
    service = TaskService(db)
    task = await service.update_task_status(task_id, status_in)
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
    dependencies=[Depends(RequireTasksPriority), Depends(set_rls_context)],
)
async def update_task_priority(
    task_id: UUID,
    priority_in: TaskPriorityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Cambiar la prioridad de una tarea (low, medium, high, urgent)."""
    service = TaskService(db)
    task = await service.update_task_priority(task_id, priority_in)
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
    dependencies=[Depends(RequireTasksDelete), Depends(set_rls_context)],
)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una tarea permanentemente.
    
    No elimina el historial financiero asociado (movimientos de ingreso).
    """
    service = TaskService(db)
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )
    return TaskDeleteResponse(id=task_id)


# ============================================================
# PAGOS DE TAREAS
# ============================================================

@router.post(
    "/{task_id}/payments",
    response_model=TaskPaymentListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo abono/pago a una tarea",
    dependencies=[Depends(RequireTasksCreate), Depends(set_rls_context)],
)
async def add_task_payment(
    task_id: UUID,
    payment_in: TaskPaymentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Registrar un nuevo pago/abono a una tarea.
    
    Crea automáticamente un movimiento de ingreso en Finanzas vinculado a la tarea.
    Actualiza total abonado, saldo pendiente y estado de pago.
    
    Validaciones:
    - No permite pagos superiores al saldo pendiente
    - Valida que la cuenta financiera pertenezca al mismo tenant
    - Requiere método de pago y fecha
    """
    service = TaskService(db)
    try:
        payment = await service.add_payment(task_id, payment_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return TaskPaymentListResponse(
        payments=[payment],
        total=1,
        page=1,
        page_size=1,
        total_pages=1,
    )


@router.get(
    "/{task_id}/payments",
    response_model=TaskPaymentListResponse,
    summary="Obtener historial de pagos de una tarea",
    dependencies=[Depends(RequireTasksRead), Depends(set_rls_context)],
)
async def get_task_payments(
    task_id: UUID,
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: AsyncSession = Depends(get_db),
):
    """Obtener el historial completo de pagos de una tarea.
    
    Consulta los movimientos financieros existentes vinculados a la tarea.
    Incluye: monto, fecha, cuenta receptora, método de pago, usuario responsable, estado.
    """
    service = TaskService(db)
    try:
        return await service.get_task_payments(task_id, page=page, page_size=page_size)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================
# PAGOS PENDIENTES
# ============================================================

@router.get(
    "/pending-payments",
    response_model=PendingPaymentsListResponse,
    summary="Listar tareas con saldo pendiente (Pagos pendientes)",
    dependencies=[Depends(RequireTasksRead), Depends(set_rls_context)],
)
async def get_pending_payments(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    customer_id: UUID | None = Query(None, description="Filtrar por cliente"),
    status: TaskStatus | None = Query(None, description="Filtrar por estado operativo"),
    date_from: str | None = Query(None, description="Fecha creación desde (ISO 8601)"),
    date_to: str | None = Query(None, description="Fecha creación hasta (ISO 8601)"),
    min_pending_balance: float | None = Query(None, description="Saldo pendiente mínimo"),
    max_pending_balance: float | None = Query(None, description="Saldo pendiente máximo"),
    only_active: bool = Query(False, description="Solo tareas no finalizadas"),
    only_completed: bool = Query(False, description="Solo tareas finalizadas"),
    search: str | None = Query(None, description="Buscar en título, descripción o cliente"),
    sort_by: str = Query("created_at", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Orden"),
    db: AsyncSession = Depends(get_db),
):
    """Obtener todas las tareas con saldo pendiente mayor que cero.
    
    Incluye tareas activas y finalizadas que tengan deuda.
    Cuando el saldo llega a cero, la tarea desaparece automáticamente de esta lista.
    
    Filtros disponibles:
    - customer_id: Filtrar por cliente
    - status: Filtrar por estado operativo
    - date_from/date_to: Rango de fechas de creación
    - min_pending_balance/max_pending_balance: Rango de saldo pendiente
    - only_active: Solo tareas no finalizadas
    - only_completed: Solo tareas finalizadas
    - search: Búsqueda en título, descripción o nombre de cliente
    """
    from datetime import datetime
    
    service = TaskService(db)
    
    # Parsear fechas si se proporcionan
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de fecha inválido para date_from. Use ISO 8601."
            )
    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de fecha inválido para date_to. Use ISO 8601."
            )
    
    filters = PendingPaymentsFilters(
        customer_id=customer_id,
        status=status,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        min_pending_balance=min_pending_balance,
        max_pending_balance=max_pending_balance,
        only_active=only_active,
        only_completed=only_completed,
        search=search,
    )
    
    return await service.get_pending_payments(
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )