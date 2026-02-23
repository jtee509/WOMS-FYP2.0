"""
Order Import Router

Provides a file-upload endpoint to ingest Shopee and Lazada order Excel exports
into the order_import schema (raw + staging tables).

Endpoint:
  POST /api/v1/orders/import
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.order_import import ImportResult, import_excel_file

router = APIRouter()

_SUPPORTED_PLATFORMS = {"shopee", "lazada", "tiktok"}
_MAX_FILE_SIZE_MB = 10
_MAX_FILE_BYTES = _MAX_FILE_SIZE_MB * 1024 * 1024


@router.post(
    "/import",
    summary="Import Shopee, Lazada, or TikTok order file (CSV or Excel)",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["Order Import"],
)
async def import_orders(
    platform: str = Form(
        ...,
        description="E-commerce platform: 'shopee', 'lazada', or 'tiktok'",
        example="shopee",
    ),
    seller_id: int = Form(
        ...,
        description="Seller ID (FK to seller table)",
        example=1,
    ),
    file: UploadFile = File(
        ...,
        description="Order export file — CSV (.csv) or Excel (.xlsx/.xls)",
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upload a Shopee, Lazada, or TikTok order export (CSV or Excel) and import it into woms_db.

    **Processing pipeline:**
    1. Parse Excel into raw row dicts (handles platform-specific quirks)
    2. Insert each row verbatim into `order_import.order_import_raw` (JSONB)
    3. Clean each row (encoding, date normalisation, type coercions)
    4. Map cleaned fields to the unified staging schema
    5. Insert into `order_import.order_import_staging`

    **Returns** an import summary with row counts and any per-row errors.
    """
    # Validate platform
    platform_lower = platform.strip().lower()
    if platform_lower not in _SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported platform '{platform}'. Must be one of: {sorted(_SUPPORTED_PLATFORMS)}",
        )

    # Validate file type
    filename = file.filename or "unknown.xlsx"
    if not filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be a CSV or Excel file (.csv, .xlsx, or .xls)",
        )

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {_MAX_FILE_SIZE_MB} MB size limit",
        )

    # Run import pipeline
    try:
        result: ImportResult = await import_excel_file(
            session=session,
            platform=platform_lower,
            seller_id=seller_id,
            file_bytes=file_bytes,
            filename=filename,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {exc}",
        ) from exc

    return {
        "platform": result.platform,
        "seller_id": result.seller_id,
        "filename": result.filename,
        "import_batch_id": result.import_batch_id,
        "total_rows": result.total_rows,
        "success_rows": result.success_rows,
        "skipped_rows": result.skipped_rows,
        "error_rows": result.error_rows,
        "errors": result.errors,
    }
