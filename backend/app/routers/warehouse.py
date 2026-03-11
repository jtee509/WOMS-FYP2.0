"""
WOMS Warehouse Router

CRUD endpoints for Warehouse, Inventory Locations, Inventory Levels,
Inventory Movements, and Inventory Alerts.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.items import Item
from app.models.users import User
from app.models.warehouse import (
    InventoryAlert,
    InventoryLevel,
    InventoryLocation,
    InventoryMovement,
    InventoryTransaction,
    MovementType,
    Warehouse,
)
from app.schemas.common import PaginatedResponse
from app.schemas.warehouse import (
    AlertResolveRequest,
    BulkGenerateRequest,
    BulkGenerateResponse,
    BulkLocationUpdateItem,
    BulkLocationUpdateRequest,
    BulkLocationUpdateResponse,
    BulkLocationUpdateResult,
    BundleFulfillRequest,
    RenameLevelRequest,
    RenameLevelResponse,
    InventoryAlertRead,
    InventoryLevelEnrichedRead,
    InventoryLevelRead,
    InventoryLocationCreate,
    InventoryLocationRead,
    InventoryLocationUpdate,
    InventoryMovementCreate,
    InventoryMovementRead,
    LocationSummary,
    MovementTypeRead,
    ReleaseRequest,
    ReserveRequest,
    ReserveResponse,
    WarehouseCreate,
    WarehouseDuplicateResponse,
    WarehouseRead,
    WarehouseUpdate,
)
from app.services.inventory_guard import (
    check_stock_at_locations,
    get_location_children_ids,
    get_subtree_location_ids,
    get_warehouse_location_ids,
    soft_delete_location as _soft_delete_location_service,
)
from app.services.location_generator import (
    bulk_generate_locations as _bulk_generate_locations,
)
from app.services.location_tree import build_location_tree as _build_location_tree

router = APIRouter()


# ---------------------------------------------------------------------------
# Movement Types (must be before /{warehouse_id} to avoid route conflict)
# ---------------------------------------------------------------------------

@router.get("/movement-types", response_model=list[MovementTypeRead])
async def list_movement_types(
    session: AsyncSession = Depends(get_session),
):
    """List all movement types (Receipt, Shipment, Transfer, etc.)."""
    result = await session.execute(select(MovementType).order_by(MovementType.id))
    return [
        MovementTypeRead(id=mt.id, name=mt.movement_name)
        for mt in result.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Warehouse CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[WarehouseRead])
async def list_warehouses(
    is_active: bool | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List all warehouses (excludes soft-deleted). Optionally filter by active status."""
    # Subquery: count live locations per warehouse
    loc_count_sq = (
        select(
            InventoryLocation.warehouse_id,
            func.count(InventoryLocation.id).label("loc_count"),
        )
        .where(InventoryLocation.deleted_at.is_(None))
        .group_by(InventoryLocation.warehouse_id)
        .subquery()
    )

    query = (
        select(Warehouse, func.coalesce(loc_count_sq.c.loc_count, 0).label("location_count"))
        .outerjoin(loc_count_sq, Warehouse.id == loc_count_sq.c.warehouse_id)
        .where(Warehouse.deleted_at.is_(None))
        .order_by(Warehouse.id)
    )
    if is_active is not None:
        query = query.where(Warehouse.is_active == is_active)
    result = await session.execute(query)
    return [
        WarehouseRead(
            id=w.id,
            warehouse_name=w.warehouse_name,
            address=w.address,
            is_active=w.is_active,
            location_count=loc_cnt,
            created_at=w.created_at,
            updated_at=w.updated_at,
            deleted_at=w.deleted_at,
        )
        for w, loc_cnt in result.all()
    ]


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single warehouse by ID (404 if soft-deleted)."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    loc_count_result = await session.execute(
        select(func.count(InventoryLocation.id)).where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at.is_(None),
        )
    )
    loc_count = loc_count_result.scalar() or 0

    return WarehouseRead(
        id=warehouse.id,
        warehouse_name=warehouse.warehouse_name,
        address=warehouse.address,
        is_active=warehouse.is_active,
        location_count=loc_count,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
        deleted_at=warehouse.deleted_at,
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
        deleted_at=warehouse.deleted_at,
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
    if warehouse is None or warehouse.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    update_data = body.model_dump(exclude_unset=True)

    # Inventory guard — block deactivation if locations still hold stock
    if update_data.get("is_active") is False and warehouse.is_active is True:
        loc_ids = await get_warehouse_location_ids(session, warehouse_id)
        has_stock, total_qty, loc_count = await check_stock_at_locations(session, loc_ids)
        if has_stock:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete: Location contains active stock.",
            )

    for key, value in update_data.items():
        setattr(warehouse, key, value)
    warehouse.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await session.flush()
    await session.refresh(warehouse)
    return WarehouseRead(
        id=warehouse.id,
        warehouse_name=warehouse.warehouse_name,
        address=warehouse.address,
        is_active=warehouse.is_active,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
        deleted_at=warehouse.deleted_at,
    )


