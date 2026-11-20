from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tasks import PaymentStatus, Task, TaskPriority, TaskStatus


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        title: str,
        created_by_id: UUID,
        tenant_id: UUID,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: datetime | None = None,
        assignee_id: UUID | None = None,
        customer_id: UUID | None = None,
        total_price: Decimal | None = None,
        total_paid: Decimal = Decimal(0),
        pending_balance: Decimal = Decimal(0),
        payment_status: PaymentStatus = PaymentStatus.NO_PAYMENTS,
        last_payment_date: datetime | None = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            assignee_id=assignee_id,
            customer_id=customer_id,
            total_price=total_price,
            total_paid=total_paid,
            pending_balance=pending_balance,
            payment_status=payment_status,
            last_payment_date=last_payment_date,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID) -> Task | None:
        stmt = select(Task).where(Task.id == task_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[Sequence[Task], int]:
        stmt = select(Task)
        count_stmt = select(func.count())

        # Filters
        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
            count_stmt = count_stmt.where(Task.priority == priority)
        if assignee_id:
            stmt = stmt.where(Task.assignee_id == assignee_id)
            count_stmt = count_stmt.where(Task.assignee_id == assignee_id)
        if search:
            search_filter = or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Sorting
        sort_column = getattr(Task, sort_by, Task.created_at)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return tasks, total

    async def update(
        self,
        task: Task,
        *,
        title: str | None = None,
        description: str | None = None,
        priority: TaskPriority | None = None,
        due_date: datetime | None = None,
        assignee_id: UUID | None = None,
        customer_id: UUID | None = None,
        total_price: Decimal | None = None,
    ) -> Task:
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if due_date is not None:
            task.due_date = due_date
        if assignee_id is not None:
            task.assignee_id = assignee_id
        if customer_id is not None:
            task.customer_id = customer_id
        if total_price is not None:
            task.total_price = total_price

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update_status(self, task: Task, status: TaskStatus) -> Task:
        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update_priority(self, task: Task, priority: TaskPriority) -> Task:
        task.priority = priority
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.db.delete(task)
        await self.db.flush()

    async def update_financial_info(
        self,
        task: Task,
        *,
        total_price: Decimal | None = None,
        total_paid: Decimal | None = None,
        pending_balance: Decimal | None = None,
        payment_status: PaymentStatus | None = None,
        last_payment_date: datetime | None = None,
    ) -> Task:
        """Actualizar información financiera de la tarea."""
        if total_price is not None:
            task.total_price = total_price
        if total_paid is not None:
            task.total_paid = total_paid
        if pending_balance is not None:
            task.pending_balance = pending_balance
        if payment_status is not None:
            task.payment_status = payment_status
        if last_payment_date is not None:
            task.last_payment_date = last_payment_date

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_pending_payments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: TaskStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_pending_balance: Decimal | None = None,
        max_pending_balance: Decimal | None = None,
        only_active: bool = False,
        only_completed: bool = False,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[Sequence[Task], int]:
        """Obtener tareas con saldo pendiente > 0."""
        from app.models.customers import Customer

        stmt = select(Task).where(Task.pending_balance > 0)
        count_stmt = select(func.count()).where(Task.pending_balance > 0)

        # Join con customers si se filtra por cliente
        if customer_id or search:
            stmt = stmt.join(Customer, Task.customer_id == Customer.id, isouter=True)
            count_stmt = count_stmt.join(Customer, Task.customer_id == Customer.id, isouter=True)

        if customer_id:
            stmt = stmt.where(Task.customer_id == customer_id)
            count_stmt = count_stmt.where(Task.customer_id == customer_id)

        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)

        if only_active:
            stmt = stmt.where(Task.status != TaskStatus.COMPLETED)
            count_stmt = count_stmt.where(Task.status != TaskStatus.COMPLETED)

        if only_completed:
            stmt = stmt.where(Task.status == TaskStatus.COMPLETED)
            count_stmt = count_stmt.where(Task.status == TaskStatus.COMPLETED)

        if date_from:
            stmt = stmt.where(Task.created_at >= date_from)
            count_stmt = count_stmt.where(Task.created_at >= date_from)

        if date_to:
            stmt = stmt.where(Task.created_at <= date_to)
            count_stmt = count_stmt.where(Task.created_at <= date_to)

        if min_pending_balance is not None:
            stmt = stmt.where(Task.pending_balance >= min_pending_balance)
            count_stmt = count_stmt.where(Task.pending_balance >= min_pending_balance)

        if max_pending_balance is not None:
            stmt = stmt.where(Task.pending_balance <= max_pending_balance)
            count_stmt = count_stmt.where(Task.pending_balance <= max_pending_balance)

        if search:
            search_filter = or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%") if hasattr(Customer, 'name') else False,
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Sorting
        sort_column = getattr(Task, sort_by, Task.created_at)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return tasks, total

    async def get_task_with_customer(self, task_id: UUID) -> Task | None:
        """Obtener tarea con información del cliente cargada."""
        stmt = select(Task).where(Task.id == task_id).options(
            selectinload(Task.customer)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()