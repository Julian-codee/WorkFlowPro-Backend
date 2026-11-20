from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa

from app.db.session import AsyncSession
from app.models.financial import (
    FinancialMovement,
    MovementCategory,
    MovementType,
    PaymentMethod,
)
from app.models.tasks import PaymentStatus, TaskPriority, TaskStatus
from app.repositories.tasks import TaskRepository
from app.schemas.tasks import (
    PendingPaymentsFilters,
    PendingPaymentsListResponse,
    PendingPaymentTaskResponse,
    TaskCreate,
    TaskListResponse,
    TaskPaymentCreate,
    TaskPaymentListResponse,
    TaskPaymentResponse,
    TaskPriorityUpdate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.financial_service import FinancialService


class TaskService:
    def __init__(self, db: AsyncSession):
        self.repository = TaskRepository(db)
        self.db = db
        self.financial_service = FinancialService(db)

    async def _get_current_user_id(self) -> UUID:
        """Obtener el user_id del contexto RLS."""
        result = await self.db.execute(
            sa.text("SELECT current_setting('app.current_user_id', true)")
        )
        user_id_str = result.scalar()
        return UUID(user_id_str)

    async def _get_current_tenant_id(self) -> UUID:
        """Obtener el tenant_id del contexto RLS."""
        result = await self.db.execute(
            sa.text("SELECT current_setting('app.current_tenant_id', true)")
        )
        tenant_id_str = result.scalar()
        return UUID(tenant_id_str)

    def _calculate_payment_status(self, total_price: Decimal | None, total_paid: Decimal) -> PaymentStatus:
        """Calcular el estado del pago basado en el precio y lo pagado."""
        if total_price is None or total_price == 0:
            return PaymentStatus.NO_PAYMENTS if total_paid == 0 else PaymentStatus.PARTIALLY_PAID
        if total_paid == 0:
            return PaymentStatus.NO_PAYMENTS
        if total_paid >= total_price:
            return PaymentStatus.PAID
        return PaymentStatus.PARTIALLY_PAID

    def _calculate_pending_balance(self, total_price: Decimal | None, total_paid: Decimal) -> Decimal:
        """Calcular el saldo pendiente."""
        if total_price is None:
            return Decimal(0)
        balance = total_price - total_paid
        return max(balance, Decimal(0))

    async def create_task(
        self,
        *,
        task_in: TaskCreate,
    ) -> TaskResponse:
        created_by_id = await self._get_current_user_id()
        tenant_id = await self._get_current_tenant_id()

        # Calcular información financiera inicial
        total_price = task_in.total_price
        initial_payment = task_in.initial_payment_amount or Decimal(0)
        total_paid = initial_payment
        pending_balance = self._calculate_pending_balance(total_price, total_paid)
        payment_status = self._calculate_payment_status(total_price, total_paid)
        last_payment_date = task_in.initial_payment_date if initial_payment > 0 else None

        task = await self.repository.create(
            title=task_in.title,
            description=task_in.description,
            priority=task_in.priority,
            due_date=task_in.due_date,
            assignee_id=task_in.assignee_id,
            customer_id=task_in.customer_id,
            created_by_id=created_by_id,
            tenant_id=tenant_id,
            total_price=total_price,
            total_paid=total_paid,
            pending_balance=pending_balance,
            payment_status=payment_status,
            last_payment_date=last_payment_date,
        )

        # Si hay abono inicial, crear movimiento financiero
        if initial_payment > 0:
            await self._create_payment_movement(
                task=task,
                amount=initial_payment,
                transaction_date=task_in.initial_payment_date or task.created_at,
                cash_account_id=task_in.initial_payment_account_id,
                payment_method=task_in.initial_payment_method or "cash",
                reference=task_in.initial_payment_reference,
                notes=task_in.initial_payment_notes,
                created_by_id=created_by_id,
            )

        # Recargar tarea con relaciones para la respuesta
        task = await self.repository.get_by_id(task.id)
        response = TaskResponse.model_validate(task)
        response.has_pending_balance = response.pending_balance > 0
        return response

    async def _create_payment_movement(
        self,
        *,
        task,
        amount: Decimal,
        transaction_date,
        cash_account_id: UUID,
        payment_method: str,
        reference: str | None = None,
        notes: str | None = None,
        created_by_id: UUID,
    ) -> FinancialMovement:
        """Crear un movimiento financiero de ingreso asociado a la tarea."""
        tenant_id = task.tenant_id

        # Validar que la cuenta pertenece al mismo tenant
        from app.repositories.financial import CashAccountRepository
        account_repo = CashAccountRepository(self.db)
        cash_account = await account_repo.get_by_id(cash_account_id, tenant_id)
        if not cash_account:
            raise ValueError("Cuenta de dinero no encontrada")
        if not cash_account.is_active:
            raise ValueError("La cuenta de dinero no está activa")

        # Determinar categoría (servicios por defecto para tareas)
        category = MovementCategory.SERVICES

        concept = f"Abono a tarea: {task.title}"
        if reference:
            concept += f" (Ref: {reference})"

        description = notes or f"Pago registrado desde la tarea {task.id}"

        movement = await self.financial_service.movement_repo.create(
            transaction_date=transaction_date,
            movement_type=MovementType.INCOME,
            category=category,
            amount=amount,
            payment_method=PaymentMethod(payment_method) if isinstance(payment_method, str) else payment_method,
            cash_account_id=cash_account_id,
            concept=concept,
            description=description,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            task_id=task.id,
            customer_id=task.customer_id,
        )

        # Actualizar saldo de la cuenta
        new_balance = cash_account.current_balance + amount
        await account_repo.update_balance(cash_account, new_balance)

        return movement

    async def get_task(self, task_id: UUID) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None
        response = TaskResponse.model_validate(task)
        response.has_pending_balance = response.pending_balance > 0
        return response

    async def get_tasks(
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
    ) -> TaskListResponse:
        tasks, total = await self.repository.get_all(
            page=page,
            page_size=page_size,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total + page_size - 1) // page_size

        task_responses = []
        for t in tasks:
            resp = TaskResponse.model_validate(t)
            resp.has_pending_balance = resp.pending_balance > 0
            task_responses.append(resp)

        return TaskListResponse(
            tasks=task_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_task(
        self,
        task_id: UUID,
        task_in: TaskUpdate,
    ) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None

        # Validar cambio de precio
        if task_in.total_price is not None and task_in.total_price != task.total_price:
            new_price = task_in.total_price
            if new_price < task.total_paid:
                raise ValueError(
                    f"El nuevo precio ({new_price}) no puede ser inferior al total pagado ({task.total_paid}). "
                    "Use un procedimiento de devolución o ajuste autorizado."
                )

            # Recalcular información financiera
            total_paid = task.total_paid
            pending_balance = self._calculate_pending_balance(new_price, total_paid)
            payment_status = self._calculate_payment_status(new_price, total_paid)

            updated_task = await self.repository.update(
                task,
                title=task_in.title,
                description=task_in.description,
                priority=task_in.priority,
                due_date=task_in.due_date,
                assignee_id=task_in.assignee_id,
                customer_id=task_in.customer_id,
                total_price=new_price,
            )

            # Actualizar información financiera
            await self.repository.update_financial_info(
                updated_task,
                pending_balance=pending_balance,
                payment_status=payment_status,
            )
        else:
            updated_task = await self.repository.update(
                task,
                title=task_in.title,
                description=task_in.description,
                priority=task_in.priority,
                due_date=task_in.due_date,
                assignee_id=task_in.assignee_id,
                customer_id=task_in.customer_id,
                total_price=task_in.total_price,
            )

        response = TaskResponse.model_validate(updated_task)
        response.has_pending_balance = response.pending_balance > 0
        return response

    async def update_task_status(
        self,
        task_id: UUID,
        status_in: TaskStatusUpdate,
    ) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None

        updated_task = await self.repository.update_status(task, status_in.status)
        response = TaskResponse.model_validate(updated_task)
        response.has_pending_balance = response.pending_balance > 0
        return response

    async def update_task_priority(
        self,
        task_id: UUID,
        priority_in: TaskPriorityUpdate,
    ) -> TaskResponse | None:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return None

        updated_task = await self.repository.update_priority(task, priority_in.priority)
        response = TaskResponse.model_validate(updated_task)
        response.has_pending_balance = response.pending_balance > 0
        return response

    async def delete_task(self, task_id: UUID) -> bool:
        task = await self.repository.get_by_id(task_id)
        if not task:
            return False

        await self.repository.delete(task)
        return True

    # ============================================================
    # PAGOS DE TAREAS
    # ============================================================

    async def add_payment(
        self,
        task_id: UUID,
        payment_in: TaskPaymentCreate,
    ) -> TaskPaymentResponse:
        """Registrar un nuevo abono/pago a una tarea."""
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise ValueError("Tarea no encontrada")

        # Validar que no exceda el saldo pendiente
        if task.total_price is not None and payment_in.amount > task.pending_balance:
            raise ValueError(
                f"El monto del pago ({payment_in.amount}) excede el saldo pendiente ({task.pending_balance})"
            )

        # Validar cuenta financiera
        tenant_id = task.tenant_id
        from app.repositories.financial import CashAccountRepository
        account_repo = CashAccountRepository(self.db)
        cash_account = await account_repo.get_by_id(payment_in.cash_account_id, tenant_id)
        if not cash_account:
            raise ValueError("Cuenta de dinero no encontrada")
        if not cash_account.is_active:
            raise ValueError("La cuenta de dinero no está activa")

        created_by_id = await self._get_current_user_id()

        # Crear movimiento financiero
        movement = await self._create_payment_movement(
            task=task,
            amount=payment_in.amount,
            transaction_date=payment_in.transaction_date,
            cash_account_id=payment_in.cash_account_id,
            payment_method=payment_in.payment_method,
            reference=payment_in.reference,
            notes=payment_in.notes,
            created_by_id=created_by_id,
        )

        # Actualizar totales de la tarea
        new_total_paid = task.total_paid + payment_in.amount
        new_pending_balance = self._calculate_pending_balance(task.total_price, new_total_paid)
        new_payment_status = self._calculate_payment_status(task.total_price, new_total_paid)

        await self.repository.update_financial_info(
            task,
            total_paid=new_total_paid,
            pending_balance=new_pending_balance,
            payment_status=new_payment_status,
            last_payment_date=payment_in.transaction_date,
        )

        # Recargar tarea
        task = await self.repository.get_by_id(task_id)

        # Construir respuesta
        return TaskPaymentResponse(
            id=movement.id,
            task_id=task.id,
            amount=movement.amount,
            transaction_date=movement.transaction_date,
            recorded_at=movement.recorded_at,
            cash_account_id=movement.cash_account_id,
            cash_account_name=cash_account.name,
            payment_method=movement.payment_method.value,
            concept=movement.concept,
            description=movement.description,
            reference=payment_in.reference,
            created_by_id=movement.created_by_id,
            created_by_name=None,  # Se podría cargar el usuario si se necesita
            is_late_entry=movement.is_late_entry,
            status="completed",
        )

    async def get_task_payments(
        self,
        task_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> TaskPaymentListResponse:
        """Obtener historial de pagos de una tarea."""
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise ValueError("Tarea no encontrada")

        # Obtener movimientos financieros asociados a la tarea
        from app.repositories.financial import FinancialMovementRepository
        movement_repo = FinancialMovementRepository(self.db)

        movements, total = await movement_repo.get_all(
            tenant_id=task.tenant_id,
            page=page,
            page_size=page_size,
            filters=None,  # Filtrar por task_id en el repo
            sort_by="transaction_date",
            sort_order="desc",
        )

        # Filtrar solo los de esta tarea
        task_movements = [m for m in movements if m.task_id == task_id]
        total = len(task_movements)

        # Cargar cuentas para nombres
        from app.repositories.financial import CashAccountRepository
        account_repo = CashAccountRepository(self.db)

        payments = []
        for m in task_movements:
            account = await account_repo.get_by_id(m.cash_account_id, task.tenant_id)
            payments.append(TaskPaymentResponse(
                id=m.id,
                task_id=task.id,
                amount=m.amount,
                transaction_date=m.transaction_date,
                recorded_at=m.recorded_at,
                cash_account_id=m.cash_account_id,
                cash_account_name=account.name if account else None,
                payment_method=m.payment_method.value,
                concept=m.concept,
                description=m.description,
                reference=None,  # No se guarda en el movimiento directamente
                created_by_id=m.created_by_id,
                created_by_name=None,
                is_late_entry=m.is_late_entry,
                status="completed",
            ))

        total_pages = (total + page_size - 1) // page_size

        return TaskPaymentListResponse(
            payments=payments,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ============================================================
    # PAGOS PENDIENTES
    # ============================================================

    async def get_pending_payments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: PendingPaymentsFilters | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PendingPaymentsListResponse:
        """Obtener todas las tareas con saldo pendiente > 0."""
        filter_obj = None
        if filters:
            filter_obj = filters

        tasks, total = await self.repository.get_pending_payments(
            page=page,
            page_size=page_size,
            customer_id=getattr(filter_obj, 'customer_id', None) if filter_obj else None,
            status=getattr(filter_obj, 'status', None) if filter_obj else None,
            date_from=getattr(filter_obj, 'date_from', None) if filter_obj else None,
            date_to=getattr(filter_obj, 'date_to', None) if filter_obj else None,
            min_pending_balance=getattr(filter_obj, 'min_pending_balance', None) if filter_obj else None,
            max_pending_balance=getattr(filter_obj, 'max_pending_balance', None) if filter_obj else None,
            only_active=getattr(filter_obj, 'only_active', False) if filter_obj else False,
            only_completed=getattr(filter_obj, 'only_completed', False) if filter_obj else False,
            search=getattr(filter_obj, 'search', None) if filter_obj else None,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total + page_size - 1) // page_size

        # Cargar información de clientes
        task_responses = []
        for t in tasks:
            # Obtener info del cliente si existe
            customer_name = None
            customer_phone = None
            if t.customer_id:
                from app.repositories.customers import CustomerRepository
                customer_repo = CustomerRepository(self.db)
                customer = await customer_repo.get_by_id(t.customer_id)
                if customer:
                    customer_name = customer.full_name
                    customer_phone = customer.phone

            task_responses.append(PendingPaymentTaskResponse(
                id=t.id,
                title=t.title,
                description=t.description,
                status=t.status,
                priority=t.priority,
                due_date=t.due_date,
                customer_id=t.customer_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                total_price=t.total_price,
                total_paid=t.total_paid,
                pending_balance=t.pending_balance,
                payment_status=t.payment_status,
                last_payment_date=t.last_payment_date,
                created_at=t.created_at,
                completed_at=t.completed_at,
                updated_at=t.updated_at,
            ))

        return PendingPaymentsListResponse(
            tasks=task_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )