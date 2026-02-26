"""
WOMS User Schemas

Request/response models for User management and Role endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Role (read-only for most users)
# ---------------------------------------------------------------------------

class RoleRead(BaseModel):
    """Response body for a user role."""
    role_id: int
    role_name: str
    description: Optional[str] = None
    permissions: Optional[dict[str, Any]] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """POST /users request body."""
    username: str = Field(..., max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role_id: Optional[int] = None
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    """PATCH /users/{id} request body. All fields optional."""
    username: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserRead(BaseModel):
    """Response body for a user (no password_hash)."""
    user_id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[int] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    # Nested
    role: Optional[RoleRead] = None
