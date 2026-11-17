from datetime import datetime
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
from app.schemas.financial import (
    CashAccountCreate,
    CashAccountListResponse,
    CashAccountResponse,
    CashAccountUpdate,
    CashClosureCreate,
    CashClosureListResponse,
    CashClosureResponse,
    CashClosureSearchFilters,
    CashClosureUpdate,
    ClosureAdjustmentCreate,
    ClosureAdjustmentResponse,
    FinancialMovementCreate,
    FinancialMovementListResponse,
    FinancialMovementResponse,
    FinancialMovementUpdate,
    FinancialSearchFilters,
    MonthlyCalendarResponse,
    WeeklyPeriodCreate,
    WeeklyPeriodListResponse,
    WeeklyPeriodResponse,
    WeeklyPeriodSearchFilters,
    WeeklyPeriodSummary,
    WeeklyPeriodUpdate,
)
from app.services.financial_service import FinancialService

router = APIRouter(prefix="/financial", tags=["Finanzas"])


# ============================================================
# CASH ACCOUNTS
# ============================================================

@router.post(
    "/accounts",
    response_model=CashAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cuenta de dinero",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_cash_account(
    account_in: CashAccountCreate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear una nueva cuenta de dinero (caja, banco, etc.)."""
    service = FinancialService(db)
    try:
        return await service.create_cash_account(
            account_in=account_in,
            tenant_id=tenant_id,
            created_by_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/accounts",
    response_model=CashAccountListResponse,
    summary="Listar cuentas de dinero",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_cash_accounts(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    is_active: bool | None = Query(None, description="Filtrar por estado activo"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de cuentas de dinero."""
    service = FinancialService(db)
    return await service.get_cash_accounts(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
    )


@router.get(
    "/accounts/{account_id}",
    response_model=CashAccountResponse,
    summary="Obtener cuenta de dinero por ID",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_cash_account(
    account_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener detalles de una cuenta de dinero."""
    service = FinancialService(db)
    account = await service.get_cash_account(account_id, tenant_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta de dinero no encontrada",
        )
    return account


@router.patch(
    "/accounts/{account_id}",
    response_model=CashAccountResponse,
    summary="Actualizar cuenta de dinero",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_cash_account(
    account_id: UUID,
    account_in: CashAccountUpdate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Actualizar una cuenta de dinero."""
    service = FinancialService(db)
    account = await service.update_cash_account(account_id, tenant_id, account_in)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta de dinero no encontrada",
        )
    return account


# ============================================================
# FINANCIAL MOVEMENTS
# ============================================================

@router.post(
    "/movements",
    response_model=FinancialMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimiento financiero",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_movement(
    movement_in: FinancialMovementCreate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Registrar un nuevo movimiento financiero (ingreso/egreso)."""
    service = FinancialService(db)
    try:
        return await service.create_movement(
            movement_in=movement_in,
            tenant_id=tenant_id,
            created_by_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/movements",
    response_model=FinancialMovementListResponse,
    summary="Listar movimientos financieros",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_movements(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    query: str | None = Query(None, description="Búsqueda por concepto, cliente"),
    movement_type: str | None = Query(None, description="Tipo: income, expense, transfer"),
    category: str | None = Query(None, description="Categoría"),
    payment_method: str | None = Query(None, description="Método de pago"),
    cash_account_id: UUID | None = Query(None, description="Filtrar por cuenta"),
    customer_id: UUID | None = Query(None, description="Filtrar por cliente"),
    task_id: UUID | None = Query(None, description="Filtrar por tarea"),
    transaction_from: datetime | None = Query(None, description="Fecha de movimiento desde"),
    transaction_to: datetime | None = Query(None, description="Fecha de movimiento hasta"),
    recorded_from: datetime | None = Query(None, description="Fecha de registro desde"),
    recorded_to: datetime | None = Query(None, description="Fecha de registro hasta"),
    is_late_entry: bool | None = Query(None, description="Filtrar registros tardíos"),
    min_amount: float | None = Query(None, description="Monto mínimo"),
    max_amount: float | None = Query(None, description="Monto máximo"),
    sort_by: str = Query("transaction_date", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Orden"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de movimientos con filtros opcionales."""
    service = FinancialService(db)
    filters = FinancialSearchFilters(
        query=query,
        movement_type=movement_type,
        category=category,
        payment_method=payment_method,
        cash_account_id=cash_account_id,
        customer_id=customer_id,
        task_id=task_id,
        transaction_from=transaction_from,
        transaction_to=transaction_to,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
        is_late_entry=is_late_entry,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    return await service.get_movements(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/movements/{movement_id}",
    response_model=FinancialMovementResponse,
    summary="Obtener un movimiento financiero por ID",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_movement(
    movement_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener detalles de un movimiento financiero."""
    service = FinancialService(db)
    movement = await service.get_movement(movement_id, tenant_id)
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        )
    return movement


@router.patch(
    "/movements/{movement_id}",
    response_model=FinancialMovementResponse,
    summary="Actualizar movimiento financiero",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_movement(
    movement_id: UUID,
    movement_in: FinancialMovementUpdate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Actualizar un movimiento financiero."""
    service = FinancialService(db)
    movement = await service.update_movement(movement_id, tenant_id, movement_in)
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        )
    return movement


@router.delete(
    "/movements/{movement_id}",
    summary="Eliminar movimiento financiero",
    dependencies=[Depends(RequireUsersDelete), Depends(set_rls_context)],
)
async def delete_movement(
    movement_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Eliminar un movimiento financiero."""
    service = FinancialService(db)
    deleted = await service.delete_movement(movement_id, tenant_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        )
    return {"message": "Movimiento eliminado correctamente", "id": movement_id}


# ============================================================
# CALENDAR / DAILY SUMMARIES
# ============================================================

@router.get(
    "/calendar/{year}/{month}",
    response_model=MonthlyCalendarResponse,
    summary="Obtener calendario financiero mensual",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_monthly_calendar(
    year: int,
    month: int,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener calendario financiero mensual con totales diarios."""
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mes inválido (1-12)",
        )
    if year < 2020 or year > 2100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Año inválido",
        )

    service = FinancialService(db)
    return await service.get_monthly_calendar(tenant_id=tenant_id, year=year, month=month)


@router.get(
    "/daily-summary",
    summary="Obtener resumen diario para un rango de fechas",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_daily_summary(
    start_date: datetime = Query(..., description="Fecha inicio"),
    end_date: datetime = Query(..., description="Fecha fin"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener resumen diario para un rango de fechas."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de inicio debe ser anterior a la fecha de fin",
        )

    service = FinancialService(db)
    from app.repositories.financial import FinancialMovementRepository
    FinancialMovementRepository(db)
    daily_summaries = await service.movement_repo.get_daily_summaries(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {"daily_summaries": daily_summaries}


# ============================================================
# WEEKLY PERIODS
# ============================================================

@router.post(
    "/periods",
    response_model=WeeklyPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear período semanal",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_weekly_period(
    period_in: WeeklyPeriodCreate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear un nuevo período semanal."""
    service = FinancialService(db)
    try:
        return await service.create_weekly_period(
            period_in=period_in,
            tenant_id=tenant_id,
            created_by_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/periods/current",
    response_model=WeeklyPeriodResponse,
    summary="Obtener período actual (o crear si no existe)",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_current_period(
    cash_account_id: UUID = Query(..., description="ID de la cuenta de dinero"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Obtener el período semanal actual para una cuenta."""
    service = FinancialService(db)
    return await service.get_current_period(
        tenant_id=tenant_id,
        cash_account_id=cash_account_id,
        created_by_id=user_id,
    )


@router.get(
    "/periods",
    response_model=WeeklyPeriodListResponse,
    summary="Listar períodos semanales",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_weekly_periods(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    status: str | None = Query(None, description="Estado: open, closing, closed, adjusted"),
    cash_account_id: UUID | None = Query(None, description="Filtrar por cuenta"),
    year: int | None = Query(None, description="Filtrar por año"),
    week_number: int | None = Query(None, description="Filtrar por número de semana"),
    start_from: datetime | None = Query(None, description="Fecha inicio desde"),
    start_to: datetime | None = Query(None, description="Fecha inicio hasta"),
    end_from: datetime | None = Query(None, description="Fecha fin desde"),
    end_to: datetime | None = Query(None, description="Fecha fin hasta"),
    sort_by: str = Query("start_date", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Orden"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de períodos semanales con filtros."""
    service = FinancialService(db)
    filters = WeeklyPeriodSearchFilters(
        status=status,
        cash_account_id=cash_account_id,
        year=year,
        week_number=week_number,
        start_from=start_from,
        start_to=start_to,
        end_from=end_from,
        end_to=end_to,
    )
    return await service.get_weekly_periods(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/periods/{period_id}",
    response_model=WeeklyPeriodResponse,
    summary="Obtener un período semanal por ID",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_weekly_period(
    period_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener detalles de un período semanal."""
    service = FinancialService(db)
    period = await service.get_weekly_period(period_id, tenant_id)
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Período no encontrado",
        )
    return period


@router.patch(
    "/periods/{period_id}",
    response_model=WeeklyPeriodResponse,
    summary="Actualizar período semanal",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_weekly_period(
    period_id: UUID,
    period_in: WeeklyPeriodUpdate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Actualizar un período semanal."""
    service = FinancialService(db)
    period = await service.period_repo.get_by_id(period_id, tenant_id)
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Período no encontrado",
        )
    updated = await service.period_repo.update(period, **period_in.model_dump(exclude_unset=True))
    return WeeklyPeriodResponse.model_validate(updated)


@router.post(
    "/periods/{period_id}/close",
    response_model=WeeklyPeriodResponse,
    summary="Cerrar período semanal",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def close_weekly_period(
    period_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Cerrar un período semanal."""
    service = FinancialService(db)
    period = await service.close_weekly_period(period_id, tenant_id, user_id)
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Período no encontrado",
        )
    return period


# ============================================================
# CASH CLOSURES
# ============================================================

@router.post(
    "/closures",
    response_model=CashClosureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cierre de caja semanal",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_cash_closure(
    closure_in: CashClosureCreate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Crear un cierre de caja para un período semanal cerrado."""
    service = FinancialService(db)
    try:
        return await service.create_cash_closure(
            closure_in=closure_in,
            tenant_id=tenant_id,
            closed_by_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/closures",
    response_model=CashClosureListResponse,
    summary="Listar cierres de caja",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_cash_closures(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    status: str | None = Query(None, description="Estado: pending, confirmed, adjusted, disputed"),
    cash_account_id: UUID | None = Query(None, description="Filtrar por cuenta"),
    closed_from: datetime | None = Query(None, description="Fecha de cierre desde"),
    closed_to: datetime | None = Query(None, description="Fecha de cierre hasta"),
    discrepancy_from: float | None = Query(None, description="Diferencia mínima"),
    discrepancy_to: float | None = Query(None, description="Diferencia máxima"),
    sort_by: str = Query("confirmed_at", description="Campo de ordenación"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Orden"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener lista paginada de cierres de caja."""
    service = FinancialService(db)
    filters = CashClosureSearchFilters(
        status=status,
        cash_account_id=cash_account_id,
        closed_from=closed_from,
        closed_to=closed_to,
        discrepancy_from=discrepancy_from,
        discrepancy_to=discrepancy_to,
    )
    return await service.get_cash_closures(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/closures/{closure_id}",
    response_model=CashClosureResponse,
    summary="Obtener un cierre de caja por ID",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_cash_closure(
    closure_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener detalles de un cierre de caja."""
    service = FinancialService(db)
    closure = await service.get_cash_closure(closure_id, tenant_id)
    if not closure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cierre no encontrado",
        )
    return closure


@router.get(
    "/closures/by-period/{period_id}",
    response_model=CashClosureResponse,
    summary="Obtener cierre por período",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_cash_closure_by_period(
    period_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener cierre de caja por período semanal."""
    service = FinancialService(db)
    closure = await service.get_cash_closure_by_period(period_id, tenant_id)
    if not closure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cierre no encontrado para este período",
        )
    return closure


@router.patch(
    "/closures/{closure_id}",
    response_model=CashClosureResponse,
    summary="Actualizar cierre de caja",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def update_cash_closure(
    closure_id: UUID,
    closure_in: CashClosureUpdate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Actualizar un cierre de caja (solo si está pendiente)."""
    service = FinancialService(db)
    closure = await service.update_cash_closure(closure_id, tenant_id, closure_in)
    if not closure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cierre no encontrado",
        )
    return closure


@router.post(
    "/closures/{closure_id}/confirm",
    response_model=CashClosureResponse,
    summary="Confirmar cierre de caja",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def confirm_cash_closure(
    closure_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Confirmar un cierre de caja (cambiar estado a confirmed)."""
    service = FinancialService(db)
    closure = await service.confirm_cash_closure(closure_id, tenant_id, user_id)
    if not closure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cierre no encontrado",
        )
    return closure


# ============================================================
# ADJUSTMENTS (Late entries)
# ============================================================

@router.post(
    "/closures/{closure_id}/adjustments",
    response_model=ClosureAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar ajuste en cierre (movimiento tardío)",
    dependencies=[Depends(RequireUsersCreate), Depends(set_rls_context)],
)
async def create_adjustment(
    closure_id: UUID,
    adjustment_in: ClosureAdjustmentCreate,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Registrar un ajuste en un cierre (movimiento tardío, corrección, etc.)."""
    service = FinancialService(db)
    try:
        return await service.create_adjustment(
            adjustment_in=adjustment_in,
            tenant_id=tenant_id,
            created_by_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/closures/{closure_id}/adjustments",
    summary="Listar ajustes de un cierre",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def list_adjustments(
    closure_id: UUID,
    movement_id: UUID | None = Query(None, description="Filtrar por movimiento"),
    adjustment_type: str | None = Query(None, description="Tipo: late_income, late_expense, correction, discrepancy"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener ajustes de un cierre."""
    service = FinancialService(db)
    adjustments, total = await service.get_adjustments(
        tenant_id=tenant_id,
        cash_closure_id=closure_id,
        movement_id=movement_id,
        adjustment_type=adjustment_type,
        page=page,
        page_size=page_size,
    )
    return {
        "adjustments": adjustments,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.patch(
    "/adjustments/{adjustment_id}",
    response_model=ClosureAdjustmentResponse,
    summary="Resolver ajuste",
    dependencies=[Depends(RequireUsersUpdate), Depends(set_rls_context)],
)
async def resolve_adjustment(
    adjustment_id: UUID,
    resolution: str = Query(..., description="Resolución del ajuste"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
):
    """Resolver un ajuste (marcar como revisado/resuelto)."""
    service = FinancialService(db)
    adjustment = await service.resolve_adjustment(
        adjustment_id=adjustment_id,
        tenant_id=tenant_id,
        resolution=resolution,
        resolved_by_id=user_id,
    )
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ajuste no encontrado",
        )
    return adjustment


# ============================================================
# WEEKLY PERIOD SUMMARY
# ============================================================

@router.get(
    "/periods/{period_id}/summary",
    response_model=WeeklyPeriodSummary,
    summary="Obtener resumen completo de período (movimientos, cierre, ajustes)",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_period_summary(
    period_id: UUID,
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener resumen completo de un período semanal."""
    service = FinancialService(db)
    summary = await service.get_weekly_period_summary(period_id, tenant_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Período no encontrado",
        )
    return summary


# ============================================================
# CLOSURE HISTORY
# ============================================================

@router.get(
    "/closures-history",
    response_model=CashClosureListResponse,
    summary="Historial de cierres de caja",
    dependencies=[Depends(RequireUsersRead), Depends(set_rls_context)],
)
async def get_closure_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    cash_account_id: UUID | None = Query(None),
    closed_from: datetime | None = Query(None),
    closed_to: datetime | None = Query(None),
    discrepancy_from: float | None = Query(None),
    discrepancy_to: float | None = Query(None),
    sort_by: str = Query("confirmed_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Obtener historial de cierres de caja con filtros."""
    service = FinancialService(db)
    filters = CashClosureSearchFilters(
        status=status,
        cash_account_id=cash_account_id,
        closed_from=closed_from,
        closed_to=closed_to,
        discrepancy_from=discrepancy_from,
        discrepancy_to=discrepancy_to,
    )
    return await service.get_closure_history(
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
    )