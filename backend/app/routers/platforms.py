"""
WOMS Platforms Router

CRUD endpoints for the Marketplace domain (Platform + Seller).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.orders import Platform, Seller
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.platform import (
    PlatformCreate,
    PlatformRead,
    PlatformUpdate,
    SellerCreate,
    SellerRead,
    SellerUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

@router.get("/platforms", response_model=list[PlatformRead])
async def list_platforms(
    is_active: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List all platforms. Optionally filter by active status."""
    query = select(Platform).order_by(Platform.platform_id)
    if is_active is not None:
        query = query.where(Platform.is_active == is_active)
    result = await session.execute(query)
    return [
        PlatformRead(
            platform_id=p.platform_id,
            platform_name=p.platform_name,
            address=p.address,
            postcode=p.postcode,
            api_endpoint=p.api_endpoint,
            is_active=p.is_active,
            created_at=p.created_at,
        )
        for p in result.scalars().all()
    ]


@router.get("/platforms/{platform_id}", response_model=PlatformRead)
async def get_platform(
    platform_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single platform by ID."""
    platform = await session.get(Platform, platform_id)
    if platform is None:
        raise HTTPException(status_code=404, detail="Platform not found")
    return PlatformRead(
        platform_id=platform.platform_id,
        platform_name=platform.platform_name,
        address=platform.address,
        postcode=platform.postcode,
        api_endpoint=platform.api_endpoint,
        is_active=platform.is_active,
        created_at=platform.created_at,
    )


@router.post("/platforms", response_model=PlatformRead, status_code=status.HTTP_201_CREATED)
async def create_platform(
    body: PlatformCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new platform."""
    platform = Platform(**body.model_dump())
    session.add(platform)
    await session.flush()
    await session.refresh(platform)
    return PlatformRead(
        platform_id=platform.platform_id,
        platform_name=platform.platform_name,
        address=platform.address,
        postcode=platform.postcode,
        api_endpoint=platform.api_endpoint,
        is_active=platform.is_active,
        created_at=platform.created_at,
    )


@router.patch("/platforms/{platform_id}", response_model=PlatformRead)
async def update_platform(
    platform_id: int,
    body: PlatformUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a platform. Only provided fields are changed."""
    platform = await session.get(Platform, platform_id)
    if platform is None:
        raise HTTPException(status_code=404, detail="Platform not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(platform, key, value)

    await session.flush()
    await session.refresh(platform)
    return PlatformRead(
        platform_id=platform.platform_id,
        platform_name=platform.platform_name,
        address=platform.address,
        postcode=platform.postcode,
        api_endpoint=platform.api_endpoint,
        is_active=platform.is_active,
        created_at=platform.created_at,
    )


# ---------------------------------------------------------------------------
# Sellers
# ---------------------------------------------------------------------------

@router.get("/sellers", response_model=PaginatedResponse[SellerRead])
async def list_sellers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None, description="Search by store_name or company_name"),
    session: AsyncSession = Depends(get_session),
):
    """List sellers with pagination and optional filters."""
    query = select(Seller)

    if platform_id is not None:
        query = query.where(Seller.platform_id == platform_id)
    if is_active is not None:
        query = query.where(Seller.is_active == is_active)
    if search:
        query = query.where(
            (Seller.store_name.ilike(f"%{search}%"))
            | (Seller.company_name.ilike(f"%{search}%"))
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    query = (
        query
        .options(selectinload(Seller.platform))
        .order_by(Seller.seller_id)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(query)
    sellers = result.scalars().all()

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[_seller_to_read(s) for s in sellers],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/sellers/{seller_id}", response_model=SellerRead)
async def get_seller(
    seller_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single seller by ID."""
    query = (
        select(Seller)
        .where(Seller.seller_id == seller_id)
        .options(selectinload(Seller.platform))
    )
    result = await session.execute(query)
    seller = result.scalar_one_or_none()
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")
    return _seller_to_read(seller)


@router.post("/sellers", response_model=SellerRead, status_code=status.HTTP_201_CREATED)
async def create_seller(
    body: SellerCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new seller."""
    seller = Seller(**body.model_dump())
    session.add(seller)
    await session.flush()
    await session.refresh(seller, attribute_names=["platform"])
    return _seller_to_read(seller)


@router.patch("/sellers/{seller_id}", response_model=SellerRead)
async def update_seller(
    seller_id: int,
    body: SellerUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a seller. Only provided fields are changed."""
    seller = await session.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(seller, key, value)

    await session.flush()
    await session.refresh(seller, attribute_names=["platform"])
    return _seller_to_read(seller)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seller_to_read(s: Seller) -> SellerRead:
    return SellerRead(
        seller_id=s.seller_id,
        store_name=s.store_name,
        platform_id=s.platform_id,
        platform_store_id=s.platform_store_id,
        company_name=s.company_name,
        is_active=s.is_active,
        created_at=s.created_at,
        platform=PlatformRead(
            platform_id=s.platform.platform_id,
            platform_name=s.platform.platform_name,
            address=s.platform.address,
            postcode=s.platform.postcode,
            api_endpoint=s.platform.api_endpoint,
            is_active=s.platform.is_active,
            created_at=s.platform.created_at,
        ) if s.platform else None,
    )
