"""
Location Bulk Generator Service

Expands SegmentRange specifications into a Cartesian product of location
tuples and bulk-inserts them into inventory_location.

WHY this exists:
    Warehouse managers need to scaffold hundreds of locations at once
    (e.g. "sections A1-A5, zones COLD/DRY, aisles 01-10, racks R1-R8,
    bins B01-B04") instead of creating them one-by-one via the UI.

Key design decisions:
    - Uses itertools.product for Cartesian expansion
    - Caps total combinations at MAX_COMBINATIONS (10,000) to prevent
      accidental creation of millions of rows
    - Inserts one-by-one with session.begin_nested() SAVEPOINTs so that
      IntegrityError on one row (duplicate) does not roll back the rest
    - Does NOT compute display_code — the BEFORE INSERT trigger
      trg_generate_display_code handles that automatically
    - Does NOT call session.commit() — the FastAPI get_session()
      dependency handles the final commit
"""

import itertools
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import InventoryLocation
from app.schemas.warehouse import (
    BulkGenerateRequest,
    BulkGenerateResponse,
    BulkGenerateError,
)

MAX_COMBINATIONS = 10_000

_SEGMENTS = ("section", "zone", "aisle", "rack", "bin")


def expand_ranges(request: BulkGenerateRequest) -> list[dict[str, str | None]]:
    """
    Expand SegmentRange specs into a list of location dicts.

    Each dict has keys: section, zone, aisle, rack, bin.
    If a range is None for a level, that key is None in every dict.

    Raises:
        ValueError: If total combinations exceed MAX_COMBINATIONS.
    """
    expanded: dict[str, list[str | None]] = {}

    for seg in _SEGMENTS:
        spec = getattr(request, seg)
        if spec is not None:
            expanded[seg] = spec.expand()
        else:
            expanded[seg] = [None]

    # Pre-check total before materialising (avoids memory spike)
    total = 1
    for values in expanded.values():
        total *= len(values)

    if total > MAX_COMBINATIONS:
        raise ValueError(
            f"Total combinations ({total:,}) exceeds maximum allowed "
            f"({MAX_COMBINATIONS:,}). Reduce your ranges."
        )

    combos = list(itertools.product(*(expanded[seg] for seg in _SEGMENTS)))
    return [dict(zip(_SEGMENTS, combo)) for combo in combos]


async def bulk_generate_locations(
    session: AsyncSession,
    warehouse_id: int,
    request: BulkGenerateRequest,
) -> BulkGenerateResponse:
    """
    Expand ranges, validate each combination, and insert into DB.

    Uses a SAVEPOINT (session.begin_nested()) per row so that an
    IntegrityError on one duplicate does not roll back other inserts.

    WHY not ON CONFLICT DO NOTHING:
        The unique index uq_location_address is a functional index
        (uses COALESCE expressions). PostgreSQL's ON CONFLICT clause
        requires naming a constraint or simple columns — functional
        indexes are problematic. Per-row SAVEPOINTs are reliable and
        the standard asyncpg pattern for partial-failure tolerance.
    """
    locations = expand_ranges(request)
    created = 0
    skipped = 0
    errors: list[BulkGenerateError] = []

    for loc_dict in locations:
        # Human-readable label for error reporting
        parts = [
            loc_dict[k]
            for k in _SEGMENTS
            if loc_dict[k] is not None
        ]
        label = "-".join(parts) if parts else "(empty)"

        # Validate VARCHAR(50) constraint
        too_long = [
            k for k in _SEGMENTS
            if loc_dict[k] is not None and len(loc_dict[k]) > 50
        ]
        if too_long:
            errors.append(BulkGenerateError(
                location=label,
                reason=f"Field(s) {', '.join(too_long)} exceed 50 characters",
            ))
            skipped += 1
            continue

        loc = InventoryLocation(
            warehouse_id=warehouse_id,
            section=loc_dict["section"],
            zone=loc_dict["zone"],
            aisle=loc_dict["aisle"],
            rack=loc_dict["rack"],
            bin=loc_dict["bin"],
            inventory_type_id=request.inventory_type_id,
            is_active=request.is_active,
        )

        try:
            async with session.begin_nested():  # SAVEPOINT
                session.add(loc)
                await session.flush()
            created += 1
        except IntegrityError:
            skipped += 1
            errors.append(BulkGenerateError(
                location=label,
                reason="Duplicate location (already exists)",
            ))

    return BulkGenerateResponse(
        warehouse_id=warehouse_id,
        total_requested=len(locations),
        created=created,
        skipped=skipped,
        errors=errors,
    )
