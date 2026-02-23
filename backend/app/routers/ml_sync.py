"""
ML Sync Router

Endpoint to push order_import_staging records from woms_db into ml_woms_db
for ML model training and inference workloads.

Endpoint:
  POST /api/v1/ml/sync
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.ml_database import get_ml_session
from app.services.ml_sync import sync_staging_to_ml, SyncResult

router = APIRouter()


class SyncRequest(BaseModel):
    platform_source: Optional[str] = None
    seller_id: Optional[int] = None


@router.post(
    "/sync",
    summary="Sync staging data to ML database",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["ML Staging"],
)
async def sync_to_ml(
    body: SyncRequest,
    woms_session: AsyncSession = Depends(get_session),
    ml_session: AsyncSession = Depends(get_ml_session),
) -> dict:
    """
    Copy order_import_staging rows from **woms_db** into **ml_woms_db**.

    Optionally filter by `platform_source` ('shopee', 'lazada', 'tiktok')
    and/or `seller_id`.

    The sync is **idempotent** — rows already present in ml_woms_db are skipped.
    Referenced platform and seller records are copied automatically to satisfy
    FK constraints in ml_woms_db.

    **Prerequisites:**
    - `ml_woms_db` must exist and have its schema initialized (`init_ml_db()`).
    - At least one successful order import must have been run in woms_db.
    """
    platform = body.platform_source.lower() if body.platform_source else None
    if platform and platform not in {"shopee", "lazada", "tiktok"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported platform_source: '{platform}'. Use 'shopee', 'lazada', or 'tiktok'.",
        )

    try:
        result: SyncResult = await sync_staging_to_ml(
            woms_session=woms_session,
            ml_session=ml_session,
            platform_source=platform,
            seller_id=body.seller_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML sync failed: {exc}",
        ) from exc

    return {
        "platform_source": result.platform_source,
        "seller_id": result.seller_id,
        "staging_synced": result.staging_synced,
        "staging_skipped": result.staging_skipped,
        "platforms_synced": result.platforms_synced,
        "sellers_synced": result.sellers_synced,
        "has_errors": result.has_errors,
        "errors": result.errors,
    }


@router.post(
    "/init-schema",
    summary="Initialize ml_woms_db schema",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["ML Staging"],
)
async def init_ml_schema() -> dict:
    """
    Create all tables in ml_woms_db (one-time setup).

    Equivalent to running `init_ml_db()` programmatically.
    Safe to re-run — uses CREATE IF NOT EXISTS throughout.
    """
    from app.ml_database import init_ml_db
    try:
        await init_ml_db()
        return {"status": "ok", "message": "ml_woms_db schema initialized"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML schema init failed: {exc}",
        ) from exc
