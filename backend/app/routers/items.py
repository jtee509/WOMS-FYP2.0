"""
WOMS Items Router

CRUD endpoints for the Items domain (items + lookup tables).
"""

import uuid as uuid_mod
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.items import BaseUOM, Brand, Category, Item, ItemType
from app.models.orders import ListingComponent, Platform, PlatformSKU, Seller
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.items import (
    AttributeItemRead,
    BaseUOMCreate,
    BaseUOMRead,
    BaseUOMUpdate,
    BrandCreate,
    BrandRead,
    BrandUpdate,
    BundleComponentRead,
    BundleCreateRequest,
    BundleListItem,
    BundleReadResponse,
    BundleUpdateRequest,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ImportResult,
    ItemCreate,
    ItemRead,
    ItemTypeCreate,
    ItemTypeRead,
    ItemTypeUpdate,
    ItemUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Lookup tables — full CRUD
# ---------------------------------------------------------------------------

# ---- Item Type ----

@router.get("/types", response_model=list[ItemTypeRead])
async def list_item_types(session: AsyncSession = Depends(get_session)):
    """List all live (non-deleted) item types."""
    result = await session.execute(
        select(ItemType).where(ItemType.deleted_at.is_(None)).order_by(ItemType.item_type_id)
    )
    return [ItemTypeRead(item_type_id=r.item_type_id, item_type_name=r.item_type_name) for r in result.scalars().all()]


@router.post("/types", response_model=ItemTypeRead, status_code=status.HTTP_201_CREATED)
async def create_item_type(
    body: ItemTypeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new item type."""
    obj = ItemType(item_type_name=body.item_type_name)
    session.add(obj)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"An item type with name '{body.item_type_name}' already exists.")
    await session.refresh(obj)
    return ItemTypeRead(item_type_id=obj.item_type_id, item_type_name=obj.item_type_name)


@router.patch("/types/{item_type_id}", response_model=ItemTypeRead)
async def update_item_type(
    item_type_id: int,
    body: ItemTypeUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update an item type."""
    obj = await session.get(ItemType, item_type_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Item type not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An item type with that name already exists.")
    await session.refresh(obj)
    return ItemTypeRead(item_type_id=obj.item_type_id, item_type_name=obj.item_type_name)


@router.delete("/types/{item_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_type(
    item_type_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Soft-delete an item type (sets deleted_at)."""
    obj = await session.get(ItemType, item_type_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Item type not found")
    from datetime import timezone
    obj.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()


@router.post("/types/{item_type_id}/restore", response_model=ItemTypeRead)
async def restore_item_type(
    item_type_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Restore a soft-deleted item type (clears deleted_at)."""
    obj = await session.get(ItemType, item_type_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Item type not found")
    if obj.deleted_at is None:
        raise HTTPException(status_code=400, detail="Item type is not deleted")
    obj.deleted_at = None
    await session.flush()
    await session.refresh(obj)
    return ItemTypeRead(item_type_id=obj.item_type_id, item_type_name=obj.item_type_name)


# ---- Category ----

@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(session: AsyncSession = Depends(get_session)):
    """List all live (non-deleted) categories."""
    result = await session.execute(
        select(Category).where(Category.deleted_at.is_(None)).order_by(Category.category_id)
    )
    return [CategoryRead(category_id=r.category_id, category_name=r.category_name) for r in result.scalars().all()]


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new category."""
    obj = Category(category_name=body.category_name)
    session.add(obj)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A category with name '{body.category_name}' already exists.")
    await session.refresh(obj)
    return CategoryRead(category_id=obj.category_id, category_name=obj.category_name)


@router.patch("/categories/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a category."""
    obj = await session.get(Category, category_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A category with that name already exists.")
    await session.refresh(obj)
    return CategoryRead(category_id=obj.category_id, category_name=obj.category_name)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Soft-delete a category (sets deleted_at)."""
    obj = await session.get(Category, category_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Category not found")
    from datetime import timezone
    obj.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()


@router.post("/categories/{category_id}/restore", response_model=CategoryRead)
async def restore_category(
    category_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Restore a soft-deleted category (clears deleted_at)."""
    obj = await session.get(Category, category_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if obj.deleted_at is None:
        raise HTTPException(status_code=400, detail="Category is not deleted")
    obj.deleted_at = None
    await session.flush()
    await session.refresh(obj)
    return CategoryRead(category_id=obj.category_id, category_name=obj.category_name)


# ---- Brand ----

@router.get("/brands", response_model=list[BrandRead])
async def list_brands(session: AsyncSession = Depends(get_session)):
    """List all live (non-deleted) brands."""
    result = await session.execute(
        select(Brand).where(Brand.deleted_at.is_(None)).order_by(Brand.brand_id)
    )
    return [BrandRead(brand_id=r.brand_id, brand_name=r.brand_name) for r in result.scalars().all()]


@router.post("/brands", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(
    body: BrandCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new brand."""
    obj = Brand(brand_name=body.brand_name)
    session.add(obj)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A brand with name '{body.brand_name}' already exists.")
    await session.refresh(obj)
    return BrandRead(brand_id=obj.brand_id, brand_name=obj.brand_name)


@router.patch("/brands/{brand_id}", response_model=BrandRead)
async def update_brand(
    brand_id: int,
    body: BrandUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a brand."""
    obj = await session.get(Brand, brand_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A brand with that name already exists.")
    await session.refresh(obj)
    return BrandRead(brand_id=obj.brand_id, brand_name=obj.brand_name)


@router.delete("/brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Soft-delete a brand (sets deleted_at)."""
    obj = await session.get(Brand, brand_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Brand not found")
    from datetime import timezone
    obj.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()


@router.post("/brands/{brand_id}/restore", response_model=BrandRead)
async def restore_brand(
    brand_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Restore a soft-deleted brand (clears deleted_at)."""
    obj = await session.get(Brand, brand_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    if obj.deleted_at is None:
        raise HTTPException(status_code=400, detail="Brand is not deleted")
    obj.deleted_at = None
    await session.flush()
    await session.refresh(obj)
    return BrandRead(brand_id=obj.brand_id, brand_name=obj.brand_name)


# ---- Base UOM ----

@router.get("/uoms", response_model=list[BaseUOMRead])
async def list_uoms(session: AsyncSession = Depends(get_session)):
    """List all live (non-deleted) base units of measure."""
    result = await session.execute(
        select(BaseUOM).where(BaseUOM.deleted_at.is_(None)).order_by(BaseUOM.uom_id)
    )
    return [BaseUOMRead(uom_id=r.uom_id, uom_name=r.uom_name) for r in result.scalars().all()]


@router.post("/uoms", response_model=BaseUOMRead, status_code=status.HTTP_201_CREATED)
async def create_uom(
    body: BaseUOMCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new base unit of measure."""
    obj = BaseUOM(uom_name=body.uom_name)
    session.add(obj)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A UOM with name '{body.uom_name}' already exists.")
    await session.refresh(obj)
    return BaseUOMRead(uom_id=obj.uom_id, uom_name=obj.uom_name)


@router.patch("/uoms/{uom_id}", response_model=BaseUOMRead)
async def update_uom(
    uom_id: int,
    body: BaseUOMUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a base unit of measure."""
    obj = await session.get(BaseUOM, uom_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="UOM not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    try:
        await session.flush()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A UOM with that name already exists.")
    await session.refresh(obj)
    return BaseUOMRead(uom_id=obj.uom_id, uom_name=obj.uom_name)


@router.delete("/uoms/{uom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_uom(
    uom_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Soft-delete a UOM (sets deleted_at)."""
    obj = await session.get(BaseUOM, uom_id)
    if obj is None or obj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="UOM not found")
    from datetime import timezone
    obj.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()


@router.post("/uoms/{uom_id}/restore", response_model=BaseUOMRead)
async def restore_uom(
    uom_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Restore a soft-deleted UOM (clears deleted_at)."""
    obj = await session.get(BaseUOM, uom_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="UOM not found")
    if obj.deleted_at is None:
        raise HTTPException(status_code=400, detail="UOM is not deleted")
    obj.deleted_at = None
    await session.flush()
    await session.refresh(obj)
    return BaseUOMRead(uom_id=obj.uom_id, uom_name=obj.uom_name)


# ---------------------------------------------------------------------------
# Image Upload
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "items"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/upload-image")
async def upload_item_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_current_user),
):
    """Upload an item image. Returns the URL path to the saved file."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WebP, GIF.",
        )

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(contents)} bytes). Maximum is 5 MB.",
        )

    # Sanitise filename and prepend UUID for uniqueness
    original = Path(file.filename or "image").name  # strip any directory parts
    safe_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in original)
    unique_name = f"{uuid_mod.uuid4().hex}_{safe_name}"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / unique_name
    dest.write_bytes(contents)

    return {"url": f"/uploads/items/{unique_name}"}


# ---------------------------------------------------------------------------
# Items CRUD
# ---------------------------------------------------------------------------

_IMPORT_ALLOWED_EXT = {".csv", ".xlsx", ".xls"}
_IMPORT_MAX_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/import", response_model=ImportResult)
async def import_items_bulk(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Mass-import items from a CSV or Excel file.

    Required columns: item_name, master_sku
    Optional columns: sku_name, description, uom, brand, category, item_type, is_active

    Returns an ImportResult with per-row success/error details.
    """
    from app.services.items_import.importer import import_items

    # Validate file extension
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in _IMPORT_ALLOWED_EXT:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Upload a .csv, .xlsx, or .xls file.",
        )

    # Read and check file size
    file_bytes = await file.read()
    if len(file_bytes) > _IMPORT_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        result = await import_items(session, file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return result


@router.post("/bundles/import", response_model=ImportResult)
async def import_bundles_bulk(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Mass-import bundles from a CSV or Excel file.

    Each row represents a component of a bundle. Rows sharing the same
    bundle_sku are grouped into a single bundle. Metadata (name, description,
    category, etc.) is taken from the first row of each group.

    Required columns: bundle_name, bundle_sku, component_sku, component_qty
    Optional columns: sku_name, description, category, brand, uom, is_active
    """
    from app.services.items_import.bundle_importer import import_bundles

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in _IMPORT_ALLOWED_EXT:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Upload a .csv, .xlsx, or .xls file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _IMPORT_MAX_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        result = await import_bundles(session, file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return result


@router.get("/counts")
async def item_counts(
    exclude_item_type_id: int | None = Query(None, description="Exclude items of this type from counts"),
    session: AsyncSession = Depends(get_session),
):
    """Get item counts for tab filters (all, live, unpublished, deleted)."""
    def _excl(q):
        if exclude_item_type_id is not None:
            return q.where(
                (Item.item_type_id.is_(None)) | (Item.item_type_id != exclude_item_type_id)
            )
        return q

    all_count = (await session.execute(
        _excl(select(func.count()).where(Item.deleted_at.is_(None)))
    )).scalar_one()
    live_count = (await session.execute(
        _excl(select(func.count()).where(Item.deleted_at.is_(None), Item.is_active == True))  # noqa: E712
    )).scalar_one()
    unpublished_count = (await session.execute(
        _excl(select(func.count()).where(Item.deleted_at.is_(None), Item.is_active == False))  # noqa: E712
    )).scalar_one()
    deleted_count = (await session.execute(
        _excl(select(func.count()).where(Item.deleted_at.is_not(None)))
    )).scalar_one()
    return {
        "all": all_count,
        "live": live_count,
        "unpublished": unpublished_count,
        "deleted": deleted_count,
    }


@router.get("", response_model=PaginatedResponse[ItemRead])
async def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by item_name or master_sku"),
    is_active: bool | None = Query(None),
    category_id: int | None = Query(None),
    brand_id: int | None = Query(None),
    item_type_id: int | None = Query(None),
    exclude_item_type_id: int | None = Query(None, description="Exclude items of this type"),
    include_deleted: bool = Query(False, description="If true, show only soft-deleted items"),
    session: AsyncSession = Depends(get_session),
):
    """List items with pagination and optional filters."""
    if include_deleted:
        query = select(Item).where(Item.deleted_at.is_not(None))
    else:
        query = select(Item).where(Item.deleted_at.is_(None))

    if search:
        query = query.where(
            (Item.item_name.ilike(f"%{search}%")) | (Item.master_sku.ilike(f"%{search}%"))
        )
    if is_active is not None:
        query = query.where(Item.is_active == is_active)
    if category_id is not None:
        query = query.where(Item.category_id == category_id)
    if brand_id is not None:
        query = query.where(Item.brand_id == brand_id)
    if item_type_id is not None:
        query = query.where(Item.item_type_id == item_type_id)
    if exclude_item_type_id is not None:
        query = query.where(
            (Item.item_type_id.is_(None)) | (Item.item_type_id != exclude_item_type_id)
        )

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


@router.get("/bundles", response_model=PaginatedResponse[BundleListItem])
async def list_bundles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by bundle name or master_sku"),
    is_active: bool | None = Query(None),
    category_id: int | None = Query(None),
    brand_id: int | None = Query(None),
    include_deleted: bool = Query(False, description="If true, show only soft-deleted bundles"),
    session: AsyncSession = Depends(get_session),
):
    """
    List all bundle items with component counts.

    Bundles are items whose item_type = 'Bundle'. Each result includes
    component_count (distinct items) and total_quantity (sum of quantities)
    derived from the listing_component / platform_sku tables.
    """
    # Resolve Bundle type ID
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, pages=0)

    # Subquery: component counts per platform_sku
    comp_sq = (
        select(
            PlatformSKU.platform_sku.label("sku"),
            func.count(func.distinct(ListingComponent.item_id)).label("component_count"),
            func.coalesce(func.sum(ListingComponent.quantity), 0).label("total_quantity"),
        )
        .select_from(ListingComponent)
        .join(PlatformSKU, ListingComponent.listing_id == PlatformSKU.listing_id)
        .group_by(PlatformSKU.platform_sku)
        .subquery()
    )

    # Base query — filter to Bundle type
    if include_deleted:
        query = select(Item).where(Item.item_type_id == bundle_type_id, Item.deleted_at.is_not(None))
    else:
        query = select(Item).where(Item.item_type_id == bundle_type_id, Item.deleted_at.is_(None))

    if search:
        query = query.where(
            (Item.item_name.ilike(f"%{search}%")) | (Item.master_sku.ilike(f"%{search}%"))
        )
    if is_active is not None:
        query = query.where(Item.is_active == is_active)
    if category_id is not None:
        query = query.where(Item.category_id == category_id)
    if brand_id is not None:
        query = query.where(Item.brand_id == brand_id)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Paginate — join with component counts
    offset = (page - 1) * page_size
    main_q = (
        query
        .options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
        .order_by(Item.item_id)
        .offset(offset)
        .limit(page_size)
    )
    items_result = await session.execute(main_q)
    items_list = items_result.scalars().all()

    # Fetch component counts for the visible SKUs
    if items_list:
        skus = [i.master_sku for i in items_list]
        counts_result = await session.execute(
            select(comp_sq.c.sku, comp_sq.c.component_count, comp_sq.c.total_quantity)
            .where(comp_sq.c.sku.in_(skus))
        )
        counts_map = {r.sku: (r.component_count, r.total_quantity) for r in counts_result.all()}
    else:
        counts_map = {}

    pages = (total + page_size - 1) // page_size
    out_items = []
    for i in items_list:
        cc, tq = counts_map.get(i.master_sku, (0, 0))
        item_read = _item_to_read(i)
        out_items.append(BundleListItem(
            **item_read.model_dump(),
            component_count=cc,
            total_quantity=tq,
        ))

    return PaginatedResponse(
        items=out_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/bundles/counts")
async def bundle_counts(
    session: AsyncSession = Depends(get_session),
):
    """Get bundle counts for tab filters (all, live, unpublished, deleted)."""
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        return {"all": 0, "live": 0, "unpublished": 0, "deleted": 0}

    base = select(func.count()).where(Item.item_type_id == bundle_type_id)

    all_count = (await session.execute(
        base.where(Item.deleted_at.is_(None))
    )).scalar_one()
    live_count = (await session.execute(
        base.where(Item.deleted_at.is_(None), Item.is_active == True)  # noqa: E712
    )).scalar_one()
    unpublished_count = (await session.execute(
        base.where(Item.deleted_at.is_(None), Item.is_active == False)  # noqa: E712
    )).scalar_one()
    deleted_count = (await session.execute(
        base.where(Item.deleted_at.is_not(None))
    )).scalar_one()

    return {
        "all": all_count,
        "live": live_count,
        "unpublished": unpublished_count,
        "deleted": deleted_count,
    }


@router.get("/bundles/{item_id}", response_model=BundleReadResponse)
async def get_bundle(
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a single bundle by item_id, including its full components.
    """
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        raise HTTPException(status_code=500, detail="Item type 'Bundle' not found.")

    result = await session.execute(
        select(Item).where(Item.item_id == item_id).options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if item.item_type_id != bundle_type_id:
        raise HTTPException(status_code=422, detail=f"Item {item_id} is not a Bundle.")

    item_read = _item_to_read(item)

    # Find the PlatformSKU listing
    listing = (await session.execute(
        select(PlatformSKU).where(PlatformSKU.platform_sku == item.master_sku)
    )).scalar_one_or_none()

    if listing is None:
        return BundleReadResponse(
            item=item_read, listing_id=0, platform_sku=item.master_sku, components=[],
        )

    # Fetch components
    comp_rows = (await session.execute(
        select(
            ListingComponent.id, ListingComponent.item_id, ListingComponent.quantity,
            Item.item_name, Item.master_sku,
        )
        .join(Item, ListingComponent.item_id == Item.item_id)
        .where(ListingComponent.listing_id == listing.listing_id)
    )).all()

    return BundleReadResponse(
        item=item_read,
        listing_id=listing.listing_id,
        platform_sku=listing.platform_sku,
        components=[
            BundleComponentRead(
                id=r.id, item_id=r.item_id, item_name=r.item_name,
                master_sku=r.master_sku, quantity=r.quantity,
            )
            for r in comp_rows
        ],
    )


@router.post("/bundles", response_model=BundleReadResponse, status_code=status.HTTP_201_CREATED)
async def create_bundle(
    body: BundleCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Create a bundle item with its components in a single transaction.

    Flow:
    1. Validate master_sku uniqueness.
    2. Validate bundle composition (>1 distinct items OR single item with qty > 1).
    3. Insert the bundle record into items (item_type = "Bundle").
    4. Create a PlatformSKU listing for the bundle.
    5. Insert each component into listing_component.
    6. The trg_items_history_on_insert trigger auto-creates the audit trail.
    """
    # --- 1. Check SKU uniqueness upfront (friendlier than waiting for IntegrityError) ---
    existing = (await session.execute(
        select(Item.item_id).where(Item.master_sku == body.master_sku)
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An item with Master SKU '{body.master_sku}' already exists.",
        )

    # --- 2. Validate bundle composition ---
    distinct_item_ids = {c.item_id for c in body.components}
    max_qty = max(c.quantity for c in body.components)
    if len(distinct_item_ids) <= 1 and max_qty <= 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A bundle must have more than one distinct component item, "
                   "or a single component with quantity > 1.",
        )

    # --- 3. Validate all component item_ids exist and are not deleted ---
    found_items = (await session.execute(
        select(Item.item_id, Item.item_name, Item.master_sku)
        .where(Item.item_id.in_(distinct_item_ids), Item.deleted_at.is_(None))
    )).all()
    found_ids = {r.item_id for r in found_items}
    missing = distinct_item_ids - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Component item_id(s) not found or deleted: {sorted(missing)}",
        )

    # --- 4. Resolve "Bundle" item_type_id ---
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Item type 'Bundle' not found in database. Run seed data first.",
        )

    # --- 5. Insert bundle item ---
    bundle_item = Item(
        item_name=body.item_name,
        master_sku=body.master_sku,
        sku_name=body.sku_name,
        description=body.description,
        image_url=body.image_url,
        uom_id=body.uom_id,
        brand_id=body.brand_id,
        item_type_id=bundle_type_id,
        category_id=body.category_id,
        is_active=body.is_active,
    )
    session.add(bundle_item)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An item with Master SKU '{body.master_sku}' already exists.",
        )

    # --- 6. Resolve platform_id and seller_id (auto-pick first active if not provided) ---
    resolved_platform_id = body.platform_id
    resolved_seller_id = body.seller_id

    if resolved_platform_id is None:
        resolved_platform_id = (await session.execute(
            select(Platform.platform_id)
            .where(Platform.is_active.is_(True))
            .order_by(Platform.platform_id)
            .limit(1)
        )).scalar_one_or_none()

    if resolved_seller_id is None:
        resolved_seller_id = (await session.execute(
            select(Seller.seller_id)
            .where(Seller.is_active.is_(True))
            .order_by(Seller.seller_id)
            .limit(1)
        )).scalar_one_or_none()

    if resolved_platform_id is None or resolved_seller_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot create bundle: no active platform or seller exists. "
                   "Create at least one platform and one seller first.",
        )

    # --- 7. Create PlatformSKU listing ---
    listing = PlatformSKU(
        platform_id=resolved_platform_id,
        seller_id=resolved_seller_id,
        platform_sku=body.master_sku,
        platform_seller_sku_name=body.item_name,
        is_active=body.is_active,
    )
    session.add(listing)
    await session.flush()

    # --- 8. Insert components into listing_component ---
    component_records: list[ListingComponent] = []
    for comp in body.components:
        lc = ListingComponent(
            listing_id=listing.listing_id,
            item_id=comp.item_id,
            quantity=comp.quantity,
        )
        session.add(lc)
        component_records.append(lc)
    await session.flush()

    # --- 9. Build response ---
    # Re-fetch item with relationships
    result = await session.execute(
        select(Item).where(Item.item_id == bundle_item.item_id).options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
    )
    item_read = _item_to_read(result.scalar_one())

    # Map component item_ids to their details
    item_lookup = {r.item_id: r for r in found_items}
    components_out = []
    for lc in component_records:
        info = item_lookup[lc.item_id]
        components_out.append(BundleComponentRead(
            id=lc.id,
            item_id=lc.item_id,
            item_name=info.item_name,
            master_sku=info.master_sku,
            quantity=lc.quantity,
        ))

    return BundleReadResponse(
        item=item_read,
        listing_id=listing.listing_id,
        platform_sku=listing.platform_sku,
        components=components_out,
    )


@router.patch("/bundles/{item_id}", response_model=BundleReadResponse)
async def update_bundle(
    item_id: int,
    body: BundleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Update a bundle's metadata and/or its components.

    - Only provided fields are changed on the items row.
    - Changing master_sku updates the bundle's SKU only; component item
      SKUs are never modified.
    - When `components` is provided the existing listing_component rows
      are deleted and replaced (delete-and-reinsert).
    - The PlatformSKU.platform_sku is kept in sync when master_sku changes.
    """
    # --- 1. Load the bundle item and verify it exists + is a Bundle type ---
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Item type 'Bundle' not found in database. Run seed data first.",
        )

    item = await session.get(Item, item_id)
    if item is None or item.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if item.item_type_id != bundle_type_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Item {item_id} is not a Bundle (item_type_id={item.item_type_id}).",
        )

    # --- 2. Find the PlatformSKU listing linked to this bundle ---
    # The create_bundle endpoint sets platform_sku = master_sku, so we
    # look up by the current master_sku.
    listing = (await session.execute(
        select(PlatformSKU).where(PlatformSKU.platform_sku == item.master_sku)
    )).scalar_one_or_none()
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No PlatformSKU listing found for bundle SKU '{item.master_sku}'.",
        )

    # --- 3. Handle master_sku change (uniqueness + sync PlatformSKU) ---
    new_sku = body.master_sku
    if new_sku is not None and new_sku != item.master_sku:
        clash = (await session.execute(
            select(Item.item_id).where(
                Item.master_sku == new_sku,
                Item.item_id != item_id,
            )
        )).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An item with Master SKU '{new_sku}' already exists.",
            )
        # Update PlatformSKU.platform_sku to stay in sync
        listing.platform_sku = new_sku

    # --- 4. Apply item field updates (never touches component item SKUs) ---
    update_fields = body.model_dump(exclude_unset=True, exclude={"components"})
    for key, value in update_fields.items():
        setattr(item, key, value)

    # Sync listing display name if item_name changed
    if "item_name" in update_fields:
        listing.platform_seller_sku_name = update_fields["item_name"]
    if "is_active" in update_fields:
        listing.is_active = update_fields["is_active"]

    # Set session variable so the UPDATE trigger can record the user
    await session.execute(text(f"SET LOCAL app.current_user_id = '{current_user.user_id}'"))

    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An item with Master SKU '{body.master_sku}' already exists.",
        )

    # --- 5. Replace components if provided (delete-and-reinsert) ---
    if body.components is not None:
        # Validate bundle composition
        distinct_item_ids = {c.item_id for c in body.components}
        max_qty = max(c.quantity for c in body.components)
        if len(distinct_item_ids) <= 1 and max_qty <= 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A bundle must have more than one distinct component item, "
                       "or a single component with quantity > 1.",
            )

        # Validate all component item_ids exist and are not deleted
        found_items = (await session.execute(
            select(Item.item_id, Item.item_name, Item.master_sku)
            .where(Item.item_id.in_(distinct_item_ids), Item.deleted_at.is_(None))
        )).all()
        found_ids = {r.item_id for r in found_items}
        missing = distinct_item_ids - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Component item_id(s) not found or deleted: {sorted(missing)}",
            )

        # Delete existing components for this listing
        await session.execute(
            delete(ListingComponent).where(
                ListingComponent.listing_id == listing.listing_id
            )
        )

        # Insert new components
        for comp in body.components:
            session.add(ListingComponent(
                listing_id=listing.listing_id,
                item_id=comp.item_id,
                quantity=comp.quantity,
            ))
        await session.flush()

    # --- 6. Build response ---
    # Re-fetch item with relationships
    result = await session.execute(
        select(Item).where(Item.item_id == item_id).options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
    )
    item_read = _item_to_read(result.scalar_one())

    # Fetch current components
    comp_rows = (await session.execute(
        select(
            ListingComponent.id,
            ListingComponent.item_id,
            ListingComponent.quantity,
            Item.item_name,
            Item.master_sku,
        )
        .join(Item, ListingComponent.item_id == Item.item_id)
        .where(ListingComponent.listing_id == listing.listing_id)
    )).all()

    components_out = [
        BundleComponentRead(
            id=r.id,
            item_id=r.item_id,
            item_name=r.item_name,
            master_sku=r.master_sku,
            quantity=r.quantity,
        )
        for r in comp_rows
    ]

    return BundleReadResponse(
        item=item_read,
        listing_id=listing.listing_id,
        platform_sku=listing.platform_sku,
        components=components_out,
    )


@router.delete("/bundles/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bundle(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Soft-delete a bundle.

    Sets deleted_at / deleted_by on the items row and deactivates the
    associated PlatformSKU listing.  The listing_component rows are kept
    intact so the bundle can be fully restored later.
    """
    from datetime import datetime, timezone

    # --- Resolve Bundle type ---
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        raise HTTPException(status_code=500, detail="Item type 'Bundle' not found.")

    item = await session.get(Item, item_id)
    if item is None or item.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if item.item_type_id != bundle_type_id:
        raise HTTPException(status_code=422, detail=f"Item {item_id} is not a Bundle.")

    # Set session variable so the UPDATE trigger can record the user
    await session.execute(text(f"SET LOCAL app.current_user_id = '{current_user.user_id}'"))

    # Soft-delete the item (triggers trg_items_history_on_update → SOFT_DELETE)
    item.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    item.deleted_by = current_user.user_id

    # Deactivate the PlatformSKU listing
    listing = (await session.execute(
        select(PlatformSKU).where(PlatformSKU.platform_sku == item.master_sku)
    )).scalar_one_or_none()
    if listing is not None:
        listing.is_active = False

    await session.flush()


@router.post("/bundles/{item_id}/restore", response_model=BundleReadResponse)
async def restore_bundle(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Restore a soft-deleted bundle.

    Clears deleted_at / deleted_by on the items row and re-activates the
    PlatformSKU listing.  Components are still intact from the original
    soft-delete.
    """
    # --- Resolve Bundle type ---
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        raise HTTPException(status_code=500, detail="Item type 'Bundle' not found.")

    item = await session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if item.deleted_at is None:
        raise HTTPException(status_code=400, detail="Bundle is not deleted")
    if item.item_type_id != bundle_type_id:
        raise HTTPException(status_code=422, detail=f"Item {item_id} is not a Bundle.")

    # Set session variable so the UPDATE trigger can record the user
    await session.execute(text(f"SET LOCAL app.current_user_id = '{current_user.user_id}'"))

    # Restore (triggers trg_items_history_on_update → RESTORE)
    item.deleted_at = None
    item.deleted_by = None

    # Re-activate the PlatformSKU listing
    listing = (await session.execute(
        select(PlatformSKU).where(PlatformSKU.platform_sku == item.master_sku)
    )).scalar_one_or_none()
    if listing is not None:
        listing.is_active = True

    await session.flush()

    # Build response
    result = await session.execute(
        select(Item).where(Item.item_id == item_id).options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
    )
    item_read = _item_to_read(result.scalar_one())

    # Fetch components
    comp_rows = (await session.execute(
        select(
            ListingComponent.id,
            ListingComponent.item_id,
            ListingComponent.quantity,
            Item.item_name,
            Item.master_sku,
        )
        .join(Item, ListingComponent.item_id == Item.item_id)
        .where(ListingComponent.listing_id == listing.listing_id)
    )).all() if listing else []

    components_out = [
        BundleComponentRead(
            id=r.id, item_id=r.item_id, item_name=r.item_name,
            master_sku=r.master_sku, quantity=r.quantity,
        )
        for r in comp_rows
    ]

    return BundleReadResponse(
        item=item_read,
        listing_id=listing.listing_id if listing else 0,
        platform_sku=listing.platform_sku if listing else item.master_sku,
        components=components_out,
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
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"An item with Master SKU '{body.master_sku}' already exists.",
        )
    # Re-fetch with selectinload — session.refresh() with relationship names is unreliable
    # in async SQLAlchemy and can leave relationships in an expired lazy-load state.
    result = await session.execute(
        select(Item).where(Item.item_id == item.item_id).options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
    )
    return _item_to_read(result.scalar_one())


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

    # Set session variable so the UPDATE trigger can record the user
    await session.execute(text(f"SET LOCAL app.current_user_id = '{current_user.user_id}'"))

    await session.flush()
    # Re-fetch with selectinload — session.refresh() with relationship names is unreliable
    # in async SQLAlchemy and can leave relationships in an expired lazy-load state.
    result = await session.execute(
        select(Item).where(Item.item_id == item_id).options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
    )
    return _item_to_read(result.scalar_one())


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
    await session.execute(text(f"SET LOCAL app.current_user_id = '{current_user.user_id}'"))
    item.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    item.deleted_by = current_user.user_id
    await session.flush()


@router.post("/{item_id}/restore", response_model=ItemRead)
async def restore_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Restore a soft-deleted item (clears deleted_at + deleted_by)."""
    item = await session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.deleted_at is None:
        raise HTTPException(status_code=400, detail="Item is not deleted")

    await session.execute(text(f"SET LOCAL app.current_user_id = '{current_user.user_id}'"))
    item.deleted_at = None
    item.deleted_by = None
    await session.flush()
    # Re-fetch with selectinload — session.refresh() with relationship names is unreliable
    # in async SQLAlchemy and can leave relationships in an expired lazy-load state.
    result = await session.execute(
        select(Item).where(Item.item_id == item_id).options(
            selectinload(Item.uom), selectinload(Item.brand),
            selectinload(Item.item_type), selectinload(Item.category),
        )
    )
    return _item_to_read(result.scalar_one())


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
        description=item.description,
        image_url=item.image_url,
        uom_id=item.uom_id,
        brand_id=item.brand_id,
        item_type_id=item.item_type_id,
        category_id=item.category_id,
        is_active=item.is_active,
        has_variation=item.has_variation,
        variations_data=item.variations_data,
        created_at=item.created_at,
        updated_at=item.updated_at,
        deleted_at=item.deleted_at,
        uom=AttributeItemRead(id=item.uom.uom_id, name=item.uom.uom_name) if item.uom else None,
        brand=AttributeItemRead(id=item.brand.brand_id, name=item.brand.brand_name) if item.brand else None,
        item_type=AttributeItemRead(id=item.item_type.item_type_id, name=item.item_type.item_type_name) if item.item_type else None,
        category=AttributeItemRead(id=item.category.category_id, name=item.category.category_name) if item.category else None,
    )
