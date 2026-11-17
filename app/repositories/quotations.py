from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quotations import (
    Quotation,
    QuotationItem,
)


class QuotationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # QUOTATION NUMBER GENERATION
    # ============================================================
    async def generate_quotation_number(self, tenant_id: UUID) -> str:
        """Generar número único de cotización: COT-YYYY-NNNNN"""
        year = datetime.utcnow().year
        prefix = f"COT-{year}-"
        
        # Buscar el último número del año
        stmt = select(Quotation.quotation_number).where(
            Quotation.tenant_id == tenant_id,
            Quotation.quotation_number.like(f"{prefix}%")
        ).order_by(desc(Quotation.quotation_number)).limit(1)
        
        result = await self.db.execute(stmt)
        last_number = result.scalar_one_or_none()
        
        if last_number:
            try:
                last_seq = int(last_number.split("-")[-1])
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        
        return f"{prefix}{new_seq:05d}"

    # ============================================================
    # CREATE
    # ============================================================
    async def create(
        self,
        *,
        tenant_id: UUID,
        created_by_id: UUID,
        customer_id: UUID,
        issue_date: datetime,
        expiry_date: datetime,
        title: str,
        status: str = "draft",
        description: str | None = None,
        observations: str | None = None,
        payment_terms: str | None = None,
        delivery_terms: str | None = None,
        warranty_terms: str | None = None,
        profit_margin: Decimal = Decimal(0),
        quotation_number: str | None = None,
    ) -> Quotation:
        quotation = Quotation(
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            customer_id=customer_id,
            issue_date=issue_date,
            expiry_date=expiry_date,
            title=title,
            status=status,
            description=description,
            observations=observations,
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            warranty_terms=warranty_terms,
            profit_margin=profit_margin,
            quotation_number=quotation_number,
        )
        self.db.add(quotation)
        await self.db.flush()
        await self.db.refresh(quotation)
        return quotation

    async def create_item(
        self,
        quotation_id: UUID,
        *,
        item_type: str,
        sort_order: int = 0,
        name: str,
        description: str | None = None,
        sku: str | None = None,
        quantity: Decimal = Decimal(1),
        unit: str = "unidad",
        unit_cost: Decimal = Decimal(0),
        unit_price: Decimal = Decimal(0),
        discount_percent: Decimal = Decimal(0),
        extra_data: dict | None = None,
    ) -> QuotationItem:
        item = QuotationItem(
            quotation_id=quotation_id,
            item_type=item_type,
            sort_order=sort_order,
            name=name,
            description=description,
            sku=sku,
            quantity=quantity,
            unit=unit,
            unit_cost=unit_cost,
            unit_price=unit_price,
            discount_percent=discount_percent,
            extra_data=extra_data or {},
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    # ============================================================
    # GET
    # ============================================================
    async def get_by_id(self, quotation_id: UUID, tenant_id: UUID) -> Quotation | None:
        stmt = select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.tenant_id == tenant_id,
        ).options(
            selectinload(Quotation.customer),
            selectinload(Quotation.creator),
            selectinload(Quotation.items).selectinload(QuotationItem.quotation),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(self, quotation_number: str, tenant_id: UUID) -> Quotation | None:
        stmt = select(Quotation).where(
            Quotation.quotation_number == quotation_number,
            Quotation.tenant_id == tenant_id,
        ).options(
            selectinload(Quotation.customer),
            selectinload(Quotation.creator),
            selectinload(Quotation.items),
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
        status: str | None = None,
        customer_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "issue_date",
        sort_order: str = "desc",
    ) -> tuple[Sequence[Quotation], int]:
        stmt = select(Quotation).where(Quotation.tenant_id == tenant_id)
        count_stmt = select(func.count()).where(Quotation.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(Quotation.status == status)
            count_stmt = count_stmt.where(Quotation.status == status)
        
        if customer_id:
            stmt = stmt.where(Quotation.customer_id == customer_id)
            count_stmt = count_stmt.where(Quotation.customer_id == customer_id)

        if search:
            search_filter = or_(
                Quotation.quotation_number.ilike(f"%{search}%"),
                Quotation.title.ilike(f"%{search}%"),
                Quotation.description.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Sorting
        sort_column = getattr(Quotation, sort_by, Quotation.issue_date)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        quotations = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return quotations, total

    # ============================================================
    # UPDATE
    # ============================================================
    async def update(
        self,
        quotation: Quotation,
        *,
        customer_id: UUID | None = None,
        issue_date: datetime | None = None,
        expiry_date: datetime | None = None,
        title: str | None = None,
        description: str | None = None,
        observations: str | None = None,
        payment_terms: str | None = None,
        delivery_terms: str | None = None,
        warranty_terms: str | None = None,
        profit_margin: Decimal | None = None,
        status: str | None = None,
    ) -> Quotation:
        if customer_id is not None:
            quotation.customer_id = customer_id
        if issue_date is not None:
            quotation.issue_date = issue_date
        if expiry_date is not None:
            quotation.expiry_date = expiry_date
        if title is not None:
            quotation.title = title
        if description is not None:
            quotation.description = description
        if observations is not None:
            quotation.observations = observations
        if payment_terms is not None:
            quotation.payment_terms = payment_terms
        if delivery_terms is not None:
            quotation.delivery_terms = delivery_terms
        if warranty_terms is not None:
            quotation.warranty_terms = warranty_terms
        if profit_margin is not None:
            quotation.profit_margin = profit_margin
        if status is not None:
            quotation.status = status
            if status == "accepted":
                quotation.accepted_at = datetime.utcnow()
            elif status == "rejected":
                quotation.rejected_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(quotation)
        return quotation

    # ============================================================
    # ITEMS
    # ============================================================
    async def get_items(self, quotation_id: UUID) -> Sequence[QuotationItem]:
        stmt = select(QuotationItem).where(
            QuotationItem.quotation_id == quotation_id
        ).order_by(QuotationItem.sort_order)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_item_by_id(self, item_id: UUID, quotation_id: UUID) -> QuotationItem | None:
        stmt = select(QuotationItem).where(
            QuotationItem.id == item_id,
            QuotationItem.quotation_id == quotation_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_item(
        self,
        item: QuotationItem,
        *,
        item_type: str | None = None,
        name: str | None = None,
        description: str | None = None,
        sku: str | None = None,
        quantity: Decimal | None = None,
        unit: str | None = None,
        unit_cost: Decimal | None = None,
        unit_price: Decimal | None = None,
        discount_percent: Decimal | None = None,
        metadata: dict | None = None,
        sort_order: int | None = None,
    ) -> QuotationItem:
        if item_type is not None:
            item.item_type = item_type
        if name is not None:
            item.name = name
        if description is not None:
            item.description = description
        if sku is not None:
            item.sku = sku
        if quantity is not None:
            item.quantity = quantity
        if unit is not None:
            item.unit = unit
        if unit_cost is not None:
            item.unit_cost = unit_cost
        if unit_price is not None:
            item.unit_price = unit_price
        if discount_percent is not None:
            item.discount_percent = discount_percent
        if metadata is not None:
            item.extra_data = metadata
        if sort_order is not None:
            item.sort_order = sort_order

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete_item(self, item: QuotationItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def delete_all_items(self, quotation_id: UUID) -> None:
        stmt = select(QuotationItem).where(QuotationItem.quotation_id == quotation_id)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        for item in items:
            await self.db.delete(item)
        await self.db.flush()

    # ============================================================
    # CALCULATIONS
    # ============================================================
    async def calculate_totals(self, quotation_id: UUID) -> dict:
        """Calcular totales de la cotización basándose en los ítems"""
        items = await self.get_items(quotation_id)
        
        subtotal = Decimal(0)
        total_cost = Decimal(0)
        
        for item in items:
            line_subtotal = item.quantity * item.unit_price
            discount_amount = line_subtotal * (item.discount_percent / Decimal(100))
            line_total = line_subtotal - discount_amount
            subtotal += line_total
            total_cost += item.quantity * item.unit_cost
        
        return {
            "subtotal": subtotal,
            "total_cost": total_cost,
            "items_count": len(items),
        }

    async def recalculate_totals(self, quotation: Quotation) -> Quotation:
        """Recalcular y actualizar totales de la cotización"""
        calc = await self.calculate_totals(quotation.id)
        
        quotation.subtotal = calc["subtotal"]
        # tax_amount, discount_amount, total se pueden calcular aquí o en el service
        # Por ahora solo actualizamos subtotal
        await self.db.flush()
        await self.db.refresh(quotation)
        return quotation

    # ============================================================
    # STATUS CHANGES
    # ============================================================
    async def accept(self, quotation: Quotation) -> Quotation:
        quotation.status = "accepted"
        quotation.accepted_at = datetime.utcnow()
        await self.db.flush()
        # No refresh to avoid loading strategy conflicts
        return quotation

    async def reject(self, quotation: Quotation) -> Quotation:
        quotation.status = "rejected"
        quotation.rejected_at = datetime.utcnow()
        await self.db.flush()
        # No refresh to avoid loading strategy conflicts
        return quotation

    async def send(self, quotation: Quotation) -> Quotation:
        quotation.status = "sent"
        await self.db.flush()
        # No refresh to avoid loading strategy conflicts
        return quotation

    async def back_to_draft(self, quotation: Quotation) -> Quotation:
        quotation.status = "draft"
        quotation.accepted_at = None
        quotation.rejected_at = None
        await self.db.flush()
        # No refresh to avoid loading strategy conflicts
        return quotation

    # ============================================================
    # DUPLICATE
    # ============================================================
    async def duplicate(
        self,
        quotation: Quotation,
        new_customer_id: UUID | None = None,
        new_expiry_date: datetime | None = None,
        new_title: str | None = None,
        new_created_by_id: UUID | None = None,
    ) -> Quotation:
        # Obtener items
        await self.get_items(quotation.id)
        
        # Crear nueva cotización
        new_quotation = Quotation(
            tenant_id=quotation.tenant_id,
            created_by_id=new_created_by_id or quotation.created_by_id,
            customer_id=new_customer_id or quotation.customer_id,
            issue_date=datetime.utcnow(),
            expiry_date=quotation.expiry_date,
            title=new_title or f"{quotation.title} (Copia)",
            description=quotation.description,
            observations=quotation.observations,
            payment_terms=quotation.payment_terms,
            delivery_terms=quotation.delivery_terms,
            warranty_terms=quotation.warranty_terms,
            profit_margin=quotation.profit_margin,
            status="draft",
        )
        
        self.db.add(new_quotation)
        await self.db.flush()
        
        # Duplicar items
        for item in quotation.items:
            QuotationItem(
                quotation_id=new_quotation.id,
                item_type=item.item_type,
                sort_order=item.sort_order,
                name=item.name,
                description=item.description,
                sku=item.sku,
                quantity=item.quantity,
                unit=item.unit,
                unit_cost=item.unit_cost,
                unit_price=item.unit_price,
                discount_percent=item.discount_percent,
                extra_data=item.extra_data,
            )
            self.db.add(item)
        
        await self.db.flush()
        await self.db.refresh(new_quotation)
        return new_quotation

    # ============================================================
    # DELETE
    # ============================================================
    async def delete(self, quotation: Quotation) -> None:
        await self.db.delete(quotation)
        await self.db.flush()