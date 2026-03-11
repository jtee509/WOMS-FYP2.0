"""
Items Import — Orchestrator
============================
Ties parser + validator together and bulk-inserts valid rows.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.items import Item
from app.schemas.items import ImportResult
from .parser import parse_file
from .validator import validate_and_resolve


async def import_items(
    session: AsyncSession,
    file_bytes: bytes,
    filename: str,
) -> ImportResult:
    """
    Parse, validate, and insert items from an uploaded CSV or Excel file.

    Args:
        session:    Active async DB session (caller owns commit/rollback).
        file_bytes: Raw file content.
        filename:   Original filename (used to detect CSV vs Excel).

    Returns:
        ImportResult with counts and per-row errors.

    Raises:
        ValueError: If the file cannot be parsed or contains no data rows.
    """
    # 1. Parse file → normalised row dicts
    rows = parse_file(file_bytes, filename)
    if not rows:
        raise ValueError("The file contains no data rows.")

    # 2. Validate + resolve FK names → IDs
    valid_rows, errors = await validate_and_resolve(rows, session)

    # 3. Bulk insert valid rows
    for row in valid_rows:
        session.add(Item(**row))

    if valid_rows:
        await session.flush()

    return ImportResult(
        total_rows=len(rows),
        success_rows=len(valid_rows),
        error_rows=len(errors),
        errors=errors,
    )
