"""
Reference Data Router

Admin endpoints for loading reference/master data into woms_db.
These are one-time setup operations run before order imports.

Endpoints:
  POST /api/v1/reference/load-platforms — load platform records
  POST /api/v1/reference/load-sellers   — load seller records
  POST /api/v1/reference/load-items     — load item master data
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_session
from app.services.reference_loader import load_platforms, load_sellers, load_item_master

router = APIRouter()

_MAX_FILE_MB = 20
_MAX_FILE_BYTES = _MAX_FILE_MB * 1024 * 1024
_ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".csv")


def _validate_upload(file: UploadFile) -> str:
    filename = file.filename or "unknown"
    if not filename.lower().endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File must be .xlsx, .xls, or .csv. Got: {filename}",
        )
    return filename


@router.post(
    "/load-platforms",
    summary="Load platform reference data",
    response_model=dict,
    tags=["Reference Data"],
)
async def upload_platforms(
    file: UploadFile = File(..., description="Platform reference file (.xlsx or .csv)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upsert platform records from an Excel/CSV file.

    Expected columns: Platform_ID, Platform_Name, Address, Postcode

    **Upsert key:** platform_name (unique)

    Safe to re-run — existing records are updated in-place.
    """
    filename = _validate_upload(file)
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_FILE_MB} MB limit")

    try:
        return await load_platforms(session, file_bytes, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Platform load failed: {exc}") from exc


@router.post(
    "/load-sellers",
    summary="Load seller reference data",
    response_model=dict,
    tags=["Reference Data"],
)
async def upload_sellers(
    sellers_file: UploadFile = File(..., description="Seller reference file (.xlsx or .csv)"),
    platforms_file: Optional[UploadFile] = File(
        default=None,
        description="Optional platform file for resolving Platform_ID codes to platform names",
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upsert seller records from an Excel/CSV file.

    Expected columns: Seller_ID, Seller Name, Company Name, Platform_ID

    **Platform resolution:** If platforms_file is provided, Platform_ID codes
    (e.g. MYONL1) are resolved to platform names, then matched against the
    platform table in the DB. Load platforms first for best results.

    **Upsert key:** Seller_ID (stored as platform_store_id)

    Safe to re-run — existing records are updated in-place.
    """
    sellers_filename = _validate_upload(sellers_file)
    sellers_bytes = await sellers_file.read()
    if not sellers_bytes:
        raise HTTPException(status_code=422, detail="Sellers file is empty")

    platforms_bytes: bytes | None = None
    platforms_filename: str | None = None
    if platforms_file and platforms_file.filename:
        platforms_filename = _validate_upload(platforms_file)
        platforms_bytes = await platforms_file.read()

    try:
        return await load_sellers(
            session,
            sellers_bytes,
            sellers_filename,
            platforms_bytes,
            platforms_filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Seller load failed: {exc}") from exc


@router.post(
    "/load-items",
    summary="Load item master data",
    response_model=dict,
    tags=["Reference Data"],
)
async def upload_items(
    file: UploadFile = File(..., description="Item Master Excel file (.xlsx)"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Upsert items from the Item Master Excel into the **items** table.

    Expected format: Multi-sheet Excel with headers in row 4.
    Expected columns per sheet:
    - No., Product Name, SKU Name, Internal CODE (Main code), BaseUOM

    Platform SKU columns (Lazada/Shopee/TikTok SKU CODE) in the file are
    intentionally skipped — platform SKU → Internal SKU mapping must be
    done manually per seller after reviewing order staging data.

    **Upsert key:** items.master_sku (Internal CODE, unique)

    Safe to re-run — existing records are updated in-place.
    """
    filename = _validate_upload(file)
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {_MAX_FILE_MB} MB limit")

    try:
        return await load_item_master(session, file_bytes, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Item master load failed: {exc}") from exc
