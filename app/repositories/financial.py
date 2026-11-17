from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.financial import (
    CashAccount,
    CashClosure,
    ClosureAdjustment,
    FinancialMovement,
    MovementCategory,
    MovementType,
    PaymentMethod,
    WeeklyPeriod,
)


class FinancialMovementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # CREATE
    # ============================================================
    async def create(
        self,
        *,
        transaction_date: datetime,
        movement_type: MovementType,
        category: MovementCategory,
        amount: Decimal,
        payment_method: PaymentMethod,
        cash_account_id: UUID,
        concept: str,
        tenant_id: UUID,
        created_by_id: UUID,
        description: str | None = None,
        payment_method_value: str | None = None,
        category_value: str | None = None,
        customer_id: UUID | None = None,
        task_id: UUID | None = None,
        quotation_id: UUID | None = None,
        is_late_entry: bool = False,
        late_entry_reason: str | None = None,
    ) -> FinancialMovement:
        movement = FinancialMovement(
            transaction_date=transaction_date,
            movement_type=movement_type,
            category=category,
            amount=amount,
            payment_method=payment_method,
            cash_account_id=cash_account_id,
            concept=concept,
            description=description,
            customer_id=customer_id,
            task_id=task_id,
            quotation_id=quotation_id,
            is_late_entry=is_late_entry,
            late_entry_reason=late_entry_reason,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
        )
        self.db.add(movement)
        await self.db.flush()
        await self.db.refresh(movement)
        return movement

    # ============================================================
    # GET
    # ============================================================
    async def get_by_id(self, movement_id: UUID, tenant_id: UUID) -> FinancialMovement | None:
        stmt = select(FinancialMovement).where(
            FinancialMovement.id == movement_id,
            FinancialMovement.tenant_id == tenant_id,
        ).options(
            selectinload(FinancialMovement.cash_account),
            selectinload(FinancialMovement.customer),
            selectinload(FinancialMovement.task),
            selectinload(FinancialMovement.weekly_period),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ============================================================
    # LIST WITH FILTERS
    # ============================================================
    async def get_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "transaction_date",
        sort_order: str = "desc",
    ) -> tuple[Sequence[FinancialMovement], int]:
        stmt = select(FinancialMovement).where(FinancialMovement.tenant_id == tenant_id)
        count_stmt = select(func.count()).where(FinancialMovement.tenant_id == tenant_id)

        if filters:
            filter_obj = filters

            if getattr(filter_obj, 'query', None):
                search_filter = or_(
                    FinancialMovement.concept.ilike(f"%{filter_obj.query}%"),
                    FinancialMovement.description.ilike(f"%{filter_obj.query}%"),
                )
                stmt = stmt.where(search_filter)
                count_stmt = count_stmt.where(search_filter)

            if getattr(filter_obj, 'movement_type', None):
                stmt = stmt.where(FinancialMovement.movement_type == filter_obj.movement_type)
                count_stmt = count_stmt.where(FinancialMovement.movement_type == filter_obj.movement_type)

            if getattr(filter_obj, 'category', None):
                stmt = stmt.where(FinancialMovement.category == filter_obj.category)
                count_stmt = count_stmt.where(FinancialMovement.category == filter_obj.category)

            if getattr(filter_obj, 'payment_method', None):
                stmt = stmt.where(FinancialMovement.payment_method == filter_obj.payment_method)
                count_stmt = count_stmt.where(FinancialMovement.payment_method == filter_obj.payment_method)

            if getattr(filter_obj, 'cash_account_id', None):
                stmt = stmt.where(FinancialMovement.cash_account_id == filter_obj.cash_account_id)
                count_stmt = count_stmt.where(FinancialMovement.cash_account_id == filter_obj.cash_account_id)

            if getattr(filter_obj, 'customer_id', None):
                stmt = stmt.where(FinancialMovement.customer_id == filter_obj.customer_id)
                count_stmt = count_stmt.where(FinancialMovement.customer_id == filter_obj.customer_id)

            if getattr(filter_obj, 'task_id', None):
                stmt = stmt.where(FinancialMovement.task_id == filter_obj.task_id)
                count_stmt = count_stmt.where(FinancialMovement.task_id == filter_obj.task_id)

            if getattr(filter_obj, 'transaction_from', None):
                stmt = stmt.where(FinancialMovement.transaction_date >= filter_obj.transaction_from)
                count_stmt = count_stmt.where(FinancialMovement.transaction_date >= filter_obj.transaction_from)

            if getattr(filter_obj, 'transaction_to', None):
                stmt = stmt.where(FinancialMovement.transaction_date <= filter_obj.transaction_to)
                count_stmt = count_stmt.where(FinancialMovement.transaction_date <= filter_obj.transaction_to)

            if getattr(filter_obj, 'recorded_from', None):
                stmt = stmt.where(FinancialMovement.recorded_at >= filter_obj.recorded_from)
                count_stmt = count_stmt.where(FinancialMovement.recorded_at >= filter_obj.recorded_from)

            if getattr(filter_obj, 'recorded_to', None):
                stmt = stmt.where(FinancialMovement.recorded_at <= filter_obj.recorded_to)
                count_stmt = count_stmt.where(FinancialMovement.recorded_at <= filter_obj.recorded_to)

            if getattr(filter_obj, 'is_late_entry', None) is not None:
                stmt = stmt.where(FinancialMovement.is_late_entry == filter_obj.is_late_entry)
                count_stmt = count_stmt.where(FinancialMovement.is_late_entry == filter_obj.is_late_entry)

            if getattr(filter_obj, 'min_amount', None) is not None:
                stmt = stmt.where(FinancialMovement.amount >= filter_obj.min_amount)
                count_stmt = count_stmt.where(FinancialMovement.amount >= filter_obj.min_amount)

            if getattr(filter_obj, 'max_amount', None) is not None:
                stmt = stmt.where(FinancialMovement.amount <= filter_obj.max_amount)
                count_stmt = count_stmt.where(FinancialMovement.amount <= filter_obj.max_amount)

        # Sorting
        sort_column = getattr(FinancialMovement, sort_by, FinancialMovement.transaction_date)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(stmt)
        movements = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return movements, total

    # ============================================================
    # UPDATE
    # ============================================================
    async def update(
        self,
        movement: FinancialMovement,
        *,
        transaction_date: datetime | None = None,
        movement_type: str | None = None,
        category: str | None = None,
        amount: Decimal | None = None,
        payment_method: str | None = None,
        cash_account_id: UUID | None = None,
        concept: str | None = None,
        description: str | None = None,
        customer_id: UUID | None = None,
        task_id: UUID | None = None,
        quotation_id: UUID | None = None,
        is_late_entry: bool | None = None,
        late_entry_reason: str | None = None,
    ) -> FinancialMovement:
        if transaction_date is not None:
            movement.transaction_date = transaction_date
        if movement_type is not None:
            movement.movement_type = movement_type
        if category is not None:
            movement.category = category
        if amount is not None:
            movement.amount = amount
        if payment_method is not None:
            movement.payment_method = payment_method
        if cash_account_id is not None:
            movement.cash_account_id = cash_account_id
        if concept is not None:
            movement.concept = concept
        if description is not None:
            movement.description = description
        if customer_id is not None:
            movement.customer_id = customer_id
        if task_id is not None:
            movement.task_id = task_id
        if quotation_id is not None:
            movement.quotation_id = quotation_id
        if is_late_entry is not None:
            movement.is_late_entry = is_late_entry
        if late_entry_reason is not None:
            movement.late_entry_reason = late_entry_reason

        await self.db.flush()
        await self.db.refresh(movement)
        return movement

    # ============================================================
    # DAILY SUMMARY (for calendar)
    # ============================================================
    async def get_daily_summaries(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """Obtener resumen diario para un rango de fechas"""
        stmt = (
            select(
                FinancialMovement.transaction_date,
                func.sum(
                    case(
                        (FinancialMovement.movement_type == "income", FinancialMovement.amount),
                        else_=0,
                    )
                ).label("total_income"),
                func.sum(
                    case(
                        (FinancialMovement.movement_type == "expense", FinancialMovement.amount),
                        else_=0,
                    )
                ).label("total_expense"),
                func.count(FinancialMovement.id).label("movement_count"),
            )
            .where(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.transaction_date >= start_date,
                FinancialMovement.transaction_date <= end_date,
            )
            .group_by(FinancialMovement.transaction_date)
            .order_by(FinancialMovement.transaction_date)
        )

        result = await self.db.execute(stmt)
        return [
            {
                "date": row.transaction_date,
                "total_income": row.total_income or Decimal(0),
                "total_expense": row.total_expense or Decimal(0),
                "net_flow": (row.total_income or Decimal(0)) - (row.total_expense or Decimal(0)),
                "movement_count": row.movement_count,
            }
            for row in result.all()
        ]

    # ============================================================
    # MONTHLY TOTALS
    # ============================================================
    async def get_monthly_totals(
        self,
        tenant_id: UUID,
        year: int,
        month: int,
    ) -> dict:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

        stmt = select(
            func.sum(
                case(
                    (FinancialMovement.movement_type == "income", FinancialMovement.amount),
                    else_=0,
                )
            ).label("total_income"),
            func.sum(
                case(
                    (FinancialMovement.movement_type == "expense", FinancialMovement.amount),
                    else_=0,
                )
            ).label("total_expense"),
            func.count(FinancialMovement.id).label("total_movements"),
        ).where(
            FinancialMovement.tenant_id == tenant_id,
            FinancialMovement.transaction_date >= start_date,
            FinancialMovement.transaction_date <= end_date,
        )

        result = await self.db.execute(stmt)
        row = result.one()

        return {
            "total_income": row.total_income or Decimal(0),
            "total_expense": row.total_expense or Decimal(0),
            "net_flow": (row.total_income or Decimal(0)) - (row.total_expense or Decimal(0)),
            "total_movements": row.total_movements or 0,
        }


class WeeklyPeriodRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        week_number: int,
        year: int,
        start_date: datetime,
        end_date: datetime,
        cash_account_id: UUID,
        tenant_id: UUID,
        created_by_id: UUID,
        opening_balance: Decimal = Decimal(0),
    ) -> WeeklyPeriod:
        period = WeeklyPeriod(
            week_number=week_number,
            year=year,
            start_date=start_date,
            end_date=end_date,
            cash_account_id=cash_account_id,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            opening_balance=opening_balance,
        )
        self.db.add(period)
        await self.db.flush()
        await self.db.refresh(period)
        return period

    async def get_by_id(self, period_id: UUID, tenant_id: UUID) -> WeeklyPeriod | None:
        stmt = select(WeeklyPeriod).where(
            WeeklyPeriod.id == period_id,
            WeeklyPeriod.tenant_id == tenant_id,
        ).options(
            selectinload(WeeklyPeriod.cash_account),
            selectinload(WeeklyPeriod.cash_closure),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_week(
        self,
        tenant_id: UUID,
        year: int,
        week_number: int,
        cash_account_id: UUID,
    ) -> WeeklyPeriod | None:
        stmt = select(WeeklyPeriod).where(
            WeeklyPeriod.tenant_id == tenant_id,
            WeeklyPeriod.year == year,
            WeeklyPeriod.week_number == week_number,
            WeeklyPeriod.cash_account_id == cash_account_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "start_date",
        sort_order: str = "desc",
    ) -> tuple[Sequence[WeeklyPeriod], int]:
        stmt = select(WeeklyPeriod).where(WeeklyPeriod.tenant_id == tenant_id)
        count_stmt = select(func.count()).where(WeeklyPeriod.tenant_id == tenant_id)

        if filters:
            filter_obj = filters

            if getattr(filter_obj, 'status', None):
                stmt = stmt.where(WeeklyPeriod.status == filter_obj.status)
                count_stmt = count_stmt.where(WeeklyPeriod.status == filter_obj.status)

            if getattr(filter_obj, 'cash_account_id', None):
                stmt = stmt.where(WeeklyPeriod.cash_account_id == filter_obj.cash_account_id)
                count_stmt = count_stmt.where(WeeklyPeriod.cash_account_id == filter_obj.cash_account_id)

            if getattr(filter_obj, 'year', None):
                stmt = stmt.where(WeeklyPeriod.year == filter_obj.year)
                count_stmt = count_stmt.where(WeeklyPeriod.year == filter_obj.year)

            if getattr(filter_obj, 'week_number', None):
                stmt = stmt.where(WeeklyPeriod.week_number == filter_obj.week_number)
                count_stmt = count_stmt.where(WeeklyPeriod.week_number == filter_obj.week_number)

            if getattr(filter_obj, 'start_from', None):
                stmt = stmt.where(WeeklyPeriod.start_date >= filter_obj.start_from)
                count_stmt = count_stmt.where(WeeklyPeriod.start_date >= filter_obj.start_from)

            if getattr(filter_obj, 'start_to', None):
                stmt = stmt.where(WeeklyPeriod.start_date <= filter_obj.start_to)
                count_stmt = count_stmt.where(WeeklyPeriod.start_date <= filter_obj.start_to)

            if getattr(filter_obj, 'end_from', None):
                stmt = stmt.where(WeeklyPeriod.end_date >= filter_obj.end_from)
                count_stmt = count_stmt.where(WeeklyPeriod.end_date >= filter_obj.end_from)

            if getattr(filter_obj, 'end_to', None):
                stmt = stmt.where(WeeklyPeriod.end_date <= filter_obj.end_to)
                count_stmt = count_stmt.where(WeeklyPeriod.end_date <= filter_obj.end_to)

        # Sorting
        sort_column = getattr(WeeklyPeriod, sort_by, WeeklyPeriod.start_date)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        periods = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return periods, total

    async def update(
        self,
        period: WeeklyPeriod,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        status: str | None = None,
        opening_balance: Decimal | None = None,
        total_income: Decimal | None = None,
        total_expense: Decimal | None = None,
        net_flow: Decimal | None = None,
        expected_balance: Decimal | None = None,
    ) -> WeeklyPeriod:
        if start_date is not None:
            period.start_date = start_date
        if end_date is not None:
            period.end_date = end_date
        if status is not None:
            period.status = status
        if opening_balance is not None:
            period.opening_balance = opening_balance
        if total_income is not None:
            period.total_income = total_income
        if total_expense is not None:
            period.total_expense = total_expense
        if net_flow is not None:
            period.net_flow = net_flow
        if expected_balance is not None:
            period.expected_balance = expected_balance

        await self.db.flush()
        await self.db.refresh(period)
        return period

    async def close_period(
        self,
        period: WeeklyPeriod,
        closed_by_id: UUID,
    ) -> WeeklyPeriod:
        period.status = "closed"
        period.closed_at = datetime.utcnow()
        period.closed_by_id = closed_by_id
        await self.db.flush()
        await self.db.refresh(period)
        return period

    async def calculate_totals(self, period_id: UUID, tenant_id: UUID) -> dict:
        """Calcular totales del período basado en movimientos"""
        from app.repositories.financial import FinancialMovementRepository

        movement_repo = FinancialMovementRepository(self.db)
        daily_summaries = await movement_repo.get_daily_summaries(
            tenant_id,
            start_date=datetime.min,
            end_date=datetime.max,
        )

        # Filtrar solo los días del período
        period = await self.get_by_id(period_id, tenant_id)
        if not period:
            return {"total_income": Decimal(0), "total_expense": Decimal(0), "net_flow": Decimal(0)}

        daily_summaries = await self.db.execute(
            select(
                func.sum(
                    case(
                        (FinancialMovement.movement_type == "income", FinancialMovement.amount),
                        else_=0,
                    )
                ).label("total_income"),
                func.sum(
                    case(
                        (FinancialMovement.movement_type == "expense", FinancialMovement.amount),
                        else_=0,
                    )
                ).label("total_expense"),
                func.count(FinancialMovement.id).label("movement_count"),
            ).where(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.transaction_date >= period.start_date,
                FinancialMovement.transaction_date <= period.end_date,
            )
        )

        row = daily_summaries.one()
        total_income = row.total_income or Decimal(0)
        total_expense = row.total_expense or Decimal(0)
        net_flow = total_income - total_expense

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_flow": net_flow,
            "expected_balance": (period.opening_balance or Decimal(0)) + net_flow,
        }

    async def get_current_period(
        self,
        tenant_id: UUID,
        cash_account_id: UUID,
        date: datetime | None = None,
    ) -> WeeklyPeriod | None:
        """Obtener el período actual para una fecha dada"""
        if date is None:
            date = datetime.utcnow()

        stmt = select(WeeklyPeriod).where(
            WeeklyPeriod.tenant_id == tenant_id,
            WeeklyPeriod.cash_account_id == cash_account_id,
            WeeklyPeriod.start_date <= date,
            WeeklyPeriod.end_date >= date,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_current_period(
        self,
        tenant_id: UUID,
        cash_account_id: UUID,
        date: datetime | None = None,
        created_by_id: UUID | None = None,
    ) -> WeeklyPeriod:
        period = await self.get_current_period(tenant_id, cash_account_id, date)
        if period:
            return period

        # Crear nuevo período
        if date is None:
            date = datetime.utcnow()

        # Calcular número de semana
        week_number = date.isocalendar()[1]
        year = date.isocalendar()[0]

        # Calcular inicio de semana (lunes)
        start_of_week = date - timedelta(days=date.weekday())
        start_of_week = datetime.combine(start_of_week.date(), datetime.min.time())
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return await self.create(
            week_number=week_number,
            year=year,
            start_date=start_of_week,
            end_date=end_of_week,
            cash_account_id=cash_account_id,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
        )


class CashAccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        name: str,
        code: str,
        tenant_id: UUID,
        created_by_id: UUID,
        description: str | None = None,
        account_type: str = "cash",
        currency: str = "COP",
        is_active: bool = True,
    ) -> CashAccount:
        account = CashAccount(
            name=name,
            code=code,
            description=description,
            account_type=account_type,
            currency=currency,
            is_active=is_active,
            tenant_id=tenant_id,
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def get_by_id(self, account_id: UUID, tenant_id: UUID) -> CashAccount | None:
        stmt = select(CashAccount).where(
            CashAccount.id == account_id,
            CashAccount.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: UUID) -> CashAccount | None:
        stmt = select(CashAccount).where(
            CashAccount.code == code,
            CashAccount.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[Sequence[CashAccount], int]:
        stmt = select(CashAccount).where(CashAccount.tenant_id == tenant_id)
        count_stmt = select(func.count()).where(CashAccount.tenant_id == tenant_id)

        if is_active is not None:
            stmt = stmt.where(CashAccount.is_active == is_active)
            count_stmt = count_stmt.where(CashAccount.is_active == is_active)

        stmt = stmt.order_by(CashAccount.name)
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        accounts = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return accounts, total

    async def update_balance(self, account: CashAccount, new_balance: Decimal) -> CashAccount:
        account.current_balance = new_balance
        await self.db.flush()
        await self.db.refresh(account)
        return account


class CashClosureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        weekly_period_id: UUID,
        cash_account_id: UUID,
        tenant_id: UUID,
        closed_by_id: UUID,
        opening_balance: Decimal,
        total_income: Decimal,
        total_expense: Decimal,
        net_flow: Decimal,
        expected_balance: Decimal,
        physical_balance: Decimal,
        discrepancy: Decimal,
        observations: str | None = None,
        discrepancy_explanation: str | None = None,
    ) -> CashClosure:
        closure = CashClosure(
            weekly_period_id=weekly_period_id,
            cash_account_id=cash_account_id,
            tenant_id=tenant_id,
            closed_by_id=closed_by_id,
            opening_balance=opening_balance,
            total_income=total_income,
            total_expense=total_expense,
            net_flow=net_flow,
            expected_balance=expected_balance,
            physical_balance=physical_balance,
            discrepancy=discrepancy,
            observations=observations,
            discrepancy_explanation=discrepancy_explanation,
        )
        self.db.add(closure)
        await self.db.flush()
        await self.db.refresh(closure)
        return closure

    async def get_by_id(self, closure_id: UUID, tenant_id: UUID) -> CashClosure | None:
        stmt = select(CashClosure).where(
            CashClosure.id == closure_id,
            CashClosure.tenant_id == tenant_id,
        ).options(
            selectinload(CashClosure.weekly_period),
            selectinload(CashClosure.cash_account),
            selectinload(CashClosure.adjustments),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_period(self, weekly_period_id: UUID, tenant_id: UUID) -> CashClosure | None:
        stmt = select(CashClosure).where(
            CashClosure.weekly_period_id == weekly_period_id,
            CashClosure.tenant_id == tenant_id,
        ).options(
            selectinload(CashClosure.adjustments),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "confirmed_at",
        sort_order: str = "desc",
    ) -> tuple[Sequence[CashClosure], int]:
        stmt = select(CashClosure).where(CashClosure.tenant_id == tenant_id)
        count_stmt = select(func.count()).where(CashClosure.tenant_id == tenant_id)

        if filters:
            filter_obj = filters

            if getattr(filter_obj, 'status', None):
                stmt = stmt.where(CashClosure.status == filter_obj.status)
                count_stmt = count_stmt.where(CashClosure.status == filter_obj.status)

            if getattr(filter_obj, 'cash_account_id', None):
                stmt = stmt.where(CashClosure.cash_account_id == filter_obj.cash_account_id)
                count_stmt = count_stmt.where(CashClosure.cash_account_id == filter_obj.cash_account_id)

            if getattr(filter_obj, 'closed_from', None):
                stmt = stmt.where(CashClosure.confirmed_at >= filter_obj.closed_from)
                count_stmt = count_stmt.where(CashClosure.confirmed_at >= filter_obj.closed_from)

            if getattr(filter_obj, 'closed_to', None):
                stmt = stmt.where(CashClosure.confirmed_at <= filter_obj.closed_to)
                count_stmt = count_stmt.where(CashClosure.confirmed_at <= filter_obj.closed_to)

            if getattr(filter_obj, 'discrepancy_from', None) is not None:
                stmt = stmt.where(CashClosure.discrepancy >= filter_obj.discrepancy_from)
                count_stmt = count_stmt.where(CashClosure.discrepancy >= filter_obj.discrepancy_from)

            if getattr(filter_obj, 'discrepancy_to', None) is not None:
                stmt = stmt.where(CashClosure.discrepancy <= filter_obj.discrepancy_to)
                count_stmt = count_stmt.where(CashClosure.discrepancy <= filter_obj.discrepancy_to)

        sort_column = getattr(CashClosure, sort_by, CashClosure.confirmed_at)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        closures = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return closures, total

    async def update(
        self,
        closure: CashClosure,
        *,
        physical_balance: Decimal | None = None,
        discrepancy_explanation: str | None = None,
        observations: str | None = None,
    ) -> CashClosure:
        if physical_balance is not None:
            closure.physical_balance = physical_balance
            closure.discrepancy = physical_balance - closure.expected_balance
        if discrepancy_explanation is not None:
            closure.discrepancy_explanation = discrepancy_explanation
        if observations is not None:
            closure.observations = observations

        await self.db.flush()
        await self.db.refresh(closure)
        return closure

    async def confirm(self, closure: CashClosure, closed_by_id: UUID) -> CashClosure:
        closure.status = "confirmed"
        closure.closed_by_id = closed_by_id
        closure.confirmed_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(closure)
        return closure


class ClosureAdjustmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        cash_closure_id: UUID,
        movement_id: UUID,
        adjustment_type: str,
        amount: Decimal,
        impact_on_balance: Decimal,
        reason: str,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> ClosureAdjustment:
        adjustment = ClosureAdjustment(
            cash_closure_id=cash_closure_id,
            movement_id=movement_id,
            adjustment_type=adjustment_type,
            amount=amount,
            impact_on_balance=impact_on_balance,
            reason=reason,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
        )
        self.db.add(adjustment)
        await self.db.flush()
        await self.db.refresh(adjustment)
        return adjustment

    async def get_all(
        self,
        tenant_id: UUID,
        *,
        cash_closure_id: UUID | None = None,
        movement_id: UUID | None = None,
        adjustment_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[ClosureAdjustment], int]:
        stmt = select(ClosureAdjustment).where(ClosureAdjustment.tenant_id == tenant_id)
        count_stmt = select(func.count()).where(ClosureAdjustment.tenant_id == tenant_id)

        if cash_closure_id:
            stmt = stmt.where(ClosureAdjustment.cash_closure_id == cash_closure_id)
            count_stmt = count_stmt.where(ClosureAdjustment.cash_closure_id == cash_closure_id)

        if movement_id:
            stmt = stmt.where(ClosureAdjustment.movement_id == movement_id)
            count_stmt = count_stmt.where(ClosureAdjustment.movement_id == movement_id)

        if adjustment_type:
            stmt = stmt.where(ClosureAdjustment.adjustment_type == adjustment_type)
            count_stmt = count_stmt.where(ClosureAdjustment.adjustment_type == adjustment_type)

        stmt = stmt.order_by(desc(ClosureAdjustment.created_at))
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        adjustments = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return adjustments, total

    async def update(
        self,
        adjustment: ClosureAdjustment,
        *,
        resolution: str | None = None,
        resolved_by_id: UUID | None = None,
    ) -> ClosureAdjustment:
        if resolution is not None:
            adjustment.resolution = resolution
        if resolved_by_id is not None:
            adjustment.resolved_by_id = resolved_by_id
            adjustment.resolved_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(adjustment)
        return adjustment