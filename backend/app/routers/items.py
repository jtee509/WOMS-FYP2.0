"""
WOMS Items Router

CRUD endpoints for the Items domain (items + lookup tables).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.items import BaseUOM, Brand, Category, Item, ItemType, Status
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.items import (
    BaseUOMRead,
    BrandRead,
    CategoryRead,
    ItemCreate,
    ItemRead,
    ItemTypeRead,
    ItemUpdate,
    StatusRead,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Lookup tables (read-only)
# ---------------------------------------------------------------------------

@router.get("/statuses", response_model=list[StatusRead])
async def list_statuses(session: AsyncSession = Depends(get_session)):
    """List all item statuses."""
    result = await session.execute(select(Status).order_by(Status.status_id))
    return [StatusRead(status_id=r.status_id, status_name=r.status_name) for r in result.scalars().all()]


@router.get("/types", response_model=list[ItemTypeRead])
async def list_item_types(session: AsyncSession = Depends(get_session)):
    """List all item types."""
    result = await session.execute(select(ItemType).order_by(ItemType.item_type_id))
    return [ItemTypeRead(item_type_id=r.item_type_id, item_type_name=r.item_type_name) for r in result.scalars().all()]


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(session: AsyncSession = Depends(get_session)):
    """List all categories."""
    result = await session.execute(select(Category).order_by(Category.category_id))
    return [CategoryRead(category_id=r.category_id, category_name=r.category_name) for r in result.scalars().all()]


@router.get("/brands", response_model=list[BrandRead])
async def list_brands(session: AsyncSession = Depends(get_session)):
    """List all brands."""
    result = await session.execute(select(Brand).order_by(Brand.brand_id))
    return [BrandRead(brand_id=r.brand_id, brand_name=r.brand_name) for r in result.scalars().all()]


@router.get("/uoms", response_model=list[BaseUOMRead])
async def list_uoms(session: AsyncSession = Depends(get_session)):
    """List all base units of measure."""
    result = await session.execute(select(BaseUOM).order_by(BaseUOM.uom_id))
    return [BaseUOMRead(uom_id=r.uom_id, uom_name=r.uom_name) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# Items CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[ItemRead])
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by item_name or master_sku"),
    status_id: int | None = Query(None),
    category_id: int | None = Query(None),
    brand_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List items with pagination and optional filters. Excludes soft-deleted."""
    query = select(Item).where(Item.deleted_at.is_(None))

    if search:
        query = query.where(
            (Item.item_name.ilike(f"%{search}%")) | (Item.master_sku.ilike(f"%{search}%"))
        )
    if status_id is not None:
        query = query.where(Item.status_id == status_id)
    if category_id is not None:
        query = query.where(Item.category_id == category_id)
    if brand_id is not None:
        query = query.where(Item.brand_id == brand_id)

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = (
        query
        .options(
            selectinload(Item.uom),
            selectinload(Item.brand),
            selectinload(Item.status),
            selectinload(Item.item_type),
            selectinload(Item.category),
        )
        .order_by(Item.item_id)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(query)
    items = result.scalars().all()

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[_item_to_read(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single item by ID."""
    query = (
        select(Item)
        .where(Item.item_id == item_id, Item.deleted_at.is_(None))
        .options(
            selectinload(Item.uom),
            selectinload(Item.brand),
            selectinload(Item.status),
            selectinload(Item.item_type),
            selectinload(Item.category),
        )
    )
    result = await session.execute(query)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return _item_to_read(item)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ItemCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new item."""
    item = Item(**body.model_dump())
    session.add(item)
    await session.flush()
    await session.refresh(item, attribute_names=["uom", "brand", "status", "item_type", "category"])
    return _item_to_read(item)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    body: ItemUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update an item. Only provided fields are changed."""
    item = await session.get(Item, item_id)
    if item is None or item.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    await session.flush()
    await session.refresh(item, attribute_names=["uom", "brand", "status", "item_type", "category"])
    return _item_to_read(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Soft-delete an item (sets deleted_at + deleted_by)."""
    item = await session.get(Item, item_id)
    if item is None or item.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Item not found")

    from datetime import datetime, timezone
    item.deleted_at = datetime.now(timezone.utc)
    item.deleted_by = current_user.user_id
    await session.flush()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item_to_read(item: Item) -> ItemRead:
    """Convert an Item ORM instance to ItemRead schema."""
    return ItemRead(
        item_id=item.item_id,
        parent_id=item.parent_id,
        item_name=item.item_name,
        master_sku=item.master_sku,
        sku_name=item.sku_name,
        product_number=item.product_number,
        description=item.description,
        uom_id=item.uom_id,
        brand_id=item.brand_id,
        status_id=item.status_id,
        item_type_id=item.item_type_id,
        category_id=item.category_id,
        has_variation=item.has_variation,
        variations_data=item.variations_data,
        created_at=item.created_at,
        updated_at=item.updated_at,
        uom=BaseUOMRead(uom_id=item.uom.uom_id, uom_name=item.uom.uom_name) if item.uom else None,
        brand=BrandRead(brand_id=item.brand.brand_id, brand_name=item.brand.brand_name) if item.brand else None,
        status=StatusRead(status_id=item.status.status_id, status_name=item.status.status_name) if item.status else None,
        item_type=ItemTypeRead(item_type_id=item.item_type.item_type_id, item_type_name=item.item_type.item_type_name) if item.item_type else None,
        category=CategoryRead(category_id=item.category.category_id, category_name=item.category.category_name) if item.category else None,
    )