# ---------------------------------------------------------------------------
# Warehouse — Toggle Status / Soft Delete / Duplicate
# ---------------------------------------------------------------------------

@router.patch("/{warehouse_id}/toggle-status", response_model=WarehouseRead)
async def toggle_warehouse_status(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Toggle warehouse is_active between True and False."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Inventory guard — block deactivation if locations still hold stock
    if warehouse.is_active is True:
        loc_ids = await get_warehouse_location_ids(session, warehouse_id)
        has_stock, total_qty, loc_count = await check_stock_at_locations(session, loc_ids)
        if has_stock:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete: Location contains active stock.",
            )

    warehouse.is_active = not warehouse.is_active
    warehouse.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)
    return WarehouseRead(
        id=warehouse.id,
        warehouse_name=warehouse.warehouse_name,
        address=warehouse.address,
        is_active=warehouse.is_active,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
        deleted_at=warehouse.deleted_at,
    )


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_warehouse(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Soft-delete a warehouse and cascade to all its locations.

    Sets deleted_at = now() on the warehouse row and on every InventoryLocation
    belonging to it. The warehouse disappears from all standard list/get queries
    but its relational history (levels, movements, alerts) is preserved.
    """
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Inventory guard — block if any location still holds stock
    loc_ids = await get_warehouse_location_ids(session, warehouse_id)
    has_stock, total_qty, loc_count = await check_stock_at_locations(session, loc_ids)
    if has_stock:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete: Location contains active stock.",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    warehouse.deleted_at = now
    warehouse.is_active = False
    warehouse.updated_at = now
    session.add(warehouse)

    # Cascade soft-delete all live locations in one bulk UPDATE
    await session.execute(
        update(InventoryLocation)
        .where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at.is_(None),
        )
        .values(deleted_at=now)
    )

    await session.flush()


@router.post("/{warehouse_id}/restore", response_model=WarehouseRead)
async def restore_warehouse(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Restore a soft-deleted warehouse and cascade-restore its locations.

    Clears deleted_at on the warehouse row and on every InventoryLocation
    that was soft-deleted at the same timestamp (i.e. the locations that
    were cascade-deleted when the warehouse was soft-deleted).
    """
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    if warehouse.deleted_at is None:
        raise HTTPException(status_code=400, detail="Warehouse is not deleted")

    cascade_ts = warehouse.deleted_at  # timestamp used during cascade soft-delete

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    warehouse.deleted_at = None
    warehouse.is_active = True
    warehouse.updated_at = now
    session.add(warehouse)

    # Cascade-restore all locations that were soft-deleted at the same timestamp
    await session.execute(
        update(InventoryLocation)
        .where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at == cascade_ts,
        )
        .values(deleted_at=None)
    )

    await session.flush()
    await session.refresh(warehouse)
    return WarehouseRead(
        id=warehouse.id,
        warehouse_name=warehouse.warehouse_name,
        address=warehouse.address,
        is_active=warehouse.is_active,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
        deleted_at=warehouse.deleted_at,
    )


