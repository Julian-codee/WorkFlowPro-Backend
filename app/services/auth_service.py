from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.auth import TenantRepository, UserRepository
from app.schemas.auth import (
    TenantResponse,
    Token,
    TokenPayload,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

settings = get_settings()

# Password hashing - using PBKDF2 SHA256 to avoid bcrypt passlib bug
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    *,
    user_id: UUID,
    tenant_id: UUID,
    username: str,
    is_superuser: bool,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "username": username,
        "is_superuser": is_superuser,
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    *,
    user_id: UUID,
    tenant_id: UUID,
    username: str,
    is_superuser: bool,
) -> str:
    expire = datetime.now(UTC) + timedelta(days=30)

    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "username": username,
        "is_superuser": is_superuser,
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return TokenPayload(**payload)
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.tenant_repo = TenantRepository(db)

    async def register(self, user_in: UserCreate) -> tuple[UserResponse, TenantResponse, Token]:
        # Get or create tenant
        if user_in.tenant_slug:
            tenant = await self.tenant_repo.get_by_slug(user_in.tenant_slug)
            if not tenant:
                tenant = await self.tenant_repo.create(
                    name=user_in.tenant_slug.replace("-", " ").title(),
                    slug=user_in.tenant_slug,
                )
        else:
            tenant = await self.tenant_repo.get_or_create_default()

        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(user_in.email, tenant.id)
        if existing_user:
            raise ValueError("Email already registered")

        existing_username = await self.user_repo.get_by_username(user_in.username, tenant.id)
        if existing_username:
            raise ValueError("Username already taken")

        # Create user
        hashed_password = get_password_hash(user_in.password)
        user = await self.user_repo.create(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            full_name=user_in.full_name,
        )

        # Create tokens
        access_token, refresh_token = self._create_token_pair(user, tenant)

        return (
            UserResponse.model_validate(user),
            TenantResponse.model_validate(tenant),
            Token(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ),
        )

    async def login(self, user_in: UserLogin) -> Token:
        # Find user by email
        user = await self.user_repo.get_by_email(user_in.email)
        if not user:
            raise ValueError("Invalid credentials")

        if not user.is_active:
            raise ValueError("User is inactive")

        if not verify_password(user_in.password, user.hashed_password):
            raise ValueError("Invalid credentials")

        # Update last login
        await self.user_repo.update_last_login(user)

        # Create tokens
        access_token, refresh_token = self._create_token_pair(user, user.tenant)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_token(self, refresh_token: str) -> Token:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise ValueError("Invalid refresh token")

        if payload.type != "refresh":
            raise ValueError("Invalid token type")

        user = await self.user_repo.get_by_id(payload.sub, payload.tenant_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        access_token, new_refresh_token = self._create_token_pair(user, user.tenant)

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_current_user(self, token: str) -> User:
        try:
            payload = decode_token(token)
        except ValueError as e:
            raise ValueError(f"Invalid token: {e}")

        if payload.type != "access":
            raise ValueError("Invalid token type")

        user = await self.user_repo.get_by_id(payload.sub, payload.tenant_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        return user

    async def get_me(self, user: User) -> UserResponse:
        return UserResponse.model_validate(user)

    async def update_me(self, user: User, user_in: UserUpdate) -> UserResponse:
        hashed_password = None
        if user_in.password:
            hashed_password = get_password_hash(user_in.password)

        updated_user = await self.user_repo.update(
            user,
            email=user_in.email,
            username=user_in.username,
            full_name=user_in.full_name,
            is_active=user_in.is_active,
            avatar_url=user_in.avatar_url,
            hashed_password=hashed_password,
        )
        return UserResponse.model_validate(updated_user)

    def _create_token_pair(self, user: User, tenant: Tenant) -> tuple[str, str]:
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            username=user.username,
            is_superuser=user.is_superuser,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=tenant.id,
            username=user.username,
            is_superuser=user.is_superuser,
        )
        return access_token, refresh_token