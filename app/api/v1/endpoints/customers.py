from datetime import datetime
from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.customers import (
    CustomerFinancialSummary,
    CustomerLegalCreate,
    CustomerListResponse,
    CustomerNaturalCreate,
    CustomerNoteCreate,
    CustomerNoteResponse,
    CustomerNoteUpdate,
    CustomerResponse,
    CustomerSearchFilters,
    CustomerStatusUpdate,
    CustomerUpdate,
)
from app.services.customers_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Clientes"])


# ============================================================
# CREATE
# ============================================================

CustomerCreateUnion = Union[CustomerNaturalCreate, CustomerLegalCreate]


@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo cliente",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_customer(
    customer_in: CustomerCreateUnion,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear un nuevo cliente (persona natural o jurídica)."""
    service = CustomerService(db)
    
    # Extract fields based on customer type for duplicate check
    identification_number = getattr(customer_in, 'identification_number', None)
    tax_id_number = getattr(customer_in, 'tax_id_number', None)
    
    # Check duplicates
    dup_check = await service.check_duplicates(
        tenant_id,
        identification_number=identification_number,
        tax_id_number=tax_id_number,
        email=customer_in.email,
        phone=customer_in.phone,
    )
    
    if dup_check["warnings"]:
        # Return warnings but allow creation (frontend can show them)
        pass
    
    return await service.create_customer(
        customer_in=customer_in,
        tenant_id=tenant_id,
        created_by_id=user_id,
    )


@router.post(
    "/natural",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear persona natural",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_natural_customer(
    customer_in: CustomerNaturalCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear una persona natural (endpoint específico)."""
    service = CustomerService(db)
    return await service.create_customer(
        customer_in=customer_in,
        tenant_id=tenant_id,
        created_by_id=user_id,
    )