@router.post("/{warehouse_id}/duplicate", response_model=WarehouseDuplicateResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_warehouse(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Deep-duplicate a warehouse: creates a new inactive warehouse and copies all
    its live InventoryLocation rows via a single INSERT...SELECT round-trip.

    The duplicate starts as inactive — the user must explicitly activate it.
    Name collision is handled by appending a timestamp suffix when "(Copy)" is taken.
    """
    original = await session.get(Warehouse, warehouse_id)
    if original is None or original.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # --- Name collision guard ---
    copy_name = f"{original.warehouse_name} (Copy)"
    existing = await session.execute(
        select(Warehouse).where(Warehouse.warehouse_name == copy_name)
    )
    if existing.scalar_one_or_none() is not None:
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        copy_name = f"{original.warehouse_name} (Copy {ts})"

    # --- Create the new warehouse row ---
    new_warehouse = Warehouse(
        warehouse_name=copy_name,
        address=original.address,
        is_active=False,  # always starts inactive
    )
    session.add(new_warehouse)
    await session.flush()  # obtain new_warehouse.id before INSERT...SELECT

    # --- Deep copy all live locations in one SQL round-trip ---
    result = await session.execute(
        text("""
            INSERT INTO inventory_location
                (warehouse_id, section, zone, aisle, rack, bin, inventory_type_id, created_at)
            SELECT
                :new_id, section, zone, aisle, rack, bin, inventory_type_id, NOW()
            FROM inventory_location
            WHERE warehouse_id = :orig_id
              AND deleted_at IS NULL
            RETURNING id
        """),
        {"new_id": new_warehouse.id, "orig_id": warehouse_id},
    )
    locations_copied = len(result.fetchall())

    await session.commit()
    await session.refresh(new_warehouse)

    return WarehouseDuplicateResponse(
        original_id=warehouse_id,
        new_warehouse=WarehouseRead(
            id=new_warehouse.id,
            warehouse_name=new_warehouse.warehouse_name,
            address=new_warehouse.address,
            is_active=new_warehouse.is_active,
            created_at=new_warehouse.created_at,
            updated_at=new_warehouse.updated_at,
            deleted_at=new_warehouse.deleted_at,
        ),
        locations_copied=locations_copied,
    )


# ---------------------------------------------------------------------------
# Inventory Locations
# ---------------------------------------------------------------------------

@router.get("/{warehouse_id}/locations/hierarchy")
async def get_locations_hierarchy(
    warehouse_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Return inventory locations as a nested tree: Warehouse > Section > Zone > Aisle > Rack > Bin.

    Each node includes a 'summary' (e.g. 'Aisle 01 contains 5 racks').
    No hierarchy levels are skipped.
    """
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    query = (
        select(InventoryLocation)
        .where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at.is_(None),
        )
        .order_by(
            InventoryLocation.sort_order.asc().nulls_last(),
            InventoryLocation.id,
        )
    )
    result = await session.execute(query)
    locations = result.scalars().all()
    tree = _build_location_tree(
        locations,
        warehouse_names={warehouse_id: warehouse.warehouse_name},
    )
    return tree


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
        .where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at.is_(None),
        )
        .order_by(
            InventoryLocation.sort_order.asc().nulls_last(),
            InventoryLocation.id,
        )
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
            display_code=loc.display_code,
            is_active=loc.is_active,
            sort_order=loc.sort_order,
            created_at=loc.created_at,
        )
        for loc in result.scalars().all()
    ]


