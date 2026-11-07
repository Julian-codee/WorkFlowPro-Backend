from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customers import (
    Customer,
    CustomerAuditLog,
    CustomerNote,
    CustomerStatus,
    CustomerType,
)
from app.schemas.customers import CustomerSearchFilters


class CustomerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # CREATE
    # ============================================================
    async def create(
        self,
        *,
        customer_type: CustomerType,
        tenant_id: UUID,
        created_by_id: UUID,
        phone: str,
        status: CustomerStatus = CustomerStatus.ACTIVE,
        phone_secondary: str | None = None,
        whatsapp: str | None = None,
        email: str | None = None,
        address: str | None = None,
        city: str | None = None,
        department: str | None = None,
        country: str | None = "Colombia",
        postal_code: str | None = None,
        internal_notes: str | None = None,
        # Natural
        first_name: str | None = None,
        last_name: str | None = None,
        identification_type: str | None = None,
        identification_number: str | None = None,
        # Legal
        business_name: str | None = None,
        trade_name: str | None = None,
        tax_id_type: str | None = None,
        tax_id_number: str | None = None,
        verification_digit: str | None = None,
        legal_rep_name: str | None = None,
        legal_rep_id: str | None = None,
        main_contact_name: str | None = None,
        fiscal_address: str | None = None,
        commercial_address: str | None = None,
        website: str | None = None,
        economic_activity: str | None = None,
    ) -> Customer:
        customer = Customer(
            customer_type=customer_type,
            status=status,
            phone=phone,
            phone_secondary=phone_secondary,
            whatsapp=whatsapp,
            email=email,
            address=address,
            city=city,
            department=department,
            country=country,
            postal_code=postal_code,
            internal_notes=internal_notes,
            first_name=first_name,
            last_name=last_name,
            identification_type=identification_type,
            identification_number=identification_number,
            business_name=business_name,
            trade_name=trade_name,
            tax_id_type=tax_id_type,
            tax_id_number=tax_id_number,
            verification_digit=verification_digit,
            legal_rep_name=legal_rep_name,
            legal_rep_id=legal_rep_id,
            main_contact_name=main_contact_name,
            fiscal_address=fiscal_address,
            commercial_address=commercial_address,
            website=website,
            economic_activity=economic_activity,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
        )
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)
        return customer

    # ============================================================
    # DUPLICATE CHECKS
    # ============================================================
    async def check_duplicates(
        self,
        tenant_id: UUID,
        *,
        identification_number: str | None = None,
        tax_id_number: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        exclude_id: UUID | None = None,
    ) -> dict:
        """Verificar posibles duplicados"""
        warnings = []
        
        if identification_number:
            stmt = select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.identification_number == identification_number,
            )
            if exclude_id:
                stmt = stmt.where(Customer.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                warnings.append({
                    "field": "identification_number",
                    "message": "Ya existe un cliente con este número de identificación",
                    "type": "duplicate",
                })
        
        if tax_id_number:
            stmt = select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.tax_id_number == tax_id_number,
            )
            if exclude_id:
                stmt = stmt.where(Customer.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                warnings.append({
                    "field": "tax_id_number",
                    "message": "Ya existe un cliente con este NIT",
                    "type": "duplicate",
                })
        
        if email:
            stmt = select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.email.ilike(email),
            )
            if exclude_id:
                stmt = stmt.where(Customer.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                warnings.append({
                    "field": "email",
                    "message": "Ya existe un cliente con este correo electrónico",
                    "type": "warning",
                })
        
        if phone:
            stmt = select(Customer).where(
                Customer.tenant_id == tenant_id,
                or_(
                    Customer.phone == phone,
                    Customer.phone_secondary == phone,
                    Customer.whatsapp == phone,
                ),
            )
            if exclude_id:
                stmt = stmt.where(Customer.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                warnings.append({
                    "field": "phone",
                    "message": "Ya existe un cliente con este teléfono",
                    "type": "warning",
                })
        
        return {"warnings": warnings}

    # ============================================================
    # GET BY ID
    # ============================================================
    async def get_by_id(self, customer_id: UUID, tenant_id: UUID) -> Customer | None:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        ).options(
            selectinload(Customer.creator),
            selectinload(Customer.tenant),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_relations(self, customer_id: UUID, tenant_id: UUID) -> Customer | None:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        ).options(
            selectinload(Customer.creator),
            selectinload(Customer.tenant),
            selectinload(Customer.notes),
            selectinload(Customer.audit_logs),
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
        filters: CustomerSearchFilters | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[Sequence[Customer], int]:
        stmt = select(Customer).where(Customer.tenant_id == tenant_id)
        count_stmt = select(func.count()).where(Customer.tenant_id == tenant_id)

        if filters:
            # Search query
            if filters.query:
                search_filter = or_(
                    Customer.first_name.ilike(f"%{filters.query}%"),
                    Customer.last_name.ilike(f"%{filters.query}%"),
                    Customer.business_name.ilike(f"%{filters.query}%"),
                    Customer.trade_name.ilike(f"%{filters.query}%"),
                    Customer.identification_number.ilike(f"%{filters.query}%"),
                    Customer.tax_id_number.ilike(f"%{filters.query}%"),
                    Customer.email.ilike(f"%{filters.query}%"),
                    Customer.phone.ilike(f"%{filters.query}%"),
                    Customer.whatsapp.ilike(f"%{filters.query}%"),
                )
                stmt = stmt.where(search_filter)
                count_stmt = count_stmt.where(search_filter)

            # Filters
            if filters.customer_type:
                stmt = stmt.where(Customer.customer_type == filters.customer_type)
                count_stmt = count_stmt.where(Customer.customer_type == filters.customer_type)

            if filters.status:
                stmt = stmt.where(Customer.status == filters.status)
                count_stmt = count_stmt.where(Customer.status == filters.status)

            if filters.city:
                stmt = stmt.where(Customer.city.ilike(f"%{filters.city}%"))
                count_stmt = count_stmt.where(Customer.city.ilike(f"%{filters.city}%"))

            if filters.department:
                stmt = stmt.where(Customer.department.ilike(f"%{filters.department}%"))
                count_stmt = count_stmt.where(Customer.department.ilike(f"%{filters.department}%"))

            if filters.country:
                stmt = stmt.where(Customer.country.ilike(f"%{filters.country}%"))
                count_stmt = count_stmt.where(Customer.country.ilike(f"%{filters.country}%"))

            if filters.registered_from:
                stmt = stmt.where(Customer.created_at >= filters.registered_from)
                count_stmt = count_stmt.where(Customer.created_at >= filters.registered_from)

            if filters.registered_to:
                stmt = stmt.where(Customer.created_at <= filters.registered_to)
                count_stmt = count_stmt.where(Customer.created_at <= filters.registered_to)

            # Boolean filters (these would need joins with other tables)
            # For now, we'll note they need implementation with joins
            # if filters.has_active_jobs:
            # if filters.has_pending_payments:
            # if filters.has_pending_quotes:

        # Sorting
        sort_column = getattr(Customer, sort_by, Customer.created_at)
        if sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(stmt)
        customers = result.scalars().all()

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        return customers, total

    # ============================================================
    # UPDATE
    # ============================================================
    async def update(
        self,
        customer: Customer,
        *,
        status: str | None = None,
        phone: str | None = None,
        phone_secondary: str | None = None,
        whatsapp: str | None = None,
        email: str | None = None,
        address: str | None = None,
        city: str | None = None,
        department: str | None = None,
        country: str | None = None,
        postal_code: str | None = None,
        internal_notes: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        identification_type: str | None = None,
        identification_number: str | None = None,
        business_name: str | None = None,
        trade_name: str | None = None,
        tax_id_type: str | None = None,
        tax_id_number: str | None = None,
        verification_digit: str | None = None,
        legal_rep_name: str | None = None,
        legal_rep_id: str | None = None,
        main_contact_name: str | None = None,
        fiscal_address: str | None = None,
        commercial_address: str | None = None,
        website: str | None = None,
        economic_activity: str | None = None,
    ) -> Customer:
        changes = {}
        
        if status is not None:
            customer.status = CustomerStatus(status)
            changes["status"] = status
        if phone is not None:
            customer.phone = phone
            changes["phone"] = phone
        if phone_secondary is not None:
            customer.phone_secondary = phone_secondary
            changes["phone_secondary"] = phone_secondary
        if whatsapp is not None:
            customer.whatsapp = whatsapp
            changes["whatsapp"] = whatsapp
        if email is not None:
            customer.email = email
            changes["email"] = email
        if address is not None:
            customer.address = address
            changes["address"] = address
        if city is not None:
            customer.city = city
            changes["city"] = city
        if department is not None:
            customer.department = department
            changes["department"] = department
        if country is not None:
            customer.country = country
            changes["country"] = country
        if postal_code is not None:
            customer.postal_code = postal_code
            changes["postal_code"] = postal_code
        if internal_notes is not None:
            customer.internal_notes = internal_notes
            changes["internal_notes"] = internal_notes
        if first_name is not None:
            customer.first_name = first_name
            changes["first_name"] = first_name
        if last_name is not None:
            customer.last_name = last_name
            changes["last_name"] = last_name
        if identification_type is not None:
            customer.identification_type = identification_type
            changes["identification_type"] = identification_type
        if identification_number is not None:
            customer.identification_number = identification_number
            changes["identification_number"] = identification_number
        if business_name is not None:
            customer.business_name = business_name
            changes["business_name"] = business_name
        if trade_name is not None:
            customer.trade_name = trade_name
            changes["trade_name"] = trade_name
        if tax_id_type is not None:
            customer.tax_id_type = tax_id_type
            changes["tax_id_type"] = tax_id_type
        if tax_id_number is not None:
            customer.tax_id_number = tax_id_number
            changes["tax_id_number"] = tax_id_number
        if verification_digit is not None:
            customer.verification_digit = verification_digit
            changes["verification_digit"] = verification_digit
        if legal_rep_name is not None:
            customer.legal_rep_name = legal_rep_name
            changes["legal_rep_name"] = legal_rep_name
        if legal_rep_id is not None:
            customer.legal_rep_id = legal_rep_id
            changes["legal_rep_id"] = legal_rep_id
        if main_contact_name is not None:
            customer.main_contact_name = main_contact_name
            changes["main_contact_name"] = main_contact_name
        if fiscal_address is not None:
            customer.fiscal_address = fiscal_address
            changes["fiscal_address"] = fiscal_address
        if commercial_address is not None:
            customer.commercial_address = commercial_address
            changes["commercial_address"] = commercial_address
        if website is not None:
            customer.website = website
            changes["website"] = website
        if economic_activity is not None:
            customer.economic_activity = economic_activity
            changes["economic_activity"] = economic_activity

        await self.db.flush()
        await self.db.refresh(customer)
        return customer

    # ============================================================
    # UPDATE STATUS
    # ============================================================
    async def update_status(self, customer: Customer, status: CustomerStatus) -> Customer:
        customer.status = status
        await self.db.flush()
        await self.db.refresh(customer)
        return customer

    # ============================================================
    # DELETE (Soft delete - archive)
    # ============================================================
    async def delete(self, customer: Customer) -> None:
        await self.db.delete(customer)
        await self.db.flush()

    # ============================================================
    # NOTES
    # ============================================================
    async def create_note(
        self,
        customer_id: UUID,
        author_id: UUID,
        content: str,
    ) -> CustomerNote:
        note = CustomerNote(
            customer_id=customer_id,
            author_id=author_id,
            content=content,
        )
        self.db.add(note)
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def get_notes(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[CustomerNote], int]:
        stmt = select(CustomerNote).where(CustomerNote.customer_id == customer_id)
        count_stmt = select(func.count()).where(CustomerNote.customer_id == customer_id)
        
        stmt = stmt.order_by(desc(CustomerNote.created_at))
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        result = await self.db.execute(stmt)
        notes = result.scalars().all()
        
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        return notes, total

    async def get_note_by_id(self, note_id: UUID, customer_id: UUID, tenant_id: UUID) -> CustomerNote | None:
        stmt = select(CustomerNote).where(
            CustomerNote.id == note_id,
            CustomerNote.customer_id == customer_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_note(self, note: CustomerNote, content: str) -> CustomerNote:
        note.content = content
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def delete_note(self, note: CustomerNote) -> None:
        await self.db.delete(note)
        await self.db.flush()

    # ============================================================
    # AUDIT LOGS
    # ============================================================
    async def create_audit_log(
        self,
        customer_id: UUID,
        user_id: UUID,
        action: str,
        old_data: dict | None = None,
        new_data: dict | None = None,
        changed_fields: list | None = None,
    ) -> CustomerAuditLog:
        audit = CustomerAuditLog(
            customer_id=customer_id,
            user_id=user_id,
            action=action,
            old_data=old_data,
            new_data=new_data,
            changed_fields=changed_fields or [],
        )
        self.db.add(audit)
        await self.db.flush()
        await self.db.refresh(audit)
        return audit

    async def get_audit_logs(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[CustomerAuditLog], int]:
        stmt = select(CustomerAuditLog).where(CustomerAuditLog.customer_id == customer_id)
        count_stmt = select(func.count()).where(CustomerAuditLog.customer_id == customer_id)
        
        stmt = stmt.order_by(desc(CustomerAuditLog.created_at))
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        return logs, total

    # ============================================================
    # FINANCIAL SUMMARY (placeholder - needs integration with jobs/payments)
    # ============================================================
    async def get_financial_summary(self, customer_id: UUID, tenant_id: UUID) -> dict:
        """Placeholder - se implementará cuando existan los módulos de trabajos/pagos"""
        return {
            "total_contracted": Decimal(0),
            "total_invoiced": Decimal(0),
            "total_paid": Decimal(0),
            "pending_balance": Decimal(0),
            "jobs_count": 0,
            "active_jobs_count": 0,
            "completed_jobs_count": 0,
            "pending_quotes_count": 0,
            "last_transaction_at": None,
            "last_job_at": None,
        }