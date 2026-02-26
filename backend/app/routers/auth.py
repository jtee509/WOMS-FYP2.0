"""
Auth Router

Provides authentication endpoints:
  POST /api/v1/auth/login — authenticate with email + password, receive JWT
  GET  /api/v1/auth/me    — get current user info from JWT
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import authenticate_user, create_access_token

router = APIRouter()


@router.post(
    "/login",
    summary="Authenticate and receive JWT access token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Authenticate a user with email and password.

    Returns a JWT access token on success (valid for 30 minutes).
    The token must be sent as `Authorization: Bearer <token>` on subsequent requests.
    """
    user = await authenticate_user(session, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_login timestamp (auto-committed by get_session)
    # Strip tzinfo because last_login column is TIMESTAMP WITHOUT TIME ZONE
    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(user)

    # Build JWT payload
    token_data = {
        "sub": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "role": user.role.role_name if user.role else None,
    }
    access_token = create_access_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role.role_name if user.role else None,
    )


@router.get(
    "/me",
    summary="Get current authenticated user",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
)
async def get_me(
    current_user: User = Depends(require_current_user),
) -> dict:
    """
    Return the currently authenticated user's profile.

    Requires a valid JWT in the Authorization header.
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role.role_name if current_user.role else None,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "last_login": (
            current_user.last_login.isoformat()
            if current_user.last_login
            else None
        ),
    }
