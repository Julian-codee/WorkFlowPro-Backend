from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        email: str,
        username: str,
        hashed_password: str,
        tenant_id: UUID,
        full_name: str | None = None,
        is_superuser: bool = False,
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            full_name=full_name,
            is_superuser=is_superuser,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID, tenant_id: UUID | None = None) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, tenant_id: UUID | None = None) -> User | None:
        stmt = select(User).where(User.email == email)
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str, tenant_id: UUID | None = None) -> User | None:
        stmt = select(User).where(User.username == username)
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self,
        user: User,
        *,
        email: str | None = None,
        username: str | None = None,
        full_name: str | None = None,
        is_active: bool | None = None,
        avatar_url: str | None = None,
        hashed_password: str | None = None,
    ) -> User:
        if email is not None:
            user.email = email
        if username is not None:
            user.username = username
        if full_name is not None:
            user.full_name = full_name
        if is_active is not None:
            user.is_active = is_active
        if avatar_url is not None:
            user.avatar_url = avatar_url
        if hashed_password is not None:
            user.hashed_password = hashed_password

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_last_login(self, user: User) -> User:
        user.last_login_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()


class TenantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, name: str, slug: str, description: str | None = None) -> Tenant:
        tenant = Tenant(name=name, slug=slug, description=description)
        self.db.add(tenant)
        await self.db.flush()
        await self.db.refresh(tenant)
        return tenant

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_default(self) -> Tenant:
        """Get or create a default tenant for development."""
        default_slug = "default"
        tenant = await self.get_by_slug(default_slug)
        if not tenant:
            tenant = await self.create(name="Default Tenant", slug=default_slug)
        return tenant