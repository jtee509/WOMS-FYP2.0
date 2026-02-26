"""
WOMS Auth Dependencies

FastAPI dependencies for JWT-protected endpoints.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.users import User
from app.services.auth import get_current_user

# OAuth2 scheme — tells FastAPI/Swagger where the token comes from
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def require_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency: Extract JWT from Authorization header, decode it,
    fetch the user from DB, raise 401 if invalid.
    """
    user = await get_current_user(session, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
