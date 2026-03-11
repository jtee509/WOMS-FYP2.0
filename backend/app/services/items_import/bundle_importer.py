"""
Bundle Import — Orchestrator
==============================
Parses a CSV/Excel file where each row represents one component of a bundle.
Rows sharing the same bundle_sku are grouped into a single bundle.

Expected columns (case-insensitive, aliases supported):
  Required: bundle_name, bundle_sku, component_sku, component_qty
  Optional: sku_name, description, category, brand, uom, is_active

Multiple rows with the same bundle_sku contribute components. Metadata
(name, description, category, etc.) is taken from the FIRST row per group.

Example CSV:
  bundle_name,bundle_sku,component_sku,component_qty,category,brand,uom,is_active
  Summer Pack,BUNDLE-001,TSHIRT-001,2,Apparel,My Brand,Each,true
  Summer Pack,BUNDLE-001,SHORTS-001,1,,,,
  Winter Pack,BUNDLE-002,JACKET-001,1,Apparel,My Brand,Each,true
  Winter Pack,BUNDLE-002,SCARF-001,3,,,,
"""

import io
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.items import BaseUOM, Brand, Category, Item, ItemType
from app.models.orders import ListingComponent, Platform, PlatformSKU, Seller
from app.schemas.items import ImportResult, ImportRowError


# ---------------------------------------------------------------------------
# Column alias map
# ---------------------------------------------------------------------------

_ALIASES: dict[str, str] = {
    # bundle_name
    "bundle_name": "bundle_name",
    "bundle name": "bundle_name",
    "item_name": "bundle_name",
    "item name": "bundle_name",
    "name": "bundle_name",
    # bundle_sku
    "bundle_sku": "bundle_sku",
    "bundle sku": "bundle_sku",
    "master_sku": "bundle_sku",
    "master sku": "bundle_sku",
    "sku": "bundle_sku",
    # component_sku
    "component_sku": "component_sku",
    "component sku": "component_sku",
    "component master sku": "component_sku",
    "comp_sku": "component_sku",
    # component_qty
    "component_qty": "component_qty",
    "component qty": "component_qty",
    "qty": "component_qty",
    "quantity": "component_qty",
    # sku_name
    "sku_name": "sku_name",
    "sku name": "sku_name",
    "display name": "sku_name",
    # description
    "description": "description",
    "desc": "description",
    # category
    "category": "category",
    "category name": "category",
    # brand
    "brand": "brand",
    "brand name": "brand",
    # uom
    "uom": "uom",
    "base uom": "uom",
    "unit": "uom",
    # is_active
    "is_active": "is_active",
    "active": "is_active",
    "status": "is_active",
}

CANONICAL_COLUMNS = {
    "bundle_name", "bundle_sku", "component_sku", "component_qty",
    "sku_name", "description", "category", "brand", "uom", "is_active",
}

_TRUTHY = {"true", "1", "yes", "y", "active"}


# ---------------------------------------------------------------------------
# File reading / parsing helpers
# ---------------------------------------------------------------------------

def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(
                    io.BytesIO(file_bytes), dtype=str,
                    keep_default_na=False, encoding=enc,
                )
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file. Please save it as UTF-8.")
    return pd.read_excel(
        io.BytesIO(file_bytes), sheet_name=0, header=0, dtype=str,
    )


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "n/a", "na", ""):
        return None
    return s


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in _TRUTHY or value.strip().lower() not in (
        "false", "0", "no", "n", "inactive"
    )


def _parse_file(file_bytes: bytes, filename: str) -> list[dict]:
    df = _read_file(file_bytes, filename)
    # Normalise column names
    rename_map: dict[str, str] = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _ALIASES:
            rename_map[col] = _ALIASES[key]
    df = df.rename(columns=rename_map)
    keep = [c for c in df.columns if c in CANONICAL_COLUMNS]
    df = df[keep]
    if df.empty:
        raise ValueError("The file contains no data rows.")
    rows: list[dict] = []
    for _, row in df.iterrows():
        cleaned = {col: _clean(row[col]) for col in keep}
        rows.append(cleaned)
    return rows


