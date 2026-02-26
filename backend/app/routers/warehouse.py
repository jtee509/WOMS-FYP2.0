"""
WOMS Warehouse Router

CRUD endpoints for Warehouse, Inventory Locations, and Inventory Levels.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.users import User
from app.models.warehouse import (
    InventoryAlert,
    InventoryLevel,
    InventoryLocation,
    Warehouse,
)
from app.schemas.common import PaginatedResponse
from app.schemas.warehouse import (
    InventoryAlertRead,
    InventoryLevelRead,
    InventoryLocationRead,
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Warehouse CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[WarehouseRead])
async def list_warehouses(
    is_active: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List all warehouses. Optionally filter by active status."""
    query = select(Warehouse).order_by(Warehouse.id)
    if is_active is not None:
        query = query.where(Warehouse.is_active == is_active)
    result = await session.execute(query)
    return [
        WarehouseRead(
            id=w.id,
            warehouse_name=w.warehouse_name,
            address=w.address,
            is_active=w.is_active,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in result.scalars().all()
    ]


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single warehouse by ID."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseRead(
        id=warehouse.id,
        warehouse_name=warehouse.warehouse_name,
        address=warehouse.address,
        is_active=warehouse.is_active,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
    )


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new warehouse."""
    warehouse = Warehouse(**body.model_dump())
    session.add(warehouse)
    await session.flush()
    await session.refresh(warehouse)
    return WarehouseRead(
        id=warehouse.id,
        warehouse_name=warehouse.warehouse_name,
        address=warehouse.address,
        is_active=warehouse.is_active,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
    )


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(
    warehouse_id: int,
    body: WarehouseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a warehouse. Only provided fields are changed."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(warehouse, key, value)

    await session.flush()
    await session.refresh(warehouse)
    return WarehouseRead(
        id=warehouse.id,
        warehouse_name=warehouse.warehouse_name,
        address=warehouse.address,
        is_active=warehouse.is_active,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
    )


# ---------------------------------------------------------------------------
# Inventory Locations
# ---------------------------------------------------------------------------

@router.get("/{warehouse_id}/locations", response_model=list[InventoryLocationRead])
async def list_locations(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
):
    """List all inventory locations in a warehouse."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    query = (
        select(InventoryLocation)
        .where(InventoryLocation.warehouse_id == warehouse_id)
        .order_by(InventoryLocation.id)
    )
    result = await session.execute(query)
    return [
        InventoryLocationRead(
            id=loc.id,
            warehouse_id=loc.warehouse_id,
            section=loc.section,
            zone=loc.zone,
            aisle=loc.aisle,
            rack=loc.rack,
            bin=loc.bin,
            inventory_type_id=loc.inventory_type_id,
            created_at=loc.created_at,
        )
        for loc in result.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Inventory Levels (stock queries)
# ---------------------------------------------------------------------------

@router.get("/{warehouse_id}/inventory", response_model=PaginatedResponse[InventoryLevelRead])
async def list_inventory_levels(
    warehouse_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List inventory levels for a warehouse with pagination."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    query = (
        select(InventoryLevel)
        .join(InventoryLocation, InventoryLevel.location_id == InventoryLocation.id)
        .where(InventoryLocation.warehouse_id == warehouse_id)
    )

    if item_id is not None:
        query = query.where(InventoryLevel.item_id == item_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(InventoryLevel.id).offset(offset).limit(page_size)
    result = await session.execute(query)
    levels = result.scalars().all()

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[
            InventoryLevelRead(
                id=lv.id,
                location_id=lv.location_id,
                item_id=lv.item_id,
                lot_id=lv.lot_id,
                quantity_available=lv.quantity_available,
                reorder_point=lv.reorder_point,
                safety_stock=lv.safety_stock,
                max_stock=lv.max_stock,
                alert_triggered_at=lv.alert_triggered_at,
                alert_acknowledged=lv.alert_acknowledged,
                created_at=lv.created_at,
                updated_at=lv.updated_at,
            )
            for lv in levels
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# Inventory Alerts
# ---------------------------------------------------------------------------

@router.get("/{warehouse_id}/alerts", response_model=list[InventoryAlertRead])
async def list_alerts(
    warehouse_id: int,
    is_resolved: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List inventory alerts for a warehouse."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    query = (
        select(InventoryAlert)
        .where(InventoryAlert.warehouse_id == warehouse_id)
        .order_by(InventoryAlert.created_at.desc())
    )
    if is_resolved is not None:
        query = query.where(InventoryAlert.is_resolved == is_resolved)

    result = await session.execute(query)
    return [
        InventoryAlertRead(
            id=a.id,
            inventory_level_id=a.inventory_level_id,
            item_id=a.item_id,
            warehouse_id=a.warehouse_id,
            alert_type=a.alert_type,
            current_quantity=a.current_quantity,
            threshold_quantity=a.threshold_quantity,
            alert_message=a.alert_message,
            is_resolved=a.is_resolved,
            resolved_at=a.resolved_at,
            created_at=a.created_at,
        )
        for a in result.scalars().all()
    ]