@router.post(
    "/legal",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear persona jurídica",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_legal_customer(
    customer_in: CustomerLegalCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear una persona jurídica (endpoint específico)."""
    service = CustomerService(db)
    return await service.create_customer(
        customer_in=customer_in,
        tenant_id=tenant_id,
        created_by_id=user_id,
    )


# ============================================================
# DUPLICATE CHECK
# ============================================================

@router.post(
    "/check-duplicates",
    summary="Verificar duplicados antes de crear",
    dependencies=[Depends(set_rls_context)],
)
async def check_duplicates(
    identification_number: str | None = Query(None),
    tax_id_number: str | None = Query(None),
    email: str | None = Query(None),
    phone: str | None = Query(None),
    exclude_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Verificar posibles duplicados antes de crear un cliente."""
    service = CustomerService(db)
    
    exclude_id_uuid = None
    if exclude_id:
        try:
            exclude_id_uuid = UUID(exclude_id)
        except ValueError:
            pass
    
    return await CustomerService(db).check_duplicates(
        tenant_id,
        identification_number=identification_number,
        tax_id_number=tax_id_number,
        email=email,
        phone=phone,
        exclude_id=exclude_id_uuid,
    )


# ============================================================
# LIST
# ============================================================

@router.get(
    "/",
    response_model=CustomerListResponse,
    summary="Listar clientes con filtros y paginación",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_customers(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    query: str | None = Query(None, description="Búsqueda por nombre, NIT, email, teléfono"),
    customer_type: str | None = Query(None, description="Tipo: natural, legal"),
    status: str | None = Query(None, description="Estado: active, inactive, archived"),
    city: str | None = Query(None, description="Filtrar por ciudad"),
    department: str | None = Query(None, description="Filtrar por departamento"),
    country: str | None = Query(None, description="Filtrar por país"),
    has_active_jobs: bool | None = Query(None, description="Clientes con trabajos activos"),
    has_pending_payments: bool | None = Query(None, description="Clientes con pagos pendientes"),
    has_pending_quotes: bool | None = Query(None, description="Clientes con cotizaciones pendientes"),
    registered_from: datetime | None = Query(None, description="Fecha de registro desde"),
    registered_to: datetime | None = Query(None, description="Fecha de registro hasta"),
    sort_by: str = Query("created_at", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Orden"),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de clientes con filtros opcionales."""
    filters = CustomerSearchFilters(
        query=query,
        customer_type=customer_type,
        status=status,
        city=city,
        department=department,
        country=country,
        has_active_jobs=has_active_jobs,
        has_pending_payments=has_pending_payments,
        has_pending_quotes=has_pending_quotes,
        registered_from=registered_from,
        registered_to=registered_to,
    )
    
    service = CustomerService(db)
    return await service.get_customers(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ============================================================
# GET ONE
# ============================================================

@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Obtener un cliente por ID",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener detalles de un cliente específico."""
    service = CustomerService(db)
    customer = await service.get_customer(customer_id, tenant_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return customer


@router.get(
    "/{customer_id}/full",
    summary="Obtener cliente completo con notas, historial y resumen financiero",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_customer_full(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener cliente completo con notas, historial de auditoría y resumen financiero."""
    service = CustomerService(db)
    full = await service.get_customer_with_summary(customer_id, tenant_id)
    if not full:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return full


@router.get(
    "/{customer_id}/financial",
    response_model=CustomerFinancialSummary,
    summary="Obtener resumen financiero del cliente",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_customer_financial(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener resumen financiero y comercial del cliente."""
    service = CustomerService(db)
    summary = await service.get_financial_summary(customer_id, tenant_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return summary


# ============================================================
# UPDATE
# ============================================================

@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Actualizar un cliente (parcial)",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_customer(
    customer_id: UUID,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Actualizar campos de un cliente (solo los campos enviados)."""
    service = CustomerService(db)
    customer = await service.update_customer(
        customer_id=customer_id,
        tenant_id=tenant_id,
        customer_in=customer_in,
        updated_by_id=user_id,
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return customer


@router.patch(
    "/{customer_id}/status",
    response_model=CustomerResponse,
    summary="Cambiar estado de un cliente",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_customer_status(
    customer_id: UUID,
    status_in: CustomerStatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Cambiar el estado de un cliente (active, inactive, archived)."""
    service = CustomerService(db)
    customer = await service.update_customer_status(
        customer_id=customer_id,
        tenant_id=tenant_id,
        status_in=status_in,
        updated_by_id=user_id,
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return customer


@router.post(
    "/{customer_id}/reactivate",
    response_model=CustomerResponse,
    summary="Reactivar cliente archivado",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def reactivate_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Reactivar un cliente archivado (volver a active)."""
    service = CustomerService(db)
    customer = await service.reactivate_customer(
        customer_id=customer_id,
        tenant_id=tenant_id,
        updated_by_id=user_id,
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado o no está archivado",
        )
    return customer


# ============================================================
# DELETE (Archive)
# ============================================================

@router.delete(
    "/{customer_id}",
    summary="Archivar un cliente (soft delete)",
    dependencies=[Depends(RequireUsersDelete), Depends(set_rls_context)],
)
async def delete_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Archivar un cliente (soft delete - no elimina historial)."""
    service = CustomerService(db)
    deleted = await service.delete_customer(
        customer_id=customer_id,
        tenant_id=tenant_id,
        deleted_by_id=user_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return {"message": "Cliente archivado correctamente", "id": customer_id}


# ============================================================
# NOTES
# ============================================================

@router.post(
    "/{customer_id}/notes",
    response_model=CustomerNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar nota interna a un cliente",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def create_note(
    customer_id: UUID,
    note_in: CustomerNoteCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Agregar una nota interna a un cliente."""
    service = CustomerService(db)
    note = await service.create_note(
        customer_id=customer_id,
        tenant_id=tenant_id,
        note_in=note_in,
        author_id=user_id,
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return note


@router.get(
    "/{customer_id}/notes",
    summary="Listar notas de un cliente",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_notes(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de notas de un cliente."""
    service = CustomerService(db)
    notes, total = await service.get_notes(
        customer_id=customer_id,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
    )
    
    return {
        "notes": notes,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.patch(
    "/{customer_id}/notes/{note_id}",
    response_model=CustomerNoteResponse,
    summary="Actualizar nota de un cliente",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_note(
    customer_id: UUID,
    note_id: UUID,
    note_in: CustomerNoteUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Actualizar una nota de un cliente."""
    service = CustomerService(db)
    note = await service.update_note(
        note_id=note_id,
        customer_id=customer_id,
        tenant_id=tenant_id,
        note_in=note_in,
        updated_by_id=user_id,
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada",
        )
    return note


@router.delete(
    "/{customer_id}/notes/{note_id}",
    summary="Eliminar nota de un cliente",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def delete_note(
    customer_id: UUID,
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Eliminar una nota de un cliente."""
    service = CustomerService(db)
    deleted = await service.delete_note(
        note_id=note_id,
        customer_id=customer_id,
        tenant_id=tenant_id,
        deleted_by_id=user_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada",
        )
    return {"message": "Nota eliminada correctamente", "id": note_id}


# ============================================================
# AUDIT LOGS
# ============================================================

@router.get(
    "/{customer_id}/audit",
    summary="Historial de auditoría de un cliente",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_audit_logs(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener historial de auditoría de un cliente."""
    service = CustomerService(db)
    logs, total = await service.get_audit_logs(
        customer_id=customer_id,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
    )
    
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }