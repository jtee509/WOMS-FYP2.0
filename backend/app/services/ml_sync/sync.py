"""
ML Staging Sync Service

Copies cleaned staging records from woms_db.order_import.order_import_staging
into ml_woms_db.order_import.order_import_staging for ML model consumption.

Design:
- Reads from woms_db (production) — never writes there
- Upserts into ml_woms_db (ML staging) — isolated from production
- Upsert key: (platform_source, platform_order_id, platform_sku, seller_id)
- Also syncs the platform + seller records referenced by staging rows so
  FK constraints in ml_woms_db are satisfied

Usage:
    result = await sync_staging_to_ml(woms_session, ml_session, platform_source="tiktok")
"""

import json
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orders import Platform, Seller
from app.models.order_import import OrderImportStaging


@dataclass
class SyncResult:
    platform_source: Optional[str]
    seller_id: Optional[int]
    staging_synced: int = 0
    staging_skipped: int = 0
    platforms_synced: int = 0
    sellers_synced: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def _safe_value(v: Any) -> Any:
    """Convert Decimal and date objects to JSON-serialisable types."""
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


# ---------------------------------------------------------------------------
# Reference data sync (platforms + sellers)
# ---------------------------------------------------------------------------

async def _sync_platform(
    woms_session: AsyncSession,
    ml_session: AsyncSession,
    platform_id: int,
) -> None:
    """Copy a platform record from woms_db to ml_woms_db if not already there."""
    result = await ml_session.execute(
        select(Platform).where(Platform.platform_id == platform_id)
    )
    if result.scalar_one_or_none():
        return  # already exists

    src = await woms_session.execute(
        select(Platform).where(Platform.platform_id == platform_id)
    )
    src_platform = src.scalar_one_or_none()
    if not src_platform:
        return

    ml_session.add(Platform(
        platform_id=src_platform.platform_id,
        platform_name=src_platform.platform_name,
        address=src_platform.address,
        postcode=src_platform.postcode,
        is_active=src_platform.is_active,
        created_at=src_platform.created_at,
    ))
    await ml_session.flush()


async def _sync_seller(
    woms_session: AsyncSession,
    ml_session: AsyncSession,
    seller_id: int,
) -> None:
    """Copy a seller record from woms_db to ml_woms_db if not already there."""
    result = await ml_session.execute(
        select(Seller).where(Seller.seller_id == seller_id)
    )
    if result.scalar_one_or_none():
        return  # already exists

    src = await woms_session.execute(
        select(Seller).where(Seller.seller_id == seller_id)
    )
    src_seller = src.scalar_one_or_none()
    if not src_seller:
        return

    ml_session.add(Seller(
        seller_id=src_seller.seller_id,
        store_name=src_seller.store_name,
        platform_id=src_seller.platform_id,
        platform_store_id=src_seller.platform_store_id,
        company_name=src_seller.company_name,
        is_active=src_seller.is_active,
        created_at=src_seller.created_at,
    ))
    await ml_session.flush()


# ---------------------------------------------------------------------------
# Staging sync
# ---------------------------------------------------------------------------

