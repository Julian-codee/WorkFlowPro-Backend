from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.quotations import Quotation
from app.repositories.quotations import QuotationRepository
from app.repositories.tasks import TaskRepository
from app.schemas.quotations import (
    QuotationCalculationRequest,
    QuotationCalculationsResponse,
    QuotationCreate,
    QuotationItemResponse,
    QuotationListResponse,
    QuotationResponse,
    QuotationUpdate,
)
from app.schemas.quotations import (
    QuotationConvertToTaskRequest as SchemaQuotationConvertToTaskRequest,
)
from app.schemas.quotations import (
    QuotationDuplicateRequest as SchemaQuotationDuplicateRequest,
)
from app.schemas.quotations import (
    QuotationItemCreate as SchemaQuotationItemCreate,
)
from app.schemas.quotations import (
    QuotationItemUpdate as SchemaQuotationItemUpdate,
)
from app.schemas.quotations import (
    QuotationStatus as SchemaQuotationStatus,
)
from app.schemas.quotations import (
    QuotationStatusUpdate as SchemaQuotationStatusUpdate,
)
from app.schemas.tasks import TaskResponse
from app.services.tasks_service import TaskService


class QuotationService:
    def __init__(self, db):
        self.repository = QuotationRepository(db)
        self.db = db

    # ============================================================
    # CALCULATIONS
    # ============================================================
    async def calculate_totals(
        self,
        items: list[SchemaQuotationItemCreate],
        profit_margin: Decimal = Decimal(0),
        tax_rate: Decimal = Decimal(19),
        discount_amount: Decimal = Decimal(0),
    ) -> QuotationCalculationsResponse:
        """Calcular totales de la cotización basándose en los ítems"""
        subtotal = Decimal(0)
        total_cost = Decimal(0)
        
        for item in items:
            line_subtotal = item.quantity * item.unit_price
            discount_amount_item = line_subtotal * (item.discount_percent / Decimal(100))
            line_total = line_subtotal - discount_amount_item
            subtotal += line_total
            total_cost += item.quantity * item.unit_cost
        
        # Aplicar descuento global
        subtotal_after_discount = subtotal - discount_amount
        
        # Calcular impuesto
        tax_amount = subtotal_after_discount * (tax_rate / Decimal(100))
        
        # Total
        total = subtotal_after_discount + tax_amount
        
        # Margen de utilidad sobre el total
        profit_amount = total * (profit_margin / Decimal(100))
        total_with_profit = total + profit_amount
        
        gross_profit = total_with_profit - sum(item.quantity * item.unit_cost for item in items)
        
        return QuotationCalculationsResponse(
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total=total_with_profit,
            profit_margin=profit_margin,
            items_count=len(items),
            total_cost=sum(item.quantity * item.unit_cost for item in items),
            gross_profit=gross_profit,
        )

    async def preview_calculation(self, request: QuotationCalculationRequest) -> QuotationCalculationsResponse:
        """Vista previa de cálculos sin guardar"""
        return await self.calculate_totals(
            items=request.items,
            profit_margin=request.profit_margin,
            tax_rate=request.tax_rate,
            discount_amount=request.discount_amount,
        )

    # ============================================================
    # CREATE
    # ============================================================
    async def create_quotation(
        self,
        *,
        quotation_in: QuotationCreate,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> QuotationResponse:
        # Generar número de cotización
        quotation_number = await self.repository.generate_quotation_number(tenant_id)
        
        # Crear cotización
        quotation = await self.repository.create(
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            customer_id=quotation_in.customer_id,
            issue_date=quotation_in.issue_date,
            expiry_date=quotation_in.expiry_date,
            title=quotation_in.title,
            status="draft",
            description=quotation_in.description,
            observations=quotation_in.observations,
            payment_terms=quotation_in.payment_terms,
            delivery_terms=quotation_in.delivery_terms,
            warranty_terms=quotation_in.warranty_terms,
            profit_margin=quotation_in.profit_margin,
            quotation_number=quotation_number,
        )
        
        # Crear items
        for i, item_in in enumerate(quotation_in.items):
            await self.repository.create_item(
                quotation_id=quotation.id,
                item_type=item_in.item_type.value,
                sort_order=item_in.sort_order,
                name=item_in.name,
                description=item_in.description,
                sku=item_in.sku,
                quantity=item_in.quantity,
                unit=item_in.unit,
                unit_cost=item_in.unit_cost,
                unit_price=item_in.unit_price,
                discount_percent=item_in.discount_percent,
                extra_data=item_in.extra_data,
            )
        
        # Recargar con relaciones
        quotation = await self.repository.get_by_id(quotation.id, quotation.tenant_id)
        
        # Calcular totales
        await self._recalculate_and_update(quotation)
        
        return QuotationResponse.model_validate(quotation)

    # ============================================================
    # GET
    # ============================================================
    async def get_quotation(self, quotation_id: UUID, tenant_id: UUID) -> QuotationResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        return QuotationResponse.model_validate(quotation)

    async def get_quotation_by_number(self, quotation_number: str, tenant_id: UUID) -> QuotationResponse | None:
        quotation = await self.repository.get_by_number(quotation_number, tenant_id)
        if not quotation:
            return None
        return QuotationResponse.model_validate(quotation)

    # ============================================================
    # LIST
    # ============================================================
    async def get_quotations(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        customer_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "issue_date",
        sort_order: str = "desc",
    ) -> QuotationListResponse:
        quotations, total = await self.repository.get_all(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            status=status,
            customer_id=customer_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return QuotationListResponse(
            quotations=[QuotationResponse.model_validate(q) for q in quotations],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ============================================================
    # UPDATE
    # ============================================================
    async def update_quotation(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        quotation_in: QuotationUpdate,
    ) -> QuotationResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        
        updated = await self.repository.update(
            quotation,
            customer_id=quotation_in.customer_id,
            issue_date=quotation_in.issue_date,
            expiry_date=quotation_in.expiry_date,
            title=quotation_in.title,
            description=quotation_in.description,
            observations=quotation_in.observations,
            payment_terms=quotation_in.payment_terms,
            delivery_terms=quotation_in.delivery_terms,
            warranty_terms=quotation_in.warranty_terms,
            profit_margin=quotation_in.profit_margin,
            status=quotation_in.status.value if quotation_in.status else None,
        )
        
        return QuotationResponse.model_validate(updated)

    # ============================================================
    # ITEMS MANAGEMENT
    # ============================================================
    async def add_item(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        item_in: SchemaQuotationItemCreate,
    ) -> QuotationItemResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        
        item = await self.repository.create_item(
            quotation_id=quotation_id,
            item_type=item_in.item_type.value,
            sort_order=item_in.sort_order,
            name=item_in.name,
            description=item_in.description,
            sku=item_in.sku,
            quantity=item_in.quantity,
            unit=item_in.unit,
            unit_cost=item_in.unit_cost,
            unit_price=item_in.unit_price,
            discount_percent=item_in.discount_percent,
            metadata=item_in.metadata,
        )
        
        await self._recalculate_and_update(quotation)
        return QuotationItemResponse.model_validate(item)

    async def update_item(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        item_id: UUID,
        item_in: SchemaQuotationItemUpdate,
    ) -> QuotationItemResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        
        item = await self.repository.get_item_by_id(item_id, quotation_id)
        if not item:
            return None
        
        updated = await self.repository.update_item(
            item,
            item_type=item_in.item_type.value if item_in.item_type else None,
            name=item_in.name,
            description=item_in.description,
            sku=item_in.sku,
            quantity=item_in.quantity,
            unit=item_in.unit,
            unit_cost=item_in.unit_cost,
            unit_price=item_in.unit_price,
            discount_percent=item_in.discount_percent,
            metadata=item_in.metadata,
            sort_order=item_in.sort_order,
        )
        
        await self._recalculate_and_update(quotation)
        return QuotationItemResponse.model_validate(updated)

    async def delete_item(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        item_id: UUID,
    ) -> bool:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return False
        
        item = await self.repository.get_item_by_id(item_id, quotation_id)
        if not item:
            return False
        
        await self.repository.delete_item(item)
        await self._recalculate_and_update(quotation)
        return True

    async def reorder_items(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        item_orders: list[dict],  # [{"id": uuid, "sort_order": int}, ...]
    ) -> bool:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return False
        
        for order in item_orders:
            item = await self.repository.get_item_by_id(UUID(order["id"]), quotation_id)
            if item:
                await self.repository.update_item(item, sort_order=order["sort_order"])
        
        return True

    # ============================================================
    # STATUS CHANGES
    # ============================================================
    async def update_status(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        status_in: SchemaQuotationStatusUpdate,
    ) -> QuotationResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        
        if status_in.status == SchemaQuotationStatus.ACCEPTED:
            quotation = await self.repository.accept(quotation)
        elif status_in.status == SchemaQuotationStatus.REJECTED:
            quotation = await self.repository.reject(quotation)
        elif status_in.status == SchemaQuotationStatus.SENT:
            quotation = await self.repository.send(quotation)
        elif status_in.status == SchemaQuotationStatus.DRAFT:
            quotation = await self.repository.back_to_draft(quotation)
        
        return QuotationResponse.model_validate(quotation)

    async def send_quotation(self, quotation_id: UUID, tenant_id: UUID) -> QuotationResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        quotation = await self.repository.send(quotation)
        quotation.updated_at = datetime.utcnow()
        return QuotationResponse.model_validate(quotation)

    async def accept_quotation(self, quotation_id: UUID, tenant_id: UUID) -> QuotationResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        quotation = await self.repository.accept(quotation)
        # Manually update updated_at since we don't refresh to avoid loading strategy conflicts
        quotation.updated_at = datetime.utcnow()
        return QuotationResponse.model_validate(quotation)

    async def reject_quotation(self, quotation_id: UUID, tenant_id: UUID) -> QuotationResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        quotation = await self.repository.reject(quotation)
        quotation.updated_at = datetime.utcnow()
        return QuotationResponse.model_validate(quotation)

    # ============================================================
    # DUPLICATE
    # ============================================================
    async def duplicate_quotation(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        duplicate_in: SchemaQuotationDuplicateRequest,
        created_by_id: UUID,
    ) -> QuotationResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        
        new_quotation = await self.repository.duplicate(
            quotation,
            new_customer_id=duplicate_in.new_customer_id,
            new_expiry_date=duplicate_in.new_expiry_date,
            new_title=duplicate_in.new_title,
            new_created_by_id=created_by_id,
        )
        
        return QuotationResponse.model_validate(new_quotation)

    # ============================================================
    # CONVERT TO TASK
    # ============================================================
    async def convert_to_task(
        self,
        quotation_id: UUID,
        tenant_id: UUID,
        convert_in: SchemaQuotationConvertToTaskRequest,
        created_by_id: UUID,
    ) -> TaskResponse | None:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return None
        
        if quotation.status != "accepted":
            raise ValueError("Solo se pueden convertir cotizaciones aceptadas")
        
        if quotation.converted_task_id:
            raise ValueError("Esta cotización ya fue convertida a tarea")
        
        # Crear tarea desde la cotización
        task_repo = TaskRepository(self.db)
        task = await task_repo.create(
            title=convert_in.task_title or quotation.title,
            description=convert_in.task_description or f"Tarea generada desde cotización {quotation.quotation_number}\n\n{quotation.description or ''}",
            priority=convert_in.task_priority.value if convert_in.task_priority else "medium",
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            assignee_id=convert_in.assignee_id,
        )
        
        # Vincular cotización a la tarea
        quotation.converted_task_id = task.id
        await self.db.flush()
        
        # Recargar
        await self.db.refresh(quotation)
        
        task_service = TaskService(self.db)
        return await task_service.get_task(task.id)

    # ============================================================
    # DELETE
    # ============================================================
    async def delete_quotation(self, quotation_id: UUID, tenant_id: UUID) -> bool:
        quotation = await self.repository.get_by_id(quotation_id, tenant_id)
        if not quotation:
            return False
        
        await self.repository.delete(quotation)
        return True

    # ============================================================
    # HELPER
    # ============================================================
    async def _recalculate_and_update(self, quotation: Quotation) -> Quotation:
        items = await self.repository.get_items(quotation.id)
        
        subtotal = Decimal(0)
        total_cost = Decimal(0)
        
        for item in items:
            line_subtotal = item.quantity * item.unit_price
            discount_amount = line_subtotal * (item.discount_percent / Decimal(100))
            line_total = line_subtotal - discount_amount
            subtotal += line_total
            total_cost += item.quantity * item.unit_cost
        
        # Actualizar cotización
        quotation.subtotal = subtotal
        # tax_amount, discount_amount, total se pueden calcular aquí
        # Por simplicidad, el total = subtotal (el frontend puede calcular más)
        quotation.total = subtotal
        
        await self.db.flush()
        await self.db.refresh(quotation)
        return quotation