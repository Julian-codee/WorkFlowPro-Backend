from collections.abc import Sequence
from uuid import UUID

from app.models.customers import (
    Customer,
    CustomerAuditAction,
    CustomerStatus,
    CustomerType,
)
from app.repositories.customers import CustomerRepository
from app.schemas.customers import (
    CustomerAuditLogResponse,
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


class CustomerService:
    def __init__(self, db):
        self.repository = CustomerRepository(db)
        self.db = db

    # ============================================================
    # CREATE
    # ============================================================
    async def create_customer(
        self,
        *,
        customer_in: CustomerNaturalCreate | CustomerLegalCreate,
        tenant_id: UUID,
        created_by_id: UUID,
    ) -> CustomerResponse:
        # Check duplicates - use getattr with defaults for union type
        identification_number = getattr(customer_in, 'identification_number', None)
        tax_id_number = getattr(customer_in, 'tax_id_number', None)
        
        # Check duplicates
        dup_check = await self.repository.check_duplicates(
            tenant_id,
            identification_number=identification_number,
            tax_id_number=tax_id_number,
            email=customer_in.email,
            phone=customer_in.phone,
        )
        
        # Convert enums to strings for repository
        customer_type = customer_in.customer_type.value
        status = customer_in.status.value
        identification_type = getattr(customer_in, 'identification_type', None)
        identification_type = identification_type.value if identification_type else None
        tax_id_type = getattr(customer_in, 'tax_id_type', None)
        tax_id_type = tax_id_type.value if tax_id_type else None
        
        customer = await self.repository.create(
            customer_type=CustomerType(customer_in.customer_type.value),
            status=CustomerStatus(customer_in.status.value),
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            phone=customer_in.phone,
            phone_secondary=getattr(customer_in, 'phone_secondary', None),
            whatsapp=getattr(customer_in, 'whatsapp', None),
            email=customer_in.email,
            address=getattr(customer_in, 'address', None),
            city=getattr(customer_in, 'city', None),
            department=getattr(customer_in, 'department', None),
            country=getattr(customer_in, 'country', 'Colombia'),
            postal_code=getattr(customer_in, 'postal_code', None),
            internal_notes=getattr(customer_in, 'internal_notes', None),
            # Natural
            first_name=getattr(customer_in, 'first_name', None),
            last_name=getattr(customer_in, 'last_name', None),
            identification_type=identification_type,
            identification_number=getattr(customer_in, 'identification_number', None),
            # Legal
            business_name=getattr(customer_in, 'business_name', None),
            trade_name=getattr(customer_in, 'trade_name', None),
            tax_id_type=tax_id_type,
            tax_id_number=getattr(customer_in, 'tax_id_number', None),
            verification_digit=getattr(customer_in, 'verification_digit', None),
            legal_rep_name=getattr(customer_in, 'legal_rep_name', None),
            legal_rep_id=getattr(customer_in, 'legal_rep_id', None),
            main_contact_name=getattr(customer_in, 'main_contact_name', None),
            fiscal_address=getattr(customer_in, 'fiscal_address', None),
            commercial_address=getattr(customer_in, 'commercial_address', None),
            website=getattr(customer_in, 'website', None),
            economic_activity=getattr(customer_in, 'economic_activity', None),
        )
        
        # Create audit log
        await self.repository.create_audit_log(
            customer_id=customer.id,
            user_id=created_by_id,
            action=CustomerAuditAction.CREATED.value,
            new_data=self._customer_to_dict(customer),
        )
        
        return CustomerResponse.model_validate(customer)

    # ============================================================
    # GET
    # ============================================================
    async def get_customer(self, customer_id: UUID, tenant_id: UUID) -> CustomerResponse | None:
        customer = await self.repository.get_by_id_with_relations(customer_id, tenant_id)
        if not customer:
            return None
        return CustomerResponse.model_validate(customer)

    async def get_customer_with_summary(
        self, 
        customer_id: UUID, 
        tenant_id: UUID
    ) -> dict | None:
        customer = await self.repository.get_by_id_with_relations(customer_id, tenant_id)
        if not customer:
            return None
        
        # Get notes and audit logs
        notes, _ = await self.repository.get_notes(customer.id, customer.tenant_id)
        audit_logs, _ = await self.repository.get_audit_logs(customer.id, customer.tenant_id)
        
        # Financial summary (placeholder)
        financial = await self.repository.get_financial_summary(customer.id, customer.tenant_id)
        
        return {
            "customer": CustomerResponse.model_validate(customer),
            "notes": [CustomerNoteResponse.model_validate(n) for n in notes],
            "audit_logs": [CustomerAuditLogResponse.model_validate(a) for a in audit_logs],
            "financial": financial,
        }

    # ============================================================
    # LIST
    # ============================================================
    async def get_customers(
        self,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: object | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> CustomerListResponse:
        # Convert filters if provided
        filter_obj = None
        if filters:
            filter_obj = CustomerSearchFilters(
                query=getattr(filters, 'query', None),
                customer_type=getattr(filters, 'customer_type', None),
                status=getattr(filters, 'status', None),
                city=getattr(filters, 'city', None),
                department=getattr(filters, 'department', None),
                country=getattr(filters, 'country', None),
                has_active_jobs=getattr(filters, 'has_active_jobs', None),
                has_pending_payments=getattr(filters, 'has_pending_payments', None),
                has_pending_quotes=getattr(filters, 'has_pending_quotes', None),
                registered_from=getattr(filters, 'registered_from', None),
                registered_to=getattr(filters, 'registered_to', None),
            )
        
        customers, total = await self.repository.get_all(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            filters=filter_obj,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return CustomerListResponse(
            customers=[CustomerResponse.model_validate(c) for c in customers],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ============================================================
    # UPDATE
    # ============================================================
    async def update_customer(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        customer_in: CustomerUpdate,
        updated_by_id: UUID,
    ) -> CustomerResponse | None:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return None
        
        # Capture old data for audit
        old_data = self._customer_to_dict(customer)
        
        # Update
        updated_customer = await self.repository.update(
            customer,
            status=customer_in.status.value if customer_in.status else None,
            phone=customer_in.phone,
            phone_secondary=customer_in.phone_secondary,
            whatsapp=customer_in.whatsapp,
            email=customer_in.email,
            address=customer_in.address,
            city=customer_in.city,
            department=customer_in.department,
            country=customer_in.country,
            postal_code=customer_in.postal_code,
            internal_notes=customer_in.internal_notes,
            first_name=customer_in.first_name,
            last_name=customer_in.last_name,
            identification_type=customer_in.identification_type.value if customer_in.identification_type else None,
            identification_number=customer_in.identification_number,
            business_name=customer_in.business_name,
            trade_name=customer_in.trade_name,
            tax_id_type=customer_in.tax_id_type.value if customer_in.tax_id_type else None,
            tax_id_number=customer_in.tax_id_number,
            verification_digit=customer_in.verification_digit,
            legal_rep_name=customer_in.legal_rep_name,
            legal_rep_id=customer_in.legal_rep_id,
            main_contact_name=customer_in.main_contact_name,
            fiscal_address=customer_in.fiscal_address,
            commercial_address=customer_in.commercial_address,
            website=customer_in.website,
            economic_activity=customer_in.economic_activity,
        )
        
        # Capture new data and changed fields
        new_data = self._customer_to_dict(updated_customer)
        changed_fields = self._get_changed_fields(old_data, new_data)
        
        # Determine action type
        action = CustomerAuditAction.UPDATED
        if "status" in changed_fields:
            action = CustomerAuditAction.STATUS_CHANGED
        if "identification_number" in changed_fields or "tax_id_number" in changed_fields:
            action = CustomerAuditAction.IDENTIFICATION_CHANGED
        
        # Create audit log
        await self.repository.create_audit_log(
            customer_id=updated_customer.id,
            user_id=updated_by_id,
            action=action.value,
            old_data=old_data,
            new_data=new_data,
            changed_fields=changed_fields,
        )
        
        return CustomerResponse.model_validate(updated_customer)

    # ============================================================
    # UPDATE STATUS
    # ============================================================
    async def update_customer_status(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        status_in: CustomerStatusUpdate,
        updated_by_id: UUID,
    ) -> CustomerResponse | None:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return None
        
        old_status = customer.status.value
        new_status = status_in.status.value
        
        old_data = self._customer_to_dict(customer)
        
        updated_customer = await self.repository.update_status(
            customer, CustomerStatus(status_in.status.value)
        )
        
        new_data = self._customer_to_dict(updated_customer)
        
        # Create audit log
        action = CustomerAuditAction.STATUS_CHANGED
        if new_status == CustomerStatus.INACTIVE.value:
            action = CustomerAuditAction.DEACTIVATED
        elif new_status == CustomerStatus.ACTIVE.value and old_status == CustomerStatus.INACTIVE.value:
            action = CustomerAuditAction.REACTIVATED
        elif new_status == CustomerStatus.ARCHIVED.value:
            action = CustomerAuditAction.ARCHIVED
        
        await self.repository.create_audit_log(
            customer_id=updated_customer.id,
            user_id=updated_by_id,
            action=action.value,
            old_data=old_data,
            new_data=new_data,
            changed_fields=["status"],
        )
        
        return CustomerResponse.model_validate(updated_customer)

    # ============================================================
    # DELETE (Archive)
    # ============================================================
    async def delete_customer(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        deleted_by_id: UUID,
    ) -> bool:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return False
        
        old_data = self._customer_to_dict(customer)
        
        # Soft delete - archive
        await self.repository.update_status(customer, CustomerStatus.ARCHIVED)
        
        # Audit log
        await self.repository.create_audit_log(
            customer_id=customer.id,
            user_id=deleted_by_id,
            action=CustomerAuditAction.ARCHIVED.value,
            old_data=old_data,
            new_data={**old_data, "status": CustomerStatus.ARCHIVED.value},
            changed_fields=["status"],
        )
        
        return True

    # ============================================================
    # REACTIVATE
    # ============================================================
    async def reactivate_customer(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        updated_by_id: UUID,
    ) -> CustomerResponse | None:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer or customer.status != CustomerStatus.ARCHIVED:
            return None
        
        old_data = self._customer_to_dict(customer)
        
        updated_customer = await self.repository.update_status(customer, CustomerStatus.ACTIVE)
        
        new_data = self._customer_to_dict(updated_customer)
        
        await self.repository.create_audit_log(
            customer_id=updated_customer.id,
            user_id=updated_by_id,
            action=CustomerAuditAction.REACTIVATED.value,
            old_data=old_data,
            new_data=new_data,
            changed_fields=["status"],
        )
        
        return CustomerResponse.model_validate(updated_customer)

    # ============================================================
    # NOTES
    # ============================================================
    async def create_note(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        note_in: CustomerNoteCreate,
        author_id: UUID,
    ) -> CustomerNoteResponse | None:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return None
        
        note = await self.repository.create_note(
            customer_id=customer_id,
            author_id=author_id,
            content=note_in.content,
        )
        
        # Audit log
        await self.repository.create_audit_log(
            customer_id=customer_id,
            user_id=author_id,
            action=CustomerAuditAction.UPDATED.value,
            new_data={"note_created": note_in.content},
            changed_fields=["notes"],
        )
        
        return CustomerNoteResponse.model_validate(note)

    async def get_notes(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[CustomerNoteResponse], int]:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return [], 0
        
        notes, total = await self.repository.get_notes(
            customer_id=customer_id,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
        )
        
        return [CustomerNoteResponse.model_validate(n) for n in notes], total

    async def update_note(
        self,
        note_id: UUID,
        customer_id: UUID,
        tenant_id: UUID,
        note_in: CustomerNoteUpdate,
        updated_by_id: UUID,
    ) -> CustomerNoteResponse | None:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return None
        
        note = await self.repository.get_note_by_id(note_id, customer_id, tenant_id)
        if not note:
            return None
        
        updated_note = await self.repository.update_note(note, note_in.content)
        
        # Audit log
        await self.repository.create_audit_log(
            customer_id=customer_id,
            user_id=updated_by_id,
            action=CustomerAuditAction.UPDATED.value,
            new_data={"note_updated": note_in.content},
            changed_fields=["notes"],
        )
        
        return CustomerNoteResponse.model_validate(updated_note)

    async def delete_note(
        self,
        note_id: UUID,
        customer_id: UUID,
        tenant_id: UUID,
        deleted_by_id: UUID,
    ) -> bool:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return False
        
        note = await self.repository.get_note_by_id(note_id, customer_id, tenant_id)
        if not note:
            return False
        
        await self.repository.delete_note(note)
        
        await self.repository.create_audit_log(
            customer_id=customer_id,
            user_id=deleted_by_id,
            action=CustomerAuditAction.UPDATED.value,
            new_data={"note_deleted": True},
            changed_fields=["notes"],
        )
        
        return True

    # ============================================================
    # AUDIT LOGS
    # ============================================================
    async def get_audit_logs(
        self,
        customer_id: UUID,
        tenant_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[CustomerAuditLogResponse], int]:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return [], 0
        
        logs, total = await self.repository.get_audit_logs(
            customer_id=customer_id,
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
        )
        
        return [CustomerAuditLogResponse.model_validate(l) for l in logs], total

    # ============================================================
    # FINANCIAL SUMMARY
    # ============================================================
    async def get_financial_summary(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> CustomerFinancialSummary | None:
        customer = await self.repository.get_by_id(customer_id, tenant_id)
        if not customer:
            return None
        
        data = await self.repository.get_financial_summary(customer_id, tenant_id)
        return CustomerFinancialSummary(**data)

    # ============================================================
    # DUPLICATE CHECK
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
        return await self.repository.check_duplicates(
            tenant_id,
            identification_number=identification_number,
            tax_id_number=tax_id_number,
            email=email,
            phone=phone,
            exclude_id=exclude_id,
        )

    # ============================================================
    # HELPERS
    # ============================================================
    def _customer_to_dict(self, customer: Customer) -> dict:
        return {
            "id": str(customer.id),
            "customer_type": customer.customer_type.value,
            "status": customer.status.value,
            "phone": customer.phone,
            "phone_secondary": customer.phone_secondary,
            "whatsapp": customer.whatsapp,
            "email": customer.email,
            "address": customer.address,
            "city": customer.city,
            "department": customer.department,
            "country": customer.country,
            "postal_code": customer.postal_code,
            "internal_notes": customer.internal_notes,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "identification_type": customer.identification_type.value if customer.identification_type else None,
            "identification_number": customer.identification_number,
            "business_name": customer.business_name,
            "trade_name": customer.trade_name,
            "tax_id_type": customer.tax_id_type.value if customer.tax_id_type else None,
            "tax_id_number": customer.tax_id_number,
            "verification_digit": customer.verification_digit,
            "legal_rep_name": customer.legal_rep_name,
            "legal_rep_id": customer.legal_rep_id,
            "main_contact_name": customer.main_contact_name,
            "fiscal_address": customer.fiscal_address,
            "commercial_address": customer.commercial_address,
            "website": customer.website,
            "economic_activity": customer.economic_activity,
            "tenant_id": str(customer.tenant_id),
            "created_by_id": str(customer.created_by_id),
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
        }

    def _get_changed_fields(self, old: dict, new: dict) -> list[str]:
        changed = []
        for key in set(old.keys()) | set(new.keys()):
            if old.get(key) != new.get(key):
                changed.append(key)
        return changed