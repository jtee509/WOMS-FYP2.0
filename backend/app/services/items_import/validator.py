"""
Items Import — Validator
========================
Validates and FK-resolves a list of parsed row dicts.
Returns (valid_rows, errors) where valid_rows have FK names replaced
with their resolved integer IDs ready for Item() construction.
"""

import re
from dataclasses import dataclass, field
from itertools import product as _cartesian

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.items import BaseUOM, Brand, Category, Item, ItemType
from app.schemas.items import ImportRowError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRUTHY = {"true", "1", "yes", "y", "active"}
_FALSY  = {"false", "0", "no", "n", "inactive"}


def _parse_bool(value: str | None) -> bool:
    """Convert flexible boolean string to Python bool, defaulting to True."""
    if value is None:
        return True
    v = value.strip().lower()
    if v in _TRUTHY:
        return True
    if v in _FALSY:
        return False
    return True  # unknown → default active


def _has_space(value: str) -> bool:
    return bool(re.search(r"\s", value))


def _build_variations_data(raw: dict) -> tuple[dict | None, str | None]:
    """
    Build a VariationsData JSONB dict from flat variation columns.

    Returns (variations_data, error_message).
    variations_data is None when no variation columns are supplied.
    error_message is non-None when columns are partially/incorrectly filled.
    """
    name1   = raw.get("variation_name_1")
    values1 = raw.get("variation_values_1")
    name2   = raw.get("variation_name_2")
    values2 = raw.get("variation_values_2")

    # No variation columns at all → plain item
    if not name1 and not values1 and not name2 and not values2:
        return None, None

    if not name1:
        return None, "variation_name_1 is required when variation columns are provided"
    if not values1:
        return None, "variation_values_1 is required when variation_name_1 is set"

    opts1 = [v.strip() for v in values1.split(";") if v.strip()]
    if not opts1:
        return None, "variation_values_1 must contain at least one value (use ; to separate)"

    attributes = [{"name": name1.strip(), "values": opts1}]
    combo_arrays: list[list[str]] = [opts1]

    if name2 or values2:
        if not name2:
            return None, "variation_name_2 is required when variation_values_2 is provided"
        if not values2:
            return None, "variation_values_2 is required when variation_name_2 is set"
        opts2 = [v.strip() for v in values2.split(";") if v.strip()]
        if not opts2:
            return None, "variation_values_2 must contain at least one value (use ; to separate)"
        attributes.append({"name": name2.strip(), "values": opts2})
        combo_arrays.append(opts2)

    combinations = [
        {"values": list(combo), "sku": "", "image": None}
        for combo in _cartesian(*combo_arrays)
    ]

    return {"attributes": attributes, "combinations": combinations}, None


# ---------------------------------------------------------------------------
# Cache builder — one SELECT per lookup table
# ---------------------------------------------------------------------------

async def _build_caches(session: AsyncSession) -> dict:
    """
    Fetch all lookup records and return name → id caches.
    Also fetches all existing master_sku values for duplicate detection.
    """
    uom_res      = await session.execute(select(BaseUOM))
    brand_res    = await session.execute(select(Brand))
    cat_res      = await session.execute(select(Category))
    type_res     = await session.execute(select(ItemType))
    sku_res      = await session.execute(select(Item.master_sku).where(Item.deleted_at.is_(None)))

    return {
        "uom":       {r.uom_name.lower(): r.uom_id       for r in uom_res.scalars().all()},
        "brand":     {r.brand_name.lower(): r.brand_id   for r in brand_res.scalars().all()},
        "category":  {r.category_name.lower(): r.category_id for r in cat_res.scalars().all()},
        "item_type": {r.item_type_name.lower(): r.item_type_id for r in type_res.scalars().all()},
        "sku_set":   {row[0] for row in sku_res.all()},
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def validate_and_resolve(
    rows: list[dict],
    session: AsyncSession,
) -> tuple[list[dict], list[ImportRowError]]:
    """
    Validate each row and resolve FK name strings to integer IDs.

    Returns:
        valid_rows  — list of dicts ready to pass to Item(**row)
        errors      — list of ImportRowError for invalid rows
    """
    caches = await _build_caches(session)
    uom_cache      = caches["uom"]
    brand_cache    = caches["brand"]
    cat_cache      = caches["category"]
    type_cache     = caches["item_type"]
    sku_db_set     = caches["sku_set"]
    sku_file_seen: set[str] = set()

    valid_rows: list[dict] = []
    errors: list[ImportRowError] = []

    for i, raw in enumerate(rows, start=2):   # row 2 = first data row (row 1 = header)
        sku_label = raw.get("master_sku") or ""

        def _err(msg: str) -> None:
            errors.append(ImportRowError(row=i, master_sku=sku_label, error=msg))

        # ---- Required: item_name ----
        item_name = raw.get("item_name")
        if not item_name:
            _err("item_name is required")
            continue
        if len(item_name) > 500:
            _err("item_name exceeds 500 characters")
            continue

        # ---- Required: master_sku ----
        master_sku = raw.get("master_sku")
        if not master_sku:
            _err("master_sku is required")
            continue
        if len(master_sku) > 100:
            _err("master_sku exceeds 100 characters")
            continue
        if _has_space(master_sku):
            _err("master_sku must not contain spaces")
            continue
        if master_sku in sku_db_set:
            _err(f"master_sku '{master_sku}' already exists in the database")
            continue
        if master_sku in sku_file_seen:
            _err(f"master_sku '{master_sku}' appears more than once in this file")
            continue
        sku_file_seen.add(master_sku)

        # ---- Optional FK lookups ----
        uom_id = brand_id = category_id = item_type_id = None

        if raw.get("uom"):
            key = raw["uom"].lower()
            uom_id = uom_cache.get(key)
            if uom_id is None:
                _err(f"UOM '{raw['uom']}' not found. Add it in Settings first.")
                continue

        if raw.get("brand"):
            key = raw["brand"].lower()
            brand_id = brand_cache.get(key)
            if brand_id is None:
                _err(f"Brand '{raw['brand']}' not found. Add it in Settings first.")
                continue

        if raw.get("category"):
            key = raw["category"].lower()
            category_id = cat_cache.get(key)
            if category_id is None:
                _err(f"Category '{raw['category']}' not found. Add it in Settings first.")
                continue

        if raw.get("item_type"):
            key = raw["item_type"].lower()
            item_type_id = type_cache.get(key)
            if item_type_id is None:
                _err(f"Item Type '{raw['item_type']}' not found. Add it in Settings first.")
                continue

        # ---- Optional text fields ----
        sku_name    = raw.get("sku_name")
        description = raw.get("description")

        # ---- is_active ----
        is_active = _parse_bool(raw.get("is_active"))

        # ---- Variations ----
        variations_data, var_error = _build_variations_data(raw)
        if var_error:
            _err(var_error)
            continue
        has_variation = variations_data is not None

        valid_rows.append({
            "item_name":       item_name,
            "master_sku":      master_sku,
            "sku_name":        sku_name,
            "description":     description,
            "uom_id":          uom_id,
            "brand_id":        brand_id,
            "category_id":     category_id,
            "item_type_id":    item_type_id,
            "is_active":       is_active,
            "has_variation":   has_variation,
            "variations_data": variations_data,
        })

    return valid_rows, errors
