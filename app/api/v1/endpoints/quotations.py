from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.dependencies.auth import (
    RequireUsersCreate,
    RequireUsersDelete,
    RequireUsersRead,
    RequireUsersUpdate,
    get_current_tenant_id,
    get_current_user_id,
    set_rls_context,
)
from app.db.session import get_db
from app.schemas.quotations import (
    QuotationCalculationRequest,
    QuotationCalculationsResponse,
    QuotationConvertToTaskRequest,
    QuotationCreate,
    QuotationDuplicateRequest,
    QuotationItemCreate,
    QuotationItemResponse,
    QuotationItemUpdate,
    QuotationListResponse,
    QuotationResponse,
    QuotationStatusUpdate,
    QuotationUpdate,
)
from app.services.quotations_service import QuotationService

router = APIRouter(prefix="/quotations", tags=["Cotizaciones"])


# ============================================================
# CALCULATIONS
# ============================================================

@router.post(
    "/calculate",
    response_model=QuotationCalculationsResponse,
    summary="Calcular totales de cotización (vista previa)",
    dependencies=[Depends(set_rls_context)],
)
async def calculate_quotation(
    request: QuotationCalculationRequest,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Calcular totales de una cotización sin guardarla."""
    service = QuotationService(db)
    return await service.preview_calculation(request)


# ============================================================
# CREATE
# ============================================================

@router.post(
    "/",
    response_model=QuotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva cotización",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_quotation(
    quotation_in: QuotationCreate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear una nueva cotización con sus ítems."""
    service = QuotationService(db)
    return await service.create_quotation(
        quotation_in=quotation_in,
        tenant_id=tenant_id,
        created_by_id=user_id,
    )


# ============================================================
# LIST
# ============================================================

@router.get(
    "/",
    response_model=QuotationListResponse,
    summary="Listar cotizaciones con filtros y paginación",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_quotations(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    status: str | None = Query(None, description="Filtrar por estado: draft, sent, accepted, rejected"),
    customer_id: UUID | None = Query(None, description="Filtrar por cliente"),
    search: str | None = Query(None, description="Buscar por número, título, descripción"),
    sort_by: str = Query("issue_date", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Orden"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de cotizaciones con filtros opcionales."""
    service = QuotationService(db)
    return await service.get_quotations(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status=status,
        customer_id=customer_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ============================================================
# GET
# ============================================================

@router.get(
    "/{quotation_id}",
    response_model=QuotationResponse,
    summary="Obtener una cotización por ID",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_quotation(
    quotation_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener detalles de una cotización específica."""
    service = QuotationService(db)
    quotation = await service.get_quotation(quotation_id, tenant_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


@router.get(
    "/number/{quotation_number}",
    response_model=QuotationResponse,
    summary="Obtener una cotización por número",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_quotation_by_number(
    quotation_number: str,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener una cotización por su número único."""
    service = QuotationService(db)
    quotation = await service.get_quotation_by_number(quotation_number, tenant_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


# ============================================================
# UPDATE
# ============================================================

@router.patch(
    "/{quotation_id}",
    response_model=QuotationResponse,
    summary="Actualizar una cotización (parcial)",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_quotation(
    quotation_id: UUID,
    quotation_in: QuotationUpdate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Actualizar campos de una cotización (solo los campos enviados)."""
    service = QuotationService(db)
    quotation = await service.update_quotation(quotation_id, tenant_id, quotation_in)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


# ============================================================
# ITEMS
# ============================================================

@router.post(
    "/{quotation_id}/items",
    response_model=QuotationItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar ítem a una cotización",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def add_item(
    quotation_id: UUID,
    item_in: "QuotationItemCreate",
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Agregar un ítem a una cotización."""
    from app.services.quotations_service import QuotationService
    
    service = QuotationService(db)
    item = await service.add_item(quotation_id, tenant_id, item_in)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return item


@router.patch(
    "/{quotation_id}/items/{item_id}",
    response_model=QuotationItemResponse,
    summary="Actualizar un ítem de cotización",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_item(
    quotation_id: UUID,
    item_id: UUID,
    item_in: "QuotationItemUpdate",
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Actualizar un ítem de una cotización."""
    from app.services.quotations_service import QuotationService
    
    service = QuotationService(db)
    item = await service.update_item(quotation_id, tenant_id, item_id, item_in)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem no encontrado",
        )
    return item


@router.delete(
    "/{quotation_id}/items/{item_id}",
    summary="Eliminar un ítem de cotización",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def delete_item(
    quotation_id: UUID,
    item_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Eliminar un ítem de una cotización."""
    from app.services.quotations_service import QuotationService
    
    service = QuotationService(db)
    deleted = await service.delete_item(quotation_id, tenant_id, item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem no encontrado",
        )
    return {"message": "Ítem eliminado correctamente", "id": item_id}


# ============================================================
# STATUS CHANGES
# ============================================================

@router.patch(
    "/{quotation_id}/status",
    response_model=QuotationResponse,
    summary="Cambiar estado de una cotización",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_quotation_status(
    quotation_id: UUID,
    status_in: "QuotationStatusUpdate",
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Cambiar el estado de una cotización (draft, sent, accepted, rejected)."""
    from app.services.quotations_service import QuotationService
    
    service = QuotationService(db)
    quotation = await service.update_status(quotation_id, tenant_id, status_in)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


@router.post(
    "/{quotation_id}/send",
    response_model=QuotationResponse,
    summary="Enviar cotización (cambiar a 'sent')",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def send_quotation(
    quotation_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Marcar cotización como enviada."""
    service = QuotationService(db)
    quotation = await service.send_quotation(quotation_id, tenant_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


@router.post(
    "/{quotation_id}/accept",
    response_model=QuotationResponse,
    summary="Aceptar cotización",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def accept_quotation(
    quotation_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Marcar cotización como aceptada."""
    service = QuotationService(db)
    quotation = await service.accept_quotation(quotation_id, tenant_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


@router.post(
    "/{quotation_id}/reject",
    response_model=QuotationResponse,
    summary="Rechazar cotización",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def reject_quotation(
    quotation_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Marcar cotización como rechazada."""
    service = QuotationService(db)
    quotation = await service.reject_quotation(quotation_id, tenant_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


# ============================================================
# DUPLICATE
# ============================================================

@router.post(
    "/{quotation_id}/duplicate",
    response_model=QuotationResponse,
    summary="Duplicar una cotización",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def duplicate_quotation(
    quotation_id: UUID,
    duplicate_in: "QuotationDuplicateRequest",
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Duplicar una cotización existente."""
    from app.services.quotations_service import QuotationService
    
    service = QuotationService(db)
    quotation = await service.duplicate_quotation(
        quotation_id=quotation_id,
        tenant_id=tenant_id,
        duplicate_in=duplicate_in,
        created_by_id=user_id,
    )
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return quotation


# ============================================================
# CONVERT TO TASK
# ============================================================

@router.post(
    "/{quotation_id}/convert-to-task",
    response_model="TaskResponse",
    summary="Convertir cotización aceptada a tarea",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def convert_to_task(
    quotation_id: UUID,
    convert_in: "QuotationConvertToTaskRequest",
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Convertir una cotización aceptada en un trabajo/tarea."""
    from app.services.quotations_service import QuotationService
    
    service = QuotationService(db)
    try:
        task = await service.convert_to_task(
            quotation_id=quotation_id,
            tenant_id=tenant_id,
            convert_in=convert_in,
            created_by_id=user_id,
        )
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cotización no encontrada",
            )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================
# DELETE
# ============================================================

@router.delete(
    "/{quotation_id}",
    summary="Eliminar una cotización",
    dependencies=[Depends(RequireUsersDelete), Depends(set_rls_context)],
)
async def delete_quotation(
    quotation_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Eliminar una cotización permanentemente."""
    service = QuotationService(db)
    deleted = await service.delete_quotation(quotation_id, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotización no encontrada",
        )
    return {"message": "Cotización eliminada correctamente", "id": quotation_id}