# ---------------------------------------------------------------------------
# Group rows by bundle_sku
# ---------------------------------------------------------------------------

def _group_rows(rows: list[dict]) -> list[tuple[dict, list[dict]]]:
    """
    Group rows by bundle_sku. Returns a list of (metadata_row, [component_rows]).
    Metadata is taken from the first occurrence of each bundle_sku.
    """
    groups: dict[str, tuple[dict, list[dict]]] = {}
    for row in rows:
        bsku = row.get("bundle_sku")
        if not bsku:
            continue
        if bsku not in groups:
            groups[bsku] = (row, [row])
        else:
            groups[bsku][1].append(row)
    return list(groups.values())


# ---------------------------------------------------------------------------
# Main import function
# ---------------------------------------------------------------------------

async def import_bundles(
    session: AsyncSession,
    file_bytes: bytes,
    filename: str,
) -> ImportResult:
    """
    Parse, validate, and bulk-create bundles from an uploaded CSV or Excel file.
    """
    rows = _parse_file(file_bytes, filename)
    if not rows:
        raise ValueError("The file contains no data rows.")

    # Build FK caches
    uom_res = await session.execute(select(BaseUOM))
    brand_res = await session.execute(select(Brand))
    cat_res = await session.execute(select(Category))

    uom_cache = {r.uom_name.lower(): r.uom_id for r in uom_res.scalars().all()}
    brand_cache = {r.brand_name.lower(): r.brand_id for r in brand_res.scalars().all()}
    cat_cache = {r.category_name.lower(): r.category_id for r in cat_res.scalars().all()}

    # Resolve "Bundle" item type
    bundle_type_id = (await session.execute(
        select(ItemType.item_type_id).where(
            ItemType.item_type_name == "Bundle",
            ItemType.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if bundle_type_id is None:
        raise ValueError("Item type 'Bundle' not found in database. Run seed data first.")

    # Existing SKUs for duplicate detection
    sku_res = await session.execute(
        select(Item.master_sku).where(Item.deleted_at.is_(None))
    )
    existing_skus = {row[0] for row in sku_res.all()}

    # Build item SKU → item_id lookup for component resolution
    items_res = await session.execute(
        select(Item.item_id, Item.master_sku).where(Item.deleted_at.is_(None))
    )
    sku_to_id = {row.master_sku: row.item_id for row in items_res.all()}

    # Resolve first active platform and seller for listing creation
    platform_id = (await session.execute(
        select(Platform.platform_id)
        .where(Platform.is_active.is_(True))
        .order_by(Platform.platform_id)
        .limit(1)
    )).scalar_one_or_none()

    seller_id = (await session.execute(
        select(Seller.seller_id)
        .where(Seller.is_active.is_(True))
        .order_by(Seller.seller_id)
        .limit(1)
    )).scalar_one_or_none()

    if platform_id is None or seller_id is None:
        raise ValueError(
            "Cannot import bundles: no active platform or seller exists. "
            "Create at least one platform and one seller first."
        )

    # Group rows by bundle_sku
    groups = _group_rows(rows)
    if not groups:
        raise ValueError("No valid bundle_sku values found in the file.")

    errors: list[ImportRowError] = []
    success_count = 0
    bundle_skus_in_file: set[str] = set()

    for meta_row, component_rows in groups:
        bundle_sku = meta_row.get("bundle_sku", "")
        bundle_name = meta_row.get("bundle_name")

        # Find the row number of the first occurrence for error reporting
        first_row_num = rows.index(meta_row) + 2  # +2 for header + 0-based

        def _err(msg: str) -> None:
            errors.append(ImportRowError(row=first_row_num, master_sku=bundle_sku, error=msg))

        # Validate required fields
        if not bundle_name:
            _err("bundle_name is required")
            continue
        if len(bundle_name) > 500:
            _err("bundle_name exceeds 500 characters")
            continue
        if not bundle_sku:
            _err("bundle_sku is required")
            continue
        if len(bundle_sku) > 100:
            _err("bundle_sku exceeds 100 characters")
            continue
        if " " in bundle_sku:
            _err("bundle_sku must not contain spaces")
            continue
        if bundle_sku in existing_skus:
            _err(f"bundle_sku '{bundle_sku}' already exists in the database")
            continue
        if bundle_sku in bundle_skus_in_file:
            _err(f"bundle_sku '{bundle_sku}' appears more than once as a group (duplicate)")
            continue
        bundle_skus_in_file.add(bundle_sku)

        # Resolve optional FKs from first row
        uom_id = brand_id = category_id = None

        if meta_row.get("uom"):
            uom_id = uom_cache.get(meta_row["uom"].lower())
            if uom_id is None:
                _err(f"UOM '{meta_row['uom']}' not found. Add it in Settings first.")
                continue

        if meta_row.get("brand"):
            brand_id = brand_cache.get(meta_row["brand"].lower())
            if brand_id is None:
                _err(f"Brand '{meta_row['brand']}' not found. Add it in Settings first.")
                continue

        if meta_row.get("category"):
            category_id = cat_cache.get(meta_row["category"].lower())
            if category_id is None:
                _err(f"Category '{meta_row['category']}' not found. Add it in Settings first.")
                continue

        is_active = _parse_bool(meta_row.get("is_active"))
        sku_name = meta_row.get("sku_name")
        description = meta_row.get("description")

        # Validate and resolve components
        components: list[tuple[int, int]] = []  # (item_id, quantity)
        comp_error = False

        for comp_row in component_rows:
            comp_sku = comp_row.get("component_sku")
            comp_qty_str = comp_row.get("component_qty")
            row_num = rows.index(comp_row) + 2

            if not comp_sku:
                errors.append(ImportRowError(
                    row=row_num, master_sku=bundle_sku,
                    error="component_sku is required for each row",
                ))
                comp_error = True
                continue

            comp_item_id = sku_to_id.get(comp_sku)
            if comp_item_id is None:
                errors.append(ImportRowError(
                    row=row_num, master_sku=bundle_sku,
                    error=f"Component SKU '{comp_sku}' not found in items",
                ))
                comp_error = True
                continue

            comp_qty = 1
            if comp_qty_str:
                try:
                    comp_qty = int(float(comp_qty_str))
                    if comp_qty < 1:
                        raise ValueError()
                except (ValueError, TypeError):
                    errors.append(ImportRowError(
                        row=row_num, master_sku=bundle_sku,
                        error=f"component_qty must be a positive integer, got '{comp_qty_str}'",
                    ))
                    comp_error = True
                    continue

            components.append((comp_item_id, comp_qty))

        if comp_error or not components:
            if not comp_error:
                _err("No valid components found for this bundle")
            continue

        # Validate bundle composition
        distinct_ids = {c[0] for c in components}
        max_qty = max(c[1] for c in components)
        if len(distinct_ids) <= 1 and max_qty <= 1:
            _err("A bundle must have >1 distinct components or a single component with qty > 1")
            continue

        # Create the bundle item
        bundle_item = Item(
            item_name=bundle_name,
            master_sku=bundle_sku,
            sku_name=sku_name,
            description=description,
            uom_id=uom_id,
            brand_id=brand_id,
            item_type_id=bundle_type_id,
            category_id=category_id,
            is_active=is_active,
        )
        session.add(bundle_item)
        await session.flush()

        # Add to existing SKUs to prevent duplicates within file
        existing_skus.add(bundle_sku)

        # Create PlatformSKU listing
        listing = PlatformSKU(
            platform_id=platform_id,
            seller_id=seller_id,
            platform_sku=bundle_sku,
            platform_seller_sku_name=bundle_name,
            is_active=is_active,
        )
        session.add(listing)
        await session.flush()

        # Create listing components
        for comp_item_id, comp_qty in components:
            session.add(ListingComponent(
                listing_id=listing.listing_id,
                item_id=comp_item_id,
                quantity=comp_qty,
            ))
        await session.flush()

        success_count += 1

    return ImportResult(
        total_rows=len(groups),
        success_rows=success_count,
        error_rows=len(groups) - success_count,
        errors=errors,
    )
