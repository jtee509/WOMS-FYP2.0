"""
Inventory Guard Service

Prevents deletion / deactivation of warehouses and locations that still
hold stock.  The guard checks InventoryLevel rows where
quantity_available > 0 OR reserved_quantity > 0.

WHY:
    Deleting a warehouse or location that has live stock would orphan
    inventory data, making it impossible to reconcile counts.  This
    service provides a reusable guard that any endpoint can call before
    performing a destructive operation.

Recursive Soft-Delete:
    The soft_delete_location() function determines the hierarchy level of
    a location (Section > Zone > Aisle > Rack > Bin) and cascades the
    soft-delete to all children sharing the same prefix.  For example,
    deleting a "Section" node soft-deletes every Zone/Aisle/Rack/Bin
    underneath it.  The inventory guard runs against the FULL subtree
    before any deletion occurs.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import InventoryLevel, InventoryLocation


# ---------------------------------------------------------------------------
# Hierarchy helpers
# ---------------------------------------------------------------------------

# Ordered from deepest to shallowest; first match determines the level.
_HIERARCHY_LEVELS = ("bin", "rack", "aisle", "zone", "section")


def _get_location_level(loc: InventoryLocation) -> str | None:
    """
    Return the deepest hierarchy level that is set on a location.

    Examples:
        section="A", zone=None  -> "section"
        section="A", zone="Z1", aisle="01", rack=None -> "aisle"
        section="A", zone="Z1", aisle="01", rack="R1", bin="B5" -> "bin"
    """
    for level in _HIERARCHY_LEVELS:
        if getattr(loc, level, None) is not None:
            return level
    return None


# ---------------------------------------------------------------------------
# Stock checks
# ---------------------------------------------------------------------------

async def check_stock_at_locations(
    session: AsyncSession,
    location_ids: list[int],
) -> tuple[bool, int, int]:
    """
    Check whether any of the given location IDs hold stock.

    Returns:
        (has_stock, total_qty, location_count)
        - has_stock: True if any location has quantity_available > 0 or reserved_quantity > 0
        - total_qty: sum of quantity_available + reserved_quantity across matching rows
        - location_count: number of distinct locations with stock
    """
    if not location_ids:
        return False, 0, 0

    result = await session.execute(
        select(
            func.coalesce(func.sum(InventoryLevel.quantity_available + InventoryLevel.reserved_quantity), 0),
            func.count(func.distinct(InventoryLevel.location_id)),
        )
        .where(
            InventoryLevel.location_id.in_(location_ids),
            or_(
                InventoryLevel.quantity_available > 0,
                InventoryLevel.reserved_quantity > 0,
            ),
        )
    )
    row = result.one()
    total_qty = int(row[0])
    loc_count = int(row[1])
    return total_qty > 0, total_qty, loc_count


# ---------------------------------------------------------------------------
# Location ID finders
# ---------------------------------------------------------------------------

async def get_warehouse_location_ids(
    session: AsyncSession,
    warehouse_id: int,
) -> list[int]:
    """Return all live (non-deleted) location IDs for a warehouse."""
    result = await session.execute(
        select(InventoryLocation.id).where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.deleted_at.is_(None),
        )
    )
    return [row[0] for row in result.all()]


async def get_subtree_location_ids(
    session: AsyncSession,
    warehouse_id: int,
    *,
    section: str | None = None,
    zone: str | None = None,
    aisle: str | None = None,
    rack: str | None = None,
) -> list[int]:
    """Return live location IDs matching the given hierarchy prefix."""
    query = select(InventoryLocation.id).where(
        InventoryLocation.warehouse_id == warehouse_id,
        InventoryLocation.deleted_at.is_(None),
    )
    if section is not None:
        query = query.where(InventoryLocation.section == section)
    if zone is not None:
        query = query.where(InventoryLocation.zone == zone)
    if aisle is not None:
        query = query.where(InventoryLocation.aisle == aisle)
    if rack is not None:
        query = query.where(InventoryLocation.rack == rack)

    result = await session.execute(query)
    return [row[0] for row in result.all()]


async def get_location_children_ids(
    session: AsyncSession,
    loc: InventoryLocation,
) -> list[int]:
    """
    Return IDs of all live child locations sharing the same hierarchy prefix.

    Determines the deepest set level of the given location and queries for
    all locations in the same warehouse that match the same prefix values.
    This includes the location itself.

    WHY:
        When soft-deleting a parent node (e.g. a Section), all child nodes
        (Zones, Aisles, Racks, Bins within that Section) must also be
        deleted. This function builds the filter dynamically based on the
        location's hierarchy depth.

    Examples:
        Location (section="A", zone=None, ...) -> all locs where section="A"
        Location (section="A", zone="Z1", aisle=None, ...) -> all locs where
            section="A" AND zone="Z1"
    """
    query = select(InventoryLocation.id).where(
        InventoryLocation.warehouse_id == loc.warehouse_id,
        InventoryLocation.deleted_at.is_(None),
    )

    # Build prefix filter: match all set hierarchy levels from top down
    # This chains equality filters for every level that IS set on the parent,
    # meaning children (which share those same values but go deeper) are included.
    if loc.section is not None:
        query = query.where(InventoryLocation.section == loc.section)
    if loc.zone is not None:
        query = query.where(InventoryLocation.zone == loc.zone)
    if loc.aisle is not None:
        query = query.where(InventoryLocation.aisle == loc.aisle)
    if loc.rack is not None:
        query = query.where(InventoryLocation.rack == loc.rack)
    if loc.bin is not None:
        query = query.where(InventoryLocation.bin == loc.bin)

    result = await session.execute(query)
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Recursive Soft-Delete
# ---------------------------------------------------------------------------

async def soft_delete_location(
    session: AsyncSession,
    location_id: int,
) -> int:
    """
    Soft-delete a location AND all of its child locations recursively.

    Logic:
        1. Load the location and determine its hierarchy level.
        2. Find all child location IDs sharing the same prefix.
        3. Run the inventory guard on the full set — if ANY location (or
           child) holds stock (quantity_available > 0 OR reserved_quantity > 0),
           raise HTTP 400 with "Cannot delete: Location contains active stock."
        4. Bulk-UPDATE all matching locations: set deleted_at = now().
        5. Return the count of rows affected.

    Raises:
        HTTPException 404 if the location doesn't exist or is already deleted.
        HTTPException 400 if the location or any child contains active stock.

    Returns:
        Number of locations soft-deleted (including the target location).
    """
    loc = await session.get(InventoryLocation, location_id)
    if loc is None or loc.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Location not found")

    # Find all children (including self) that share the same hierarchy prefix
    child_ids = await get_location_children_ids(session, loc)

    # Inventory guard — block if ANY location in the subtree holds stock
    has_stock, total_qty, loc_count = await check_stock_at_locations(session, child_ids)
    if has_stock:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete: Location contains active stock.",
        )

    # Bulk soft-delete all matching locations
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await session.execute(
        update(InventoryLocation)
        .where(InventoryLocation.id.in_(child_ids))
        .values(deleted_at=now)
    )
    await session.flush()
    return result.rowcount