async def sync_staging_to_ml(
    woms_session: AsyncSession,
    ml_session: AsyncSession,
    platform_source: Optional[str] = None,
    seller_id: Optional[int] = None,
) -> SyncResult:
    """
    Sync order_import_staging rows from woms_db into ml_woms_db.

    Steps:
    1. Query woms_db staging rows (filtered by platform_source / seller_id)
    2. For each row: ensure its platform and seller exist in ml_woms_db
    3. Check if the row already exists in ml_woms_db (upsert key below)
    4. Insert new rows; skip existing ones
    5. Commit ml_woms_db session

    Upsert key (identifies a unique order line item):
      (platform_source, platform_order_id, platform_sku, seller_id)

    Args:
        woms_session:    Session connected to woms_db (read-only usage)
        ml_session:      Session connected to ml_woms_db (read/write)
        platform_source: Optional filter — 'shopee', 'lazada', or 'tiktok'
        seller_id:       Optional filter — internal seller PK

    Returns:
        SyncResult with counts and any per-row errors.
    """
    result = SyncResult(platform_source=platform_source, seller_id=seller_id)

    # Build query for woms_db staging rows
    query = select(OrderImportStaging)
    if platform_source:
        query = query.where(OrderImportStaging.platform_source == platform_source.lower())
    if seller_id:
        query = query.where(OrderImportStaging.seller_id == seller_id)

    woms_rows = (await woms_session.execute(query)).scalars().all()

    # Build set of already-synced keys from ml_woms_db for fast dedup
    ml_query = select(
        OrderImportStaging.platform_source,
        OrderImportStaging.platform_order_id,
        OrderImportStaging.platform_sku,
        OrderImportStaging.seller_id,
    )
    if platform_source:
        ml_query = ml_query.where(OrderImportStaging.platform_source == platform_source.lower())
    if seller_id:
        ml_query = ml_query.where(OrderImportStaging.seller_id == seller_id)

    ml_existing = await ml_session.execute(ml_query)
    synced_keys: set[tuple] = {
        (r.platform_source, r.platform_order_id, r.platform_sku, r.seller_id)
        for r in ml_existing
    }

    # Track which platforms/sellers have already been synced in this run
    synced_platform_ids: set[int] = set()
    synced_seller_ids: set[int] = set()

    for row in woms_rows:
        key = (row.platform_source, row.platform_order_id, row.platform_sku, row.seller_id)
        if key in synced_keys:
            result.staging_skipped += 1
            continue

        try:
            # Ensure referenced platform exists in ml_woms_db
            if row.seller_id:
                # First sync the seller's platform (if any)
                seller_src = await woms_session.execute(
                    select(Seller).where(Seller.seller_id == row.seller_id)
                )
                src_seller = seller_src.scalar_one_or_none()
                if src_seller and src_seller.platform_id and src_seller.platform_id not in synced_platform_ids:
                    await _sync_platform(woms_session, ml_session, src_seller.platform_id)
                    synced_platform_ids.add(src_seller.platform_id)
                    result.platforms_synced += 1

                # Sync the seller itself
                if row.seller_id not in synced_seller_ids:
                    await _sync_seller(woms_session, ml_session, row.seller_id)
                    synced_seller_ids.add(row.seller_id)
                    result.sellers_synced += 1

            # Insert the staging row into ml_woms_db (raw_import_id set to None —
            # the raw import table is not synced to ml_woms_db)
            ml_session.add(OrderImportStaging(
                seller_id=row.seller_id,
                platform_source=row.platform_source,
                platform_order_id=row.platform_order_id,
                order_date=row.order_date,
                recipient_name=row.recipient_name,
                shipping_address=row.shipping_address,
                shipping_postcode=row.shipping_postcode,
                shipping_state=row.shipping_state,
                country=row.country,
                platform_sku=row.platform_sku,
                sku_name=row.sku_name,
                variation_name=row.variation_name,
                quantity=row.quantity,
                unit_price=row.unit_price,
                paid_amount=row.paid_amount,
                shipping_fee=row.shipping_fee,
                discount=row.discount,
                courier_type=row.courier_type,
                tracking_number=row.tracking_number,
                phone_number=row.phone_number,
                platform_order_status=row.platform_order_status,
                manual_status=row.manual_status,
                manual_driver=row.manual_driver,
                manual_date=row.manual_date,
                manual_note=row.manual_note,
                raw_row_data=row.raw_row_data,
                raw_import_id=None,  # raw table not synced to ml_woms_db
                created_at=row.created_at,
            ))

            synced_keys.add(key)
            result.staging_synced += 1

        except Exception as exc:
            result.errors.append({
                "platform_source": row.platform_source,
                "platform_order_id": row.platform_order_id,
                "error": str(exc),
            })

    await ml_session.commit()
    return result