@router.post(
    "/{warehouse_id}/locations",
    response_model=InventoryLocationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_location(
    warehouse_id: int,
    body: InventoryLocationCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new inventory location in a warehouse."""
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    loc = InventoryLocation(warehouse_id=warehouse_id, **body.model_dump())
    session.add(loc)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Location code already exists (duplicate section/zone/aisle/rack/bin)",
        )
    await session.refresh(loc)
    return InventoryLocationRead(
        id=loc.id,
        warehouse_id=loc.warehouse_id,
        section=loc.section,
        zone=loc.zone,
        aisle=loc.aisle,
        rack=loc.rack,
        bin=loc.bin,
        inventory_type_id=loc.inventory_type_id,
        display_code=loc.display_code,
        is_active=loc.is_active,
        sort_order=loc.sort_order,
        created_at=loc.created_at,
    )


@router.patch("/locations/{location_id}", response_model=InventoryLocationRead)
async def update_location(
    location_id: int,
    body: InventoryLocationUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update an inventory location."""
    loc = await session.get(InventoryLocation, location_id)
    if loc is None or loc.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = body.model_dump(exclude_unset=True)

    # Inventory guard — block deactivation if location (or children) holds stock
    if update_data.get("is_active") is False and loc.is_active is True:
        child_ids = await get_location_children_ids(session, loc)
        has_stock, total_qty, loc_count = await check_stock_at_locations(session, child_ids)
        if has_stock:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete: Location contains active stock.",
            )

    for key, value in update_data.items():
        setattr(loc, key, value)

    # Recompute display_code when hierarchy fields change (trigger only fires
    # on INSERT; for UPDATE we recalculate in Python to stay consistent).
    parts = [loc.section, loc.zone, loc.aisle, loc.rack, loc.bin]
    loc.display_code = "-".join(p for p in parts if p) or None

    await session.flush()
    await session.refresh(loc)
    return InventoryLocationRead(
        id=loc.id,
        warehouse_id=loc.warehouse_id,
        section=loc.section,
        zone=loc.zone,
        aisle=loc.aisle,
        rack=loc.rack,
        bin=loc.bin,
        inventory_type_id=loc.inventory_type_id,
        display_code=loc.display_code,
        is_active=loc.is_active,
        sort_order=loc.sort_order,
        created_at=loc.created_at,
    )


@router.patch(
    "/{warehouse_id}/locations/bulk-update",
    response_model=BulkLocationUpdateResponse,
)
async def bulk_update_locations(
    warehouse_id: int,
    body: BulkLocationUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Atomically update multiple locations in one request.

    Each item is processed independently inside a SAVEPOINT so a single row
    failure does not roll back the other updates. Returns a per-row success /
    error result alongside aggregate counts.
    """
    results: list[BulkLocationUpdateResult] = []
    updated = 0
    failed = 0

    for item in body.locations:
        try:
            async with session.begin_nested():
                loc = await session.get(InventoryLocation, item.id)
                if loc is None or loc.warehouse_id != warehouse_id or loc.deleted_at is not None:
                    raise ValueError("Location not found or does not belong to this warehouse")

                patch = item.model_dump(exclude_unset=True, exclude={"id"})

                # Inventory guard — block deactivation while stock is held
                if patch.get("is_active") is False and loc.is_active is True:
                    child_ids = await get_location_children_ids(session, loc)
                    has_stock, _, _ = await check_stock_at_locations(session, child_ids)
                    if has_stock:
                        raise ValueError("Cannot deactivate: location holds active stock")

                for key, value in patch.items():
                    setattr(loc, key, value)

                # Recompute display_code (trigger only fires on INSERT)
                parts = [loc.section, loc.zone, loc.aisle, loc.rack, loc.bin]
                loc.display_code = "-".join(p for p in parts if p) or None

            results.append(BulkLocationUpdateResult(id=item.id, success=True))
            updated += 1

        except Exception as exc:  # noqa: BLE001
            results.append(
                BulkLocationUpdateResult(id=item.id, success=False, error=str(exc))
            )
            failed += 1

    return BulkLocationUpdateResponse(updated=updated, failed=failed, results=results)


@router.delete("/locations/{location_id}")
async def soft_delete_location(
    location_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Recursively soft-delete a location and all its children.

    Determines the hierarchy level of the target location (Section, Zone,
    Aisle, Rack, or Bin) and cascades the soft-delete to every location
    sharing the same prefix.  For example, deleting a Section "A" also
    deletes all Zones, Aisles, Racks, and Bins under Section "A".

    The inventory guard checks the FULL subtree — if any child location
    holds active stock (quantity_available > 0 OR reserved_quantity > 0),
    the entire operation is blocked with HTTP 400.

    Returns {"deleted": N} with the count of rows soft-deleted.
    """
    deleted_count = await _soft_delete_location_service(session, location_id)
    return {"deleted": deleted_count}


@router.post("/locations/{location_id}/restore", response_model=InventoryLocationRead)
async def restore_location(
    location_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Restore a soft-deleted inventory location (clears deleted_at)."""
    loc = await session.get(InventoryLocation, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    if loc.deleted_at is None:
        raise HTTPException(status_code=400, detail="Location is not deleted")
    loc.deleted_at = None
    await session.flush()
    await session.refresh(loc)
    return InventoryLocationRead(
        id=loc.id,
        warehouse_id=loc.warehouse_id,
        section=loc.section,
        zone=loc.zone,
        aisle=loc.aisle,
        rack=loc.rack,
        bin=loc.bin,
        inventory_type_id=loc.inventory_type_id,
        display_code=loc.display_code,
        is_active=loc.is_active,
        sort_order=loc.sort_order,
        created_at=loc.created_at,
    )


@router.delete("/{warehouse_id}/locations/subtree")
async def soft_delete_location_subtree(
    warehouse_id: int,
    section: str | None = Query(None),
    zone: str | None = Query(None),
    aisle: str | None = Query(None),
    rack: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Soft-delete all locations in a warehouse that match the given hierarchy prefix.

    At least one filter is required. Matching is exact (e.g. section='A' deletes every
    location whose section equals 'A', regardless of zone/aisle/rack/bin).
    Returns {"deleted": N} with the count of rows soft-deleted.
    """
    if not any([section, zone, aisle, rack]):
        raise HTTPException(
            status_code=400,
            detail="At least one of section, zone, aisle, or rack is required.",
        )

    # Inventory guard — block if any location in the subtree holds stock
    loc_ids = await get_subtree_location_ids(
        session, warehouse_id, section=section, zone=zone, aisle=aisle, rack=rack,
    )
    has_stock, total_qty, loc_count = await check_stock_at_locations(session, loc_ids)
    if has_stock:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete: Location contains active stock.",
        )

    stmt = (
        update(InventoryLocation)
        .where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at.is_(None),
        )
    )
    if section is not None:
        stmt = stmt.where(InventoryLocation.section == section)
    if zone is not None:
        stmt = stmt.where(InventoryLocation.zone == zone)
    if aisle is not None:
        stmt = stmt.where(InventoryLocation.aisle == aisle)
    if rack is not None:
        stmt = stmt.where(InventoryLocation.rack == rack)

    result = await session.execute(stmt.values(deleted_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    await session.flush()
    return {"deleted": result.rowcount}


@router.patch("/{warehouse_id}/locations/rename-level", response_model=RenameLevelResponse)
async def rename_location_level(
    warehouse_id: int,
    body: RenameLevelRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Bulk-rename a hierarchy level across all matching locations.

    For example, renaming section "A" to "B" updates every location in
    that warehouse whose section equals "A".  The optional parent path
    fields (section/zone/aisle/rack) narrow the scope.
    """
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Map level name to the ORM column
    _LEVEL_COLS = {
        "section": InventoryLocation.section,
        "zone": InventoryLocation.zone,
        "aisle": InventoryLocation.aisle,
        "rack": InventoryLocation.rack,
        "bin": InventoryLocation.bin,
    }
    col = _LEVEL_COLS[body.level]

    stmt = (
        update(InventoryLocation)
        .where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at.is_(None),
            col == body.old_value,
        )
    )

    # Apply parent path filters (only levels above the target level)
    if body.level != "section" and body.section is not None:
        stmt = stmt.where(InventoryLocation.section == body.section)
    if body.level not in ("section", "zone") and body.zone is not None:
        stmt = stmt.where(InventoryLocation.zone == body.zone)
    if body.level not in ("section", "zone", "aisle") and body.aisle is not None:
        stmt = stmt.where(InventoryLocation.aisle == body.aisle)
    if body.level == "bin" and body.rack is not None:
        stmt = stmt.where(InventoryLocation.rack == body.rack)

    result = await session.execute(stmt.values({col: body.new_value}))
    count = result.rowcount

    # Recompute display_code for affected rows
    if count > 0:
        affected = await session.execute(
            select(InventoryLocation).where(
                InventoryLocation.warehouse_id == warehouse_id,
                InventoryLocation.deleted_at.is_(None),
                col == body.new_value,
            )
        )
        for loc in affected.scalars().all():
            parts = [loc.section, loc.zone, loc.aisle, loc.rack, loc.bin]
            loc.display_code = "-".join(p for p in parts if p) or None

    await session.flush()

    return RenameLevelResponse(
        updated_count=count,
        level=body.level,
        old_value=body.old_value,
        new_value=body.new_value,
    )


@router.post(
    "/{warehouse_id}/locations/bulk-generate",
    response_model=BulkGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_generate_locations(
    warehouse_id: int,
    body: BulkGenerateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Bulk-generate inventory locations from range specifications.

    Accepts optional SegmentRange objects for section, zone, aisle, rack,
    and bin.  Expands the Cartesian product of all specified ranges and
    inserts the resulting locations.  Duplicates (matching the
    uq_location_address constraint) are skipped and reported.

    Maximum 10,000 combinations per request.
    """
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    try:
        result = await _bulk_generate_locations(session, warehouse_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result



# ---------------------------------------------------------------------------
# Inventory Levels (enriched stock matrix)
# ---------------------------------------------------------------------------

def _location_summary(loc: InventoryLocation) -> LocationSummary:
    """Build a LocationSummary from an InventoryLocation ORM object."""
    return LocationSummary(
        id=loc.id,
        code=loc.full_location_code or str(loc.id),
        section=loc.section,
        zone=loc.zone,
        aisle=loc.aisle,
        rack=loc.rack,
        bin=loc.bin,
    )


@router.get(
    "/{warehouse_id}/inventory",
    response_model=PaginatedResponse[InventoryLevelEnrichedRead],
)
async def list_inventory_levels(
    warehouse_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: int | None = Query(None),
    search: str | None = Query(None, description="Search by item name or SKU"),
    stock_status: str | None = Query(None, description="Filter: ok, low, critical, out_of_stock, overstock"),
    session: AsyncSession = Depends(get_session),
):
    """
    List enriched inventory levels for a warehouse.

    Joins Item and InventoryLocation so each row includes the item name,
    master SKU, location code, and a computed stock_status.
    """
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    query = (
        select(InventoryLevel)
        .join(InventoryLocation, InventoryLevel.location_id == InventoryLocation.id)
        .join(Item, InventoryLevel.item_id == Item.item_id)
        .where(InventoryLocation.warehouse_id == warehouse_id)
        .options(
            selectinload(InventoryLevel.location),
        )
    )

    if item_id is not None:
        query = query.where(InventoryLevel.item_id == item_id)
    if search:
        query = query.where(
            (Item.item_name.ilike(f"%{search}%")) | (Item.master_sku.ilike(f"%{search}%"))
        )

    # Count total before pagination
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(InventoryLevel.id).offset(offset).limit(page_size)
    result = await session.execute(query)
    levels = result.scalars().all()

    # Batch-load items for these levels
    item_ids = {lv.item_id for lv in levels}
    items_map: dict[int, Item] = {}
    if item_ids:
        item_result = await session.execute(
            select(Item).where(Item.item_id.in_(item_ids))
        )
        items_map = {i.item_id: i for i in item_result.scalars().all()}

    # Build enriched response, filtering by stock_status if requested
    enriched: list[InventoryLevelEnrichedRead] = []
    for lv in levels:
        item = items_map.get(lv.item_id)
        computed_status = lv.stock_status.lower()  # model property returns uppercase
        if stock_status and computed_status != stock_status:
            continue
        enriched.append(
            InventoryLevelEnrichedRead(
                id=lv.id,
                location_id=lv.location_id,
                item_id=lv.item_id,
                item_name=item.item_name if item else "Unknown",
                master_sku=item.master_sku if item else "—",
                location=_location_summary(lv.location),
                lot_id=lv.lot_id,
                quantity_available=lv.quantity_available,
                reserved_quantity=lv.reserved_quantity,
                reorder_point=lv.reorder_point,
                safety_stock=lv.safety_stock,
                max_stock=lv.max_stock,
                stock_status=computed_status,
                alert_triggered_at=lv.alert_triggered_at,
                alert_acknowledged=lv.alert_acknowledged,
                created_at=lv.created_at,
                updated_at=lv.updated_at,
            )
        )

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=enriched,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# Inventory Movements
# ---------------------------------------------------------------------------

@router.get(
    "/{warehouse_id}/movements",
    response_model=PaginatedResponse[InventoryMovementRead],
)
async def list_movements(
    warehouse_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    List movement history for a warehouse (paginated).

    Joins InventoryMovement → InventoryTransaction → InventoryLocation
    to filter by warehouse and enrich with item info.
    """
    warehouse = await session.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    # Movements that have at least one transaction in this warehouse
    query = (
        select(InventoryMovement)
        .join(InventoryTransaction, InventoryMovement.id == InventoryTransaction.movement_id)
        .join(InventoryLocation, InventoryTransaction.location_id == InventoryLocation.id)
        .where(InventoryLocation.warehouse_id == warehouse_id)
        .distinct()
        .options(
            selectinload(InventoryMovement.movement_type),
            selectinload(InventoryMovement.transactions),
        )
    )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(InventoryMovement.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    movements = result.scalars().unique().all()

    # Batch-load items referenced by transactions
    item_ids: set[int] = set()
    for mv in movements:
        for tx in mv.transactions:
            item_ids.add(tx.item_id)
    items_map: dict[int, Item] = {}
    if item_ids:
        item_result = await session.execute(select(Item).where(Item.item_id.in_(item_ids)))
        items_map = {i.item_id: i for i in item_result.scalars().all()}

    reads: list[InventoryMovementRead] = []
    for mv in movements:
        # Use the first transaction for item info and quantity summary
        first_tx = mv.transactions[0] if mv.transactions else None
        item = items_map.get(first_tx.item_id) if first_tx else None
        total_qty = sum(tx.quantity_change for tx in mv.transactions)
        is_inbound = first_tx.is_inbound if first_tx else True

        reads.append(
            InventoryMovementRead(
                id=mv.id,
                warehouse_id=warehouse_id,
                movement_type_id=mv.movement_type_id,
                movement_type=MovementTypeRead(
                    id=mv.movement_type.id,
                    name=mv.movement_type.movement_name,
                ) if mv.movement_type else MovementTypeRead(id=0, name="Unknown"),
                item_id=first_tx.item_id if first_tx else 0,
                item_name=item.item_name if item else "Unknown",
                master_sku=item.master_sku if item else "—",
                reference_number=mv.reference_id,
                notes=None,
                quantity=total_qty,
                is_inbound=is_inbound,
                created_at=mv.created_at,
                created_by=None,
            )
        )

    pages_count = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=reads,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages_count,
    )


@router.post(
    "/movements",
    response_model=InventoryMovementRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_movement(
    body: InventoryMovementCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Record a stock movement (inbound / outbound / transfer).

    Creates one InventoryMovement record and one or more InventoryTransaction
    records. Updates InventoryLevel quantities accordingly.
    """
    # Validate movement type
    mt = await session.get(MovementType, body.movement_type_id)
    if mt is None:
        raise HTTPException(status_code=404, detail="Movement type not found")

    # Validate item
    item = await session.get(Item, body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Validate all locations belong to the specified warehouse
    loc_ids = [tx.location_id for tx in body.transactions]
    loc_result = await session.execute(
        select(InventoryLocation).where(InventoryLocation.id.in_(loc_ids))
    )
    locations = {loc.id: loc for loc in loc_result.scalars().all()}
    for tx in body.transactions:
        loc = locations.get(tx.location_id)
        if loc is None:
            raise HTTPException(status_code=404, detail=f"Location {tx.location_id} not found")
        if loc.warehouse_id != body.warehouse_id:
            raise HTTPException(
                status_code=400,
                detail=f"Location {tx.location_id} does not belong to warehouse {body.warehouse_id}",
            )

    # Create the movement
    movement = InventoryMovement(
        movement_type_id=body.movement_type_id,
        reference_id=body.reference_number,
    )
    session.add(movement)
    await session.flush()

    # Create transactions and update inventory levels
    total_qty = 0
    first_inbound = True
    for tx_data in body.transactions:
        tx = InventoryTransaction(
            item_id=body.item_id,
            location_id=tx_data.location_id,
            movement_id=movement.id,
            is_inbound=tx_data.is_inbound,
            quantity_change=tx_data.quantity_change,
        )
        session.add(tx)
        total_qty += tx_data.quantity_change
        first_inbound = tx_data.is_inbound

        # Update or create inventory level
        level_result = await session.execute(
            select(InventoryLevel).where(
                InventoryLevel.item_id == body.item_id,
                InventoryLevel.location_id == tx_data.location_id,
            )
        )
        level = level_result.scalar_one_or_none()

        if level is None:
            # Auto-create level for inbound; error for outbound on non-existent stock
            if not tx_data.is_inbound:
                raise HTTPException(
                    status_code=400,
                    detail=f"No inventory at location {tx_data.location_id} for item {body.item_id}",
                )
            level = InventoryLevel(
                item_id=body.item_id,
                location_id=tx_data.location_id,
                quantity_available=tx_data.quantity_change,
            )
            session.add(level)
        else:
            if tx_data.is_inbound:
                level.quantity_available += tx_data.quantity_change
            else:
                if level.quantity_available < tx_data.quantity_change:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Insufficient stock at location {tx_data.location_id}: "
                            f"available={level.quantity_available}, requested={tx_data.quantity_change}"
                        ),
                    )
                level.quantity_available -= tx_data.quantity_change
            level.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await session.flush()
    await session.refresh(movement)

    return InventoryMovementRead(
        id=movement.id,
        warehouse_id=body.warehouse_id,
        movement_type_id=movement.movement_type_id,
        movement_type=MovementTypeRead(id=mt.id, name=mt.movement_name),
        item_id=body.item_id,
        item_name=item.item_name,
        master_sku=item.master_sku,
        reference_number=movement.reference_id,
        notes=body.notes,
        quantity=total_qty,
        is_inbound=first_inbound,
        created_at=movement.created_at,
        created_by=current_user.user_id,
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
            resolution_notes=a.resolution_notes,
            resolved_by_user_id=a.resolved_by_user_id,
            created_at=a.created_at,
        )
        for a in result.scalars().all()
    ]


@router.patch(
    "/alerts/{alert_id}/resolve",
    response_model=InventoryAlertRead,
)
async def resolve_alert(
    alert_id: int,
    body: AlertResolveRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Mark an inventory alert as resolved."""
    alert = await session.get(InventoryAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.is_resolved:
        raise HTTPException(status_code=400, detail="Alert is already resolved")

    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    alert.resolved_by_user_id = current_user.user_id
    alert.resolution_notes = body.resolution_notes

    await session.flush()
    await session.refresh(alert)

    return InventoryAlertRead(
        id=alert.id,
        inventory_level_id=alert.inventory_level_id,
        item_id=alert.item_id,
        warehouse_id=alert.warehouse_id,
        alert_type=alert.alert_type,
        current_quantity=alert.current_quantity,
        threshold_quantity=alert.threshold_quantity,
        alert_message=alert.alert_message,
        is_resolved=alert.is_resolved,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        resolved_by_user_id=alert.resolved_by_user_id,
        created_at=alert.created_at,
    )


# ---------------------------------------------------------------------------
# Stock Reservation / Release / Bundle Fulfillment
# ---------------------------------------------------------------------------

@router.post(
    "/reserve",
    response_model=ReserveResponse,
    status_code=status.HTTP_200_OK,
)
async def reserve_stock(
    body: ReserveRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Pessimistically reserve stock for a standalone item (order received).

    Increments reserved_quantity on the InventoryLevel rows for this item
    in the specified warehouse. Uses SELECT ... FOR UPDATE to prevent concurrent
    oversell.

    Raises HTTP 409 if ATP < requested quantity.
    """
    from app.services.bundle.fulfillment import reserve_inventory, InsufficientStockError

    try:
        await reserve_inventory(
            item_id=body.item_id,
            quantity=body.quantity,
            warehouse_id=body.warehouse_id,
            session=session,
        )
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return ReserveResponse(
        item_id=body.item_id,
        quantity_reserved=body.quantity,
        warehouse_id=body.warehouse_id,
    )


@router.post("/release", status_code=status.HTTP_204_NO_CONTENT)
async def release_stock(
    body: ReleaseRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Release a previously placed stock reservation (e.g., order cancelled).

    Decrements reserved_quantity on the InventoryLevel rows. Clamps to zero
    to handle partial releases gracefully.
    """
    from app.services.bundle.fulfillment import release_reservation

    await release_reservation(
        item_id=body.item_id,
        quantity=body.quantity,
        warehouse_id=body.warehouse_id,
        session=session,
    )


@router.post(
    "/fulfill/bundle",
    response_model=list[InventoryMovementRead],
    status_code=status.HTTP_201_CREATED,
)
async def fulfill_bundle(
    body: BundleFulfillRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """
    Atomically deduct stock from ALL components of a Bundle on sale.

    Creates one InventoryMovement (type=Shipment) and one InventoryTransaction
    per (component, location) pair.  Raises HTTP 409 if any component's ATP
    is insufficient.
    """
    from app.services.bundle.fulfillment import (
        deduct_bundle_stock,
        BundleNotFoundError,
        InsufficientStockError,
    )

    try:
        transactions = await deduct_bundle_stock(
            bundle_item_id=body.bundle_item_id,
            bundle_qty_sold=body.bundle_qty_sold,
            warehouse_id=body.warehouse_id,
            order_reference=body.order_reference,
            session=session,
        )
    except BundleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InsufficientStockError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    # Build lightweight response from the created transactions
    reads: list[InventoryMovementRead] = []
    if transactions:
        mv = await session.get(InventoryMovement, transactions[0].movement_id)
        mt = await session.get(MovementType, mv.movement_type_id) if mv else None
        item_ids = {tx.item_id for tx in transactions}
        item_result = await session.execute(select(Item).where(Item.item_id.in_(item_ids)))
        items_map = {i.item_id: i for i in item_result.scalars().all()}

        for tx in transactions:
            item = items_map.get(tx.item_id)
            reads.append(
                InventoryMovementRead(
                    id=tx.movement_id or 0,
                    warehouse_id=body.warehouse_id,
                    movement_type_id=mv.movement_type_id if mv else 0,
                    movement_type=MovementTypeRead(
                        id=mt.id if mt else 0,
                        name=mt.movement_name if mt else "Shipment",
                    ),
                    item_id=tx.item_id,
                    item_name=item.item_name if item else "Unknown",
                    master_sku=item.master_sku if item else "—",
                    reference_number=mv.reference_id if mv else None,
                    notes=None,
                    quantity=tx.quantity_change,
                    is_inbound=False,
                    created_at=tx.created_at,
                    created_by=current_user.user_id,
                )
            )

    return reads
