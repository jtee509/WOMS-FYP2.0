"""
WOMS Auth Service

Handles password hashing, JWT creation/verification, and user authentication.
Uses passlib[bcrypt] for hashing and python-jose for JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.users import User

# Password hashing context — bcrypt with auto-deprecation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Uses settings.secret_key and settings.algorithm from config.py.
    Default expiry: settings.access_token_expire_minutes (30 min).
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.

    Returns the payload dict on success, None on failure.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> Optional[User]:
    """
    Look up a user by email and verify their password.

    Returns the User object if credentials are valid, None otherwise.
    Eager-loads the Role relationship for JWT payload.
    """
    stmt = (
        select(User)
        .options(selectinload(User.role))
        .where(User.email == email, User.is_active == True)  # noqa: E712
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None

    return user


async def get_current_user(session: AsyncSession, token: str) -> Optional[User]:
    """
    Decode token and fetch the corresponding User from DB.

    Used by the FastAPI dependency for protected endpoints.
    """
    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    stmt = (
        select(User)
        .options(selectinload(User.role))
        .where(User.user_id == int(user_id), User.is_active == True)  # noqa: E712
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
