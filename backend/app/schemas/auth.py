"""
WOMS Auth Schemas

Request/response models for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """POST /auth/login request body."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Successful login response — returns JWT access token."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str
    role: str | None = None


class TokenPayload(BaseModel):
    """Decoded JWT payload structure (internal use)."""
    sub: int          # user_id
    username: str
    email: str
    role: str | None = None
    exp: int          # expiry timestamp
