"""
WOMS Users Router

CRUD endpoints for User management and Roles.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.users import Role, User
from app.schemas.common import PaginatedResponse
from app.schemas.users import RoleRead, UserCreate, UserRead, UserUpdate
from app.services.auth import hash_password

router = APIRouter()


# ---------------------------------------------------------------------------
# Roles (read-only)
# ---------------------------------------------------------------------------

@router.get("/roles", response_model=list[RoleRead])
async def list_roles(session: AsyncSession = Depends(get_session)):
    """List all roles."""
    result = await session.execute(select(Role).order_by(Role.role_id))
    return [
        RoleRead(
            role_id=r.role_id,
            role_name=r.role_name,
            description=r.description,
            permissions=r.permissions,
            created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Users CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    role_id: int | None = Query(None),
    search: str | None = Query(None, description="Search by username or email"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """List users with pagination. Requires authentication."""
    query = select(User)

    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role_id is not None:
        query = query.where(User.role_id == role_id)
    if search:
        query = query.where(
            (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    query = (
        query
        .options(selectinload(User.role))
        .order_by(User.user_id)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(query)
    users = result.scalars().all()

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[_user_to_read(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Get a single user by ID. Requires authentication."""
    query = (
        select(User)
        .where(User.user_id == user_id)
        .options(selectinload(User.role))
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_read(user)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new user. Requires authentication (admin)."""
    # Check unique constraints
    existing = await session.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    user_data = body.model_dump(exclude={"password"})
    user_data["password_hash"] = hash_password(body.password)

    user = User(**user_data)
    session.add(user)
    await session.flush()
    await session.refresh(user, attribute_names=["role"])
    return _user_to_read(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    body: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a user. Only provided fields are changed. Requires authentication."""
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)

    # Handle password separately — hash it
    if "password" in update_data:
        user.password_hash = hash_password(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(user, key, value)

    await session.flush()
    await session.refresh(user, attribute_names=["role"])
    return _user_to_read(user)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_to_read(u: User) -> UserRead:
    return UserRead(
        user_id=u.user_id,
        username=u.username,
        email=u.email,
        first_name=u.first_name,
        last_name=u.last_name,
        role_id=u.role_id,
        is_active=u.is_active,
        is_superuser=u.is_superuser,
        created_at=u.created_at,
        updated_at=u.updated_at,
        last_login=u.last_login,
        role=RoleRead(
            role_id=u.role.role_id,
            role_name=u.role.role_name,
            description=u.role.description,
            permissions=u.role.permissions,
            created_at=u.role.created_at,
        ) if u.role else None,
    )
