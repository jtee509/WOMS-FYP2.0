"""
Reference Data Loader

Upserts platform, seller, and item master data from Excel/CSV files into
the main woms_db database. These are admin-only operations run once per
environment to seed the reference tables before order imports.

Three entry points:
  load_platforms()   — test platform.xlsx → platform table
  load_sellers()     — test_sellers.xlsx  → seller table
  load_item_master() — Item Master.xlsx   → items table only (platform SKU mapping is manual)
"""

import io
from typing import Any, Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.orders import Platform, Seller
from app.models.items import Item, BaseUOM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_file(file_bytes: bytes, filename: str, **kwargs) -> pd.DataFrame:
    """Read CSV or Excel into a DataFrame based on file extension."""
    if filename.lower().endswith(".csv"):
        return pd.read_csv(
            io.BytesIO(file_bytes),
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
            **kwargs,
        )
    return pd.read_excel(io.BytesIO(file_bytes), dtype=str, **kwargs)


def _clean(value: Any) -> str | None:
    """Strip and return None for blank / N/A values."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "n/a", "na", ""):
        return None
    return s


# ---------------------------------------------------------------------------
# Platform loader
# ---------------------------------------------------------------------------

async def load_platforms(
    session: AsyncSession,
    file_bytes: bytes,
    filename: str,
) -> dict:
    """
    Upsert platform records from file.

    Expected columns: Platform_ID, Platform_Name, Address, Postcode
    Upsert key: platform_name (unique in DB)

    Returns: {"platforms_upserted": N, "errors": [...]}
    """
    df = _read_file(file_bytes, filename, header=0)
    upserted = 0
    errors: list[dict] = []

    for _, row in df.iterrows():
        platform_name = _clean(row.get("Platform_Name"))
        if not platform_name:
            continue

        address = _clean(row.get("Address"))
        postcode = _clean(row.get("Postcode"))

        try:
            result = await session.execute(
                select(Platform).where(Platform.platform_name == platform_name)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.address = address
                existing.postcode = postcode
                session.add(existing)
            else:
                session.add(Platform(
                    platform_name=platform_name,
                    address=address,
                    postcode=postcode,
                ))
            upserted += 1

        except Exception as exc:
            errors.append({"platform_name": platform_name, "error": str(exc)})

    await session.commit()
    return {"platforms_upserted": upserted, "errors": errors}


# ---------------------------------------------------------------------------
# Seller loader
# ---------------------------------------------------------------------------

async def load_sellers(
    session: AsyncSession,
    sellers_bytes: bytes,
    sellers_filename: str,
    platforms_bytes: Optional[bytes] = None,
    platforms_filename: Optional[str] = None,
) -> dict:
    """
    Upsert seller records from file.

    Expected columns: Seller_ID, Seller Name, Company Name, Platform_ID

    Platform resolution: Platform codes (e.g. MYONL1) are resolved to
    platform_name via the optional platforms_file, then to platform_id
    via a DB lookup. If platforms_file is omitted, platform_id is NULL.

    Upsert key: platform_store_id (the Seller_ID from the file)

    Returns: {"sellers_upserted": N, "unresolved_platform_ids": [...], "errors": [...]}
    """
    # Build external code → platform_name mapping from the platforms file
    code_to_name: dict[str, str] = {}
    if platforms_bytes and platforms_filename:
        pf_df = _read_file(platforms_bytes, platforms_filename, header=0)
        for _, row in pf_df.iterrows():
            code = _clean(row.get("Platform_ID"))
            name = _clean(row.get("Platform_Name"))
            if code and name:
                code_to_name[code.upper()] = name

    # Build platform_name → platform_id mapping from DB
    db_result = await session.execute(select(Platform))
    name_to_id: dict[str, int] = {
        p.platform_name.lower(): p.platform_id
        for p in db_result.scalars().all()
        if p.platform_name and p.platform_id
    }

    sellers_df = _read_file(sellers_bytes, sellers_filename, header=0)
    upserted = 0
    unresolved: list[str] = []
    errors: list[dict] = []

    for _, row in sellers_df.iterrows():
        seller_code = _clean(row.get("Seller_ID"))
        store_name = _clean(row.get("Seller Name"))
        company_name = _clean(row.get("Company Name"))
        platform_code = _clean(row.get("Platform_ID"))

        if not store_name:
            continue

        # Resolve platform_id via code → name → DB id chain
        platform_id = None
        if platform_code:
            platform_name = code_to_name.get(platform_code.upper())
            if platform_name:
                platform_id = name_to_id.get(platform_name.lower())
            if platform_id is None and platform_code not in unresolved:
                unresolved.append(platform_code)

        try:
            # Look up by platform_store_id if available, else by store_name
            if seller_code:
                result = await session.execute(
                    select(Seller).where(Seller.platform_store_id == seller_code)
                )
            else:
                result = await session.execute(
                    select(Seller).where(Seller.store_name == store_name)
                )
            existing = result.scalar_one_or_none()

            if existing:
                existing.store_name = store_name
                existing.company_name = company_name
                existing.platform_id = platform_id
                if seller_code:
                    existing.platform_store_id = seller_code
                session.add(existing)
            else:
                session.add(Seller(
                    store_name=store_name,
                    company_name=company_name,
                    platform_id=platform_id,
                    platform_store_id=seller_code,
                ))
            upserted += 1

        except Exception as exc:
            errors.append({"seller_code": seller_code, "store_name": store_name, "error": str(exc)})

    await session.commit()
    return {
        "sellers_upserted": upserted,
        "unresolved_platform_ids": unresolved,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Item master loader
# ---------------------------------------------------------------------------

async def load_item_master(
    session: AsyncSession,
    file_bytes: bytes,
    filename: str,
) -> dict:
    """
    Upsert items from the Item Master Excel into the items table only.

    Expected format: Multi-sheet Excel with headers in row 4 (header=3, 0-indexed).
    Expected columns per sheet:
      No., Product Name, SKU Name, Internal CODE (Main code), BaseUOM

    Platform SKU columns (Lazada/Shopee/TikTok SKU CODE) are present in the
    file but are NOT loaded here. Platform SKU → Internal SKU mapping is a
    separate manual step done per-seller after order data is reviewed.

    Upsert key: items.master_sku = Internal CODE (unique)

    Returns: {"items_upserted": N, "sheets_processed": [...], "errors": [...]}
    """
    # Cache UOM records (name → uom_id) to avoid repeated DB lookups
    uom_cache: dict[str, int] = {}

    async def _get_or_create_uom(uom_name: str) -> int | None:
        key = uom_name.lower()
        if key in uom_cache:
            return uom_cache[key]
        result = await session.execute(
            select(BaseUOM).where(BaseUOM.uom_name == uom_name)
        )
        uom = result.scalar_one_or_none()
        if not uom:
            uom = BaseUOM(uom_name=uom_name)
            session.add(uom)
            await session.flush()
        uom_cache[key] = uom.uom_id
        return uom.uom_id

    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    items_upserted = 0
    sheets_processed: list[dict] = []
    errors: list[dict] = []

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet_name, header=3, dtype=str)

        # Drop rows without a valid Internal CODE (example rows, blanks, section headers)
        code_col = "Internal CODE (Main code)"
        if code_col not in df.columns:
            sheets_processed.append({"sheet": sheet_name, "rows_processed": 0, "note": "column not found"})
            continue

        df = df[df[code_col].notna()]
        df = df[df[code_col].str.strip().ne("")]

        sheet_count = 0

        for _, row in df.iterrows():
            master_sku = _clean(row.get(code_col))
            if not master_sku:
                continue

            item_name = _clean(row.get("Product Name")) or master_sku
            sku_name = _clean(row.get("SKU Name"))
            uom_name = _clean(row.get("BaseUOM"))

            product_number: int | None = None
            raw_no = _clean(row.get("No."))
            if raw_no:
                try:
                    product_number = int(float(raw_no))
                except (ValueError, OverflowError):
                    pass

            uom_id = await _get_or_create_uom(uom_name) if uom_name else None

            try:
                result = await session.execute(
                    select(Item).where(Item.master_sku == master_sku)
                )
                item = result.scalar_one_or_none()

                if item:
                    item.item_name = item_name
                    item.sku_name = sku_name
                    item.uom_id = uom_id
                    item.product_number = product_number
                    session.add(item)
                else:
                    new_item = Item(
                        master_sku=master_sku,
                        item_name=item_name,
                        sku_name=sku_name,
                        uom_id=uom_id,
                        product_number=product_number,
                    )
                    session.add(new_item)
                    # flush so the same master_sku on a later sheet is found by select()
                    await session.flush()

                items_upserted += 1
                sheet_count += 1

            except Exception as exc:
                errors.append({"master_sku": master_sku, "sheet": sheet_name, "error": str(exc)})

        sheets_processed.append({"sheet": sheet_name, "rows_processed": sheet_count})

    await session.commit()
    return {
        "items_upserted": items_upserted,
        "sheets_processed": sheets_processed,
        "errors": errors,
    }
