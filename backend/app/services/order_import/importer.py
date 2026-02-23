"""
Order Import Orchestrator

Coordinates the full pipeline:
  Excel bytes → parse → clean → raw DB insert → staging DB insert

Returns an ImportResult summary with row counts and any per-row errors.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_import.cleaner import clean_lazada_row, clean_shopee_row, clean_tiktok_row
from app.services.order_import.mapper import map_to_staging
from app.services.order_import.parser import parse_lazada_file, parse_shopee_file, parse_tiktok_file


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ImportResult:
    platform: str
    seller_id: int
    filename: str
    import_batch_id: str
    total_rows: int = 0
    success_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return self.error_rows > 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CLEANERS = {
    "shopee": clean_shopee_row,
    "lazada": clean_lazada_row,
    "tiktok": clean_tiktok_row,
}

_PARSERS = {
    "shopee": parse_shopee_file,
    "lazada": parse_lazada_file,
    "tiktok": parse_tiktok_file,
}


def _safe_json(obj: Any) -> Any:
    """Convert values that are not JSON-serialisable (date, Decimal) to strings."""
    from datetime import date
    from decimal import Decimal
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    return obj


def _row_to_jsonb(row: dict[str, Any]) -> dict[str, Any]:
    """Ensure all row values are JSON-serialisable for JSONB storage."""
    return {k: _safe_json(v) for k, v in row.items()}


async def _insert_raw_row(
    session: AsyncSession,
    seller_id: int,
    platform: str,
    batch_id: str,
    filename: str,
    excel_row_number: int,
    raw_row: dict[str, Any],
) -> int:
    """Insert one raw row and return its generated id."""
    result = await session.execute(
        text(
            """
            INSERT INTO order_import.order_import_raw
              (seller_id, platform_source, import_batch_id, import_filename,
               excel_row_number, raw_row_data, imported_at)
            VALUES
              (:seller_id, :platform_source, :batch_id, :filename,
               :excel_row_number, CAST(:raw_row_data AS jsonb), NOW())
            RETURNING id
            """
        ),
        {
            "seller_id": seller_id,
            "platform_source": platform,
            "batch_id": batch_id,
            "filename": filename,
            "excel_row_number": excel_row_number,
            "raw_row_data": json.dumps(_row_to_jsonb(raw_row)),
        },
    )
    row = result.fetchone()
    return row[0]


async def _insert_staging_row(
    session: AsyncSession,
    staging: dict[str, Any],
) -> None:
    """Insert one staging row."""
    # Build column list and param dict dynamically from staging dict
    columns = list(staging.keys())
    placeholders = [f":{col}" for col in columns]

    # Serialize raw_row_data if present
    params = dict(staging)
    if "raw_row_data" in params and params["raw_row_data"] is not None:
        params["raw_row_data"] = json.dumps(_row_to_jsonb(params["raw_row_data"]))

    col_sql = ", ".join(columns)
    ph_sql = ", ".join(
        f"CAST({ph} AS jsonb)" if col == "raw_row_data" else ph
        for col, ph in zip(columns, placeholders)
    )

    await session.execute(
        text(
            f"INSERT INTO order_import.order_import_staging ({col_sql}) VALUES ({ph_sql})"
        ),
        params,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def import_excel_file(
    session: AsyncSession,
    platform: str,
    seller_id: int,
    file_bytes: bytes,
    filename: str,
) -> ImportResult:
    """
    Full import pipeline for one order export file (CSV or Excel).

    Steps:
    1. Parse file into raw row dicts
    2. Generate a batch UUID for this import
    3. For each row:
       a. Insert raw row into order_import.order_import_raw
       b. Clean the row
       c. Map to staging columns
       d. Insert into order_import.order_import_staging
    4. Commit and return ImportResult

    Args:
        session: Active async DB session (caller owns commit/rollback)
        platform: 'shopee', 'lazada', or 'tiktok'
        seller_id: FK to seller table
        file_bytes: Raw bytes of the uploaded file (CSV or Excel)
        filename: Original filename — used to detect CSV vs Excel and for audit trail

    Returns:
        ImportResult with counts and any per-row errors.
    """
    platform = platform.lower()
    parser = _PARSERS.get(platform)
    cleaner = _CLEANERS.get(platform)
    if parser is None or cleaner is None:
        raise ValueError(f"Unsupported platform: {platform!r}. Use 'shopee', 'lazada', or 'tiktok'.")

    batch_id = str(uuid.uuid4())
    result = ImportResult(
        platform=platform,
        seller_id=seller_id,
        filename=filename,
        import_batch_id=batch_id,
    )

    raw_rows = parser(file_bytes, filename)
    result.total_rows = len(raw_rows)

    for excel_row_number, raw_row in enumerate(raw_rows, start=2):  # header = row 1
        try:
            # 1. Insert raw (immutable copy)
            raw_id = await _insert_raw_row(
                session=session,
                seller_id=seller_id,
                platform=platform,
                batch_id=batch_id,
                filename=filename,
                excel_row_number=excel_row_number,
                raw_row=raw_row,
            )

            # 2. Clean
            cleaned = cleaner(raw_row)

            # 3. Map to staging schema
            staging = map_to_staging(
                platform=platform,
                cleaned_row=cleaned,
                seller_id=seller_id,
                raw_import_id=raw_id,
            )
            staging["created_at"] = datetime.utcnow()

            # 4. Insert staging
            await _insert_staging_row(session, staging)

            result.success_rows += 1

        except Exception as exc:  # noqa: BLE001
            result.error_rows += 1
            result.errors.append({
                "excel_row": excel_row_number,
                "error": str(exc),
                "raw_row_preview": {
                    k: str(v)[:100]
                    for k, v in list(raw_row.items())[:5]
                },
            })

    return result
