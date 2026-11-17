from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.models.financial import (
    CashAccount,
)
from app.repositories.financial import (
    CashAccountRepository,
    CashClosureRepository,
    ClosureAdjustmentRepository,
    FinancialMovementRepository,
    WeeklyPeriodRepository,
)
from app.schemas.financial import (
    CashAccountCreate,
    CashAccountListResponse,
    CashAccountResponse,
    CashAccountUpdate,
    CashClosureCreate,
    CashClosureListResponse,
    CashClosureSearchFilters,
    CashClosureUpdate,
    ClosureAdjustmentCreate,
    ClosureAdjustmentResponse,
    DailySummary,
    FinancialMovementCreate,
    FinancialMovementListResponse,
    FinancialMovementResponse,
    FinancialMovementUpdate,
    FinancialSearchFilters,
    MonthlyCalendarResponse,
    WeeklyPeriodCreate,
    WeeklyPeriodListResponse,
    WeeklyPeriodSearchFilters,
    WeeklyPeriodSummary,
)
from app.schemas.financial import (
    CashClosureResponse as SchemaCashClosureResponse,
)
from app.schemas.financial import (
    WeeklyPeriodResponse as SchemaWeeklyPeriodResponse,
)


class FinancialService:
    def __init__(self, db):
        self.movement_repo = FinancialMovementRepository(db)
        self.period_repo = WeeklyPeriodRepository(db)
        self.account_repo = CashAccountRepository(db)
        self.closure_repo = CashClosureRepository(db)
        self.adjustment_repo = ClosureAdjustmentRepository(db)
        self.db = db

    # ============================================================
    # CASH ACCOUNTS
    # ============================================================
    async def create_cash_account(
        self,
        *,
        account_in: CashAccountCreate,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> CashAccountResponse:
        # Verificar código único
        existing = await self.account_repo.get_by_code(account_in.code, tenant_id)
        if existing:
            raise ValueError("El código de cuenta ya existe")

        account = await self.account_repo.create(
            name=account_in.name,
            code=account_in.code,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            description=account_in.description,
            account_type=account_in.account_type,
            currency=account_in.currency,
            is_active=account_in.is_active,
        )
        return CashAccountResponse.model_validate(account)

    async def get_cash_account(self, account_id: UUID, tenant_id: UUID) -> CashAccountResponse | None:
        account = await self.account_repo.get_by_id(account_id, tenant_id)
        if not account:
            return None
        return CashAccountResponse.model_validate(account)

    async def get_cash_accounts(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> CashAccountListResponse:
        accounts, total = await self.account_repo.get_all(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            is_active=is_active,
        )
        total_pages = (total + page_size - 1) // page_size
        return CashAccountListResponse(
            accounts=[CashAccountResponse.model_validate(a) for a in accounts],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_cash_account(
        self,
        account_id: UUID,
        tenant_id: UUID,
        account_in: CashAccountUpdate,
    ) -> CashAccountResponse | None:
        account = await self.account_repo.get_by_id(account_id, tenant_id)
        if not account:
            return None

        if account_in.name is not None:
            account.name = account_in.name
        if account_in.description is not None:
            account.description = account_in.description
        if account_in.account_type is not None:
            account.account_type = account_in.account_type
        if account_in.currency is not None:
            account.currency = account_in.currency
        if account_in.is_active is not None:
            account.is_active = account_in.is_active

        await self.db.flush()
        await self.db.refresh(account)
        return CashAccountResponse.model_validate(account)

    # ============================================================
    # FINANCIAL MOVEMENTS
    # ============================================================
    async def create_movement(
        self,
        *,
        movement_in: FinancialMovementCreate,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> FinancialMovementResponse:
        # Validar cuenta de dinero
        cash_account = await self.account_repo.get_by_id(movement_in.cash_account_id, tenant_id)
        if not cash_account:
            raise ValueError("Cuenta de dinero no encontrada")

        if not cash_account.is_active:
            raise ValueError("La cuenta de dinero no está activa")

        # Verificar si es registro tardío
        is_late = movement_in.is_late_entry
        late_reason = movement_in.late_entry_reason

        if movement_in.transaction_date.date() < datetime.utcnow().date() - timedelta(days=1):
            is_late = True
            if not late_reason:
                raise ValueError("Los movimientos de fechas anteriores requieren justificación")

        movement = await self.movement_repo.create(
            transaction_date=movement_in.transaction_date,
            movement_type=movement_in.movement_type,
            category=movement_in.category,
            amount=movement_in.amount,
            payment_method=movement_in.payment_method,
            cash_account_id=movement_in.cash_account_id,
            concept=movement_in.concept,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            description=movement_in.description,
            customer_id=movement_in.customer_id,
            task_id=movement_in.task_id,
            quotation_id=movement_in.quotation_id,
            is_late_entry=is_late,
            late_entry_reason=late_reason,
        )

        # Actualizar saldo de la cuenta
        if movement.movement_type == "income":
            new_balance = movement.cash_account.current_balance + movement.amount
        elif movement.movement_type == "expense":
            new_balance = movement.cash_account.current_balance - movement.amount
        else:
            new_balance = movement.cash_account.current_balance

        await self.account_repo.update_balance(movement.cash_account, new_balance)

        return FinancialMovementResponse.model_validate(movement)

    async def get_movement(self, movement_id: UUID, tenant_id: UUID) -> FinancialMovementResponse | None:
        movement = await self.movement_repo.get_by_id(movement_id, tenant_id)
        if not movement:
            return None
        return FinancialMovementResponse.model_validate(movement)

    async def get_movements(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "transaction_date",
        sort_order: str = "desc",
    ) -> FinancialMovementListResponse:
        filter_obj = None
        if filters:
            filter_obj = FinancialSearchFilters(
                query=getattr(filters, 'query', None),
                movement_type=getattr(filters, 'movement_type', None),
                category=getattr(filters, 'category', None),
                payment_method=getattr(filters, 'payment_method', None),
                cash_account_id=getattr(filters, 'cash_account_id', None),
                customer_id=getattr(filters, 'customer_id', None),
                task_id=getattr(filters, 'task_id', None),
                transaction_from=getattr(filters, 'transaction_from', None),
                transaction_to=getattr(filters, 'transaction_to', None),
                recorded_from=getattr(filters, 'recorded_from', None),
                recorded_to=getattr(filters, 'recorded_to', None),
                is_late_entry=getattr(filters, 'is_late_entry', None),
                min_amount=getattr(filters, 'min_amount', None),
                max_amount=getattr(filters, 'max_amount', None),
            )

        movements, total = await self.movement_repo.get_all(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            filters=filter_obj,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total + page_size - 1) // page_size

        return FinancialMovementListResponse(
            movements=[FinancialMovementResponse.model_validate(m) for m in movements],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_movement(
        self,
        movement_id: UUID,
        tenant_id: UUID,
        movement_in: FinancialMovementUpdate,
    ) -> FinancialMovementResponse | None:
        movement = await self.movement_repo.get_by_id(movement_id, tenant_id)
        if not movement:
            return None

        # Si cambia el monto, ajustar saldo de la cuenta
        old_amount = movement.amount
        old_type = movement.movement_type

        updated = await self.movement_repo.update(
            movement,
            transaction_date=movement_in.transaction_date,
            movement_type=movement_in.movement_type.value if movement_in.movement_type else None,
            category=movement_in.category.value if movement_in.category else None,
            amount=movement_in.amount,
            payment_method=movement_in.payment_method.value if movement_in.payment_method else None,
            cash_account_id=movement_in.cash_account_id,
            concept=movement_in.concept,
            description=movement_in.description,
            customer_id=movement_in.customer_id,
            task_id=movement_in.task_id,
            quotation_id=movement_in.quotation_id,
            is_late_entry=movement_in.is_late_entry,
            late_entry_reason=movement_in.late_entry_reason,
        )

        # Recalcular saldo de la cuenta si cambió el monto o tipo
        if movement_in.amount is not None or movement_in.movement_type is not None:
            new_type = movement_in.movement_type.value if movement_in.movement_type else old_type
            new_amount = movement_in.amount if movement_in.amount is not None else old_amount

            # Revertir efecto anterior
            if old_type == "income":
                new_balance = movement.cash_account.current_balance - old_amount
            elif old_type == "expense":
                new_balance = movement.cash_account.current_balance + old_amount
            else:
                new_balance = movement.cash_account.current_balance

            # Aplicar nuevo efecto
            if new_type == "income":
                new_balance += new_amount
            elif new_type == "expense":
                new_balance -= new_amount

            await self.movement_repo.db.execute(
                select(CashAccount).where(CashAccount.id == movement.cash_account_id)
            )
            # Actualizar balance
            cash_account = await self.account_repo.get_by_id(movement.cash_account_id, movement.tenant_id)
            if cash_account:
                await self.account_repo.update_balance(cash_account, new_balance)

        return FinancialMovementResponse.model_validate(updated)

    async def delete_movement(self, movement_id: UUID, tenant_id: UUID) -> bool:
        movement = await self.movement_repo.get_by_id(movement_id, tenant_id)
        if not movement:
            return False

        # Revertir efecto en saldo
        if movement.movement_type == "income":
            new_balance = movement.cash_account.current_balance - movement.amount
        elif movement.movement_type == "expense":
            new_balance = movement.cash_account.current_balance + movement.amount
        else:
            new_balance = movement.cash_account.current_balance

        await self.account_repo.update_balance(movement.cash_account, new_balance)

        await self.movement_repo.db.delete(movement)
        await self.movement_repo.db.flush()
        return True

    # ============================================================
    # CALENDAR / DAILY SUMMARIES
    # ============================================================
    async def get_monthly_calendar(
        self,
        tenant_id: UUID,
        year: int,
        month: int,
    ) -> MonthlyCalendarResponse:
        # Obtener totales mensuales
        await self.movement_repo.get_monthly_totals(tenant_id, year, month)

        # Obtener resúmenes diarios
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

        daily_summaries = await self.movement_repo.get_daily_summaries(
            tenant_id, start_date, end_date
        )

        # Obtener períodos semanales para el mes
        from app.repositories.financial import WeeklyPeriodRepository
        WeeklyPeriodRepository(self.db)
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

        # Obtener todos los períodos que intersectan con el mes
        periods, _ = await self.period_repo.get_all(
            tenant_id=tenant_id,
            filters=WeeklyPeriodSearchFilters(
                start_from=datetime(year, month, 1),
                end_to=end_date,
            ),
            page=1,
            page_size=100,
        )

        # Mapear períodos a días
        period_map = {}
        for period in periods:
            for day in range((period.end_date - period.start_date).days + 1):
                day_date = period.start_date + timedelta(days=day)
                if day_date.year == year and day_date.month == month:
                    period_map[day_date.date()] = period

        # Construir días
        days = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.month == month:
                day_summary = next(
                    (d for d in daily_summaries if d["date"].date() == current_date.date()),
                    {"total_income": Decimal(0), "total_expense": Decimal(0), "net_flow": Decimal(0), "movement_count": 0}
                )

                period = period_map.get(current_date.date())
                days.append(DailySummary(
                    date=current_date,
                    total_income=day_summary["total_income"],
                    total_expense=day_summary["total_expense"],
                    net_flow=day_summary["net_flow"],
                    movement_count=day_summary["movement_count"],
                    weekly_period_id=period.id if period else None,
                    weekly_period_status=period.status if period else None,
                ))
            current_date += timedelta(days=1)

        return MonthlyCalendarResponse(
            year=year,
            month=month,
            days=days,
            total_income=sum(d.total_income for d in days),
            total_expense=sum(d.total_expense for d in days),
            net_flow=sum(d.net_flow for d in days),
            total_movements=sum(d.movement_count for d in days),
        )

    # ============================================================
    # WEEKLY PERIODS
    # ============================================================
    async def create_weekly_period(
        self,
        period_in: WeeklyPeriodCreate,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> SchemaWeeklyPeriodResponse:
        # Verificar que la cuenta existe
        account = await self.account_repo.get_by_id(period_in.cash_account_id, tenant_id)
        if not account:
            raise ValueError("Cuenta de dinero no encontrada")

        period = await self.period_repo.create(
            week_number=period_in.week_number,
            year=period_in.year,
            start_date=period_in.start_date,
            end_date=period_in.end_date,
            cash_account_id=period_in.cash_account_id,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            opening_balance=period_in.opening_balance,
        )
        return SchemaWeeklyPeriodResponse.model_validate(period)

    async def get_weekly_period(
        self,
        period_id: UUID,
        tenant_id: UUID,
    ) -> SchemaWeeklyPeriodResponse | None:
        period = await self.period_repo.get_by_id(period_id, tenant_id)
        if not period:
            return None
        return SchemaWeeklyPeriodResponse.model_validate(period)

    async def get_current_period(
        self,
        tenant_id: UUID,
        cash_account_id: UUID,
        date: datetime | None = None,
        created_by_id: UUID | None = None,
    ) -> SchemaWeeklyPeriodResponse:
        period = await self.period_repo.get_or_create_current_period(
            tenant_id=tenant_id,
            cash_account_id=cash_account_id,
            created_by_id=created_by_id,
        )
        return SchemaWeeklyPeriodResponse.model_validate(period)

    async def get_weekly_periods(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "start_date",
        sort_order: str = "desc",
    ) -> WeeklyPeriodListResponse:
        filter_obj = None
        if filters:
            filter_obj = WeeklyPeriodSearchFilters(
                status=getattr(filters, 'status', None),
                cash_account_id=getattr(filters, 'cash_account_id', None),
                year=getattr(filters, 'year', None),
                week_number=getattr(filters, 'week_number', None),
                start_from=getattr(filters, 'start_from', None),
                start_to=getattr(filters, 'start_to', None),
                end_from=getattr(filters, 'end_from', None),
                end_to=getattr(filters, 'end_to', None),
            )

        periods, total = await self.period_repo.get_all(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            filters=filter_obj,
        )

        total_pages = (total + page_size - 1) // page_size

        return WeeklyPeriodListResponse(
            periods=[SchemaWeeklyPeriodResponse.model_validate(p) for p in periods],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def close_weekly_period(
        self,
        period_id: UUID,
        tenant_id: UUID,
        closed_by_id: UUID,
    ) -> SchemaWeeklyPeriodResponse | None:
        period = await self.period_repo.get_by_id(period_id, tenant_id)
        if not period:
            return None

        period = await self.period_repo.close_period(period, closed_by_id)
        return SchemaWeeklyPeriodResponse.model_validate(period)

    # ============================================================
    # CASH CLOSURES
    # ============================================================
    async def create_cash_closure(
        self,
        closure_in: CashClosureCreate,
        tenant_id: UUID,
        closed_by_id: UUID,
    ) -> SchemaCashClosureResponse:
        # Verificar que el período existe y está cerrado
        period = await self.period_repo.get_by_id(closure_in.weekly_period_id, tenant_id)
        if not period:
            raise ValueError("Período semanal no encontrado")

        if period.status != "closed":
            raise ValueError("El período debe estar cerrado antes de hacer el cierre de caja")

        if period.cash_account_id != closure_in.cash_account_id:
            raise ValueError("La cuenta de dinero no coincide con la del período")

        # Calcular totales del período
        calc = await self.period_repo.calculate_totals(closure_in.weekly_period_id, tenant_id)

        # Verificar que los valores coinciden
        if closure_in.total_income != calc["total_income"]:
            raise ValueError("El total de ingresos no coincide con el cálculo del período")
        if closure_in.total_expense != calc["total_expense"]:
            raise ValueError("El total de egresos no coincide con el cálculo del período")

        closure = await self.closure_repo.create(
            weekly_period_id=closure_in.weekly_period_id,
            cash_account_id=closure_in.cash_account_id,
            tenant_id=tenant_id,
            closed_by_id=closed_by_id,
            opening_balance=closure_in.opening_balance,
            total_income=closure_in.total_income,
            total_expense=closure_in.total_expense,
            net_flow=closure_in.net_flow,
            expected_balance=closure_in.expected_balance,
            physical_balance=closure_in.physical_balance,
            discrepancy=closure_in.discrepancy,
            observations=closure_in.observations,
            discrepancy_explanation=closure_in.discrepancy_explanation,
        )

        # Actualizar estado del período
        period.status = "closed"
        period.closed_at = datetime.utcnow()
        period.closed_by_id = closure.closed_by_id
        period.total_income = closure.total_income
        period.total_expense = closure.total_expense
        period.net_flow = closure.net_flow
        period.expected_balance = closure.expected_balance

        # Actualizar saldo de la cuenta al saldo físico
        from app.repositories.financial import CashAccountRepository
        account_repo = CashAccountRepository(self.db)
        account = await account_repo.get_by_id(closure_in.cash_account_id, tenant_id)
        if account:
            await account_repo.update_balance(account, closure.physical_balance)

        return SchemaCashClosureResponse.model_validate(closure)

    async def get_cash_closure(self, closure_id: UUID, tenant_id: UUID) -> SchemaCashClosureResponse | None:
        closure = await self.closure_repo.get_by_id(closure_id, tenant_id)
        if not closure:
            return None
        return SchemaCashClosureResponse.model_validate(closure)

    async def get_cash_closure_by_period(self, period_id: UUID, tenant_id: UUID) -> SchemaCashClosureResponse | None:
        closure = await self.closure_repo.get_by_period(period_id, tenant_id)
        if not closure:
            return None
        return SchemaCashClosureResponse.model_validate(closure)

    async def get_cash_closures(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "confirmed_at",
        sort_order: str = "desc",
    ) -> CashClosureListResponse:
        filter_obj = None
        if filters:
            filter_obj = CashClosureSearchFilters(
                status=getattr(filters, 'status', None),
                cash_account_id=getattr(filters, 'cash_account_id', None),
                closed_from=getattr(filters, 'closed_from', None),
                closed_to=getattr(filters, 'closed_to', None),
                discrepancy_from=getattr(filters, 'discrepancy_from', None),
                discrepancy_to=getattr(filters, 'discrepancy_to', None),
            )

        closures, total = await self.closure_repo.get_all(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            filters=filter_obj,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total + page_size - 1) // page_size

        return CashClosureListResponse(
            closures=[SchemaCashClosureResponse.model_validate(c) for c in closures],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_cash_closure(
        self,
        closure_id: UUID,
        tenant_id: UUID,
        closure_in: CashClosureUpdate,
    ) -> SchemaCashClosureResponse | None:
        closure = await self.closure_repo.get_by_id(closure_id, tenant_id)
        if not closure:
            return None

        updated = await self.closure_repo.update(
            closure,
            physical_balance=closure_in.physical_balance,
            discrepancy_explanation=closure_in.discrepancy_explanation,
            observations=closure_in.observations,
        )

        return SchemaCashClosureResponse.model_validate(updated)

    async def confirm_cash_closure(
        self,
        closure_id: UUID,
        tenant_id: UUID,
        closed_by_id: UUID,
    ) -> SchemaCashClosureResponse | None:
        closure = await self.closure_repo.get_by_id(closure_id, tenant_id)
        if not closure:
            return None

        confirmed = await self.closure_repo.confirm(closure, closed_by_id)
        return SchemaCashClosureResponse.model_validate(confirmed)

    # ============================================================
    # ADJUSTMENTS (Late entries)
    # ============================================================
    async def create_adjustment(
        self,
        adjustment_in: ClosureAdjustmentCreate,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> ClosureAdjustmentResponse:
        # Verificar que el cierre existe
        closure = await self.closure_repo.get_by_id(adjustment_in.cash_closure_id, tenant_id)
        if not closure:
            raise ValueError("Cierre no encontrado")

        # Verificar que el movimiento existe
        movement = await self.movement_repo.get_by_id(adjustment_in.movement_id, tenant_id)
        if not movement:
            raise ValueError("Movimiento no encontrado")

        adjustment = await self.adjustment_repo.create(
            cash_closure_id=adjustment_in.cash_closure_id,
            movement_id=adjustment_in.movement_id,
            adjustment_type=adjustment_in.adjustment_type,
            amount=adjustment_in.amount,
            impact_on_balance=adjustment_in.impact_on_balance,
            reason=adjustment_in.reason,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
        )

        # Actualizar contador de ajustes del cierre
        closure = await self.closure_repo.get_by_id(adjustment_in.cash_closure_id, tenant_id)
        if closure:
            closure.adjustment_count += 1
            await self.db.flush()

        # Si el movimiento es tardío, marcarlo
        if adjustment_in.adjustment_type in ["late_income", "late_expense"]:
            movement.is_late_entry = True
            await self.db.flush()

        return ClosureAdjustmentResponse.model_validate(adjustment)

    async def get_adjustments(
        self,
        tenant_id: UUID,
        *,
        cash_closure_id: UUID | None = None,
        movement_id: UUID | None = None,
        adjustment_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ClosureAdjustmentResponse], int]:
        adjustments, total = await self.adjustment_repo.get_all(
            tenant_id=tenant_id,
            cash_closure_id=cash_closure_id,
            movement_id=movement_id,
            adjustment_type=adjustment_type,
            page=page,
            page_size=page_size,
        )

        return [ClosureAdjustmentResponse.model_validate(a) for a in adjustments], total

    async def resolve_adjustment(
        self,
        adjustment_id: UUID,
        tenant_id: UUID,
        resolution: str,
        resolved_by_id: UUID,
    ) -> ClosureAdjustmentResponse | None:
        adjustments, _ = await self.adjustment_repo.get_all(
            tenant_id=tenant_id,
            page=1,
            page_size=1,
        )
        # Buscar por ID
        adjustment = next((a for a in adjustments if a.id == adjustment_id), None)
        if not adjustment:
            return None

        updated = await self.adjustment_repo.update(
            adjustment,
            resolution=resolution,
            resolved_by_id=resolved_by_id,
        )
        return ClosureAdjustmentResponse.model_validate(updated)

    # ============================================================
    # WEEKLY PERIOD SUMMARY
    # ============================================================
    async def get_weekly_period_summary(
        self,
        period_id: UUID,
        tenant_id: UUID,
    ) -> WeeklyPeriodSummary | None:
        period = await self.period_repo.get_by_id(period_id, tenant_id)
        if not period:
            return None

        # Obtener cierre si existe
        cash_closure = await self.closure_repo.get_by_period(period.id, tenant_id)
        closure_data = None
        if cash_closure:
            adjustments, _ = await self.adjustment_repo.get_all(
                tenant_id=tenant_id,
                cash_closure_id=cash_closure.id,
            )
            closure_data = {
                "closure": SchemaCashClosureResponse.model_validate(cash_closure),
                "adjustments": [ClosureAdjustmentResponse.model_validate(a) for a in adjustments],
            }

        # Obtener resúmenes diarios
        daily_summaries = await self.movement_repo.get_daily_summaries(
            tenant_id=tenant_id,
            start_date=period.start_date,
            end_date=period.end_date,
        )

        daily = [
            DailySummary(
                date=d["date"],
                total_income=d["total_income"],
                total_expense=d["total_expense"],
                net_flow=d["net_flow"],
                movement_count=d["movement_count"],
            )
            for d in daily_summaries
        ]

        return WeeklyPeriodSummary(
            period=SchemaWeeklyPeriodResponse.model_validate(period),
            cash_closure=closure_data,
            total_adjustments=len(closure_data.get("adjustments", [])) if closure_data else 0,
            daily_summaries=daily,
        )

    # ============================================================
    # HISTORY
    # ============================================================
    async def get_closure_history(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "confirmed_at",
        sort_order: str = "desc",
    ) -> CashClosureListResponse:
        return await self.get_cash_closures(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )