"""
Items Import — Parser
=====================
Reads CSV or Excel files and returns a normalised list of row dicts.
Column name aliases are mapped to canonical field names so downstream
code always works with the same keys regardless of what headers the
user chose.
"""

import io
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Column alias map — maps common user-supplied headers → canonical name
# ---------------------------------------------------------------------------

_ALIASES: dict[str, str] = {
    # item_name
    "item_name": "item_name",
    "product name": "item_name",
    "name": "item_name",
    # master_sku
    "master_sku": "master_sku",
    "internal code (main code)": "master_sku",
    "internal code": "master_sku",
    "sku": "master_sku",
    "sku code": "master_sku",
    # sku_name
    "sku_name": "sku_name",
    "sku name": "sku_name",
    "variant name": "sku_name",
    # description
    "description": "description",
    "desc": "description",
    # uom
    "uom": "uom",
    "base uom": "uom",
    "baseuom": "uom",
    "unit": "uom",
    # brand
    "brand": "brand",
    "brand name": "brand",
    # category
    "category": "category",
    "category name": "category",
    # item_type
    "item_type": "item_type",
    "item type": "item_type",
    "type": "item_type",
    # is_active
    "is_active": "is_active",
    "is active": "is_active",
    "active": "is_active",
    "status": "is_active",
    # variation columns
    "variation_name_1": "variation_name_1",
    "variation name 1": "variation_name_1",
    "variation 1 name": "variation_name_1",
    "variation_values_1": "variation_values_1",
    "variation values 1": "variation_values_1",
    "variation 1 values": "variation_values_1",
    "variation_name_2": "variation_name_2",
    "variation name 2": "variation_name_2",
    "variation 2 name": "variation_name_2",
    "variation_values_2": "variation_values_2",
    "variation values 2": "variation_values_2",
    "variation 2 values": "variation_values_2",
}


# ---------------------------------------------------------------------------
# Helpers (mirrors loader.py patterns)
# ---------------------------------------------------------------------------

def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read CSV or Excel file into a DataFrame."""
    if filename.lower().endswith(".csv"):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(
                    io.BytesIO(file_bytes),
                    dtype=str,
                    keep_default_na=False,
                    encoding=enc,
                )
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file. Please save it as UTF-8.")
    # Excel — read first sheet
    return pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name=0,
        header=0,
        dtype=str,
    )


def _clean(value: Any) -> str | None:
    """Strip whitespace and return None for blank / N/A values."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "n/a", "na", ""):
        return None
    return s


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename DataFrame columns to canonical names using the alias map."""
    rename_map: dict[str, str] = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _ALIASES:
            rename_map[col] = _ALIASES[key]
    return df.rename(columns=rename_map)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

CANONICAL_COLUMNS = {
    "item_name", "master_sku", "sku_name", "description",
    "uom", "brand", "category", "item_type", "is_active",
    "variation_name_1", "variation_values_1",
    "variation_name_2", "variation_values_2",
}


def parse_file(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Parse a CSV or Excel file into a list of normalised row dicts.

    Each dict contains only the canonical field names that are present
    in the file. Unknown columns are silently dropped.

    Raises ValueError if the file cannot be parsed or has no rows.
    """
    df = _read_file(file_bytes, filename)
    df = _normalise_columns(df)

    # Keep only recognised columns
    keep = [c for c in df.columns if c in CANONICAL_COLUMNS]
    df = df[keep]

    if df.empty:
        raise ValueError("The file contains no data rows.")

    rows: list[dict] = []
    for _, row in df.iterrows():
        cleaned = {col: _clean(row[col]) for col in keep}
        rows.append(cleaned)

    return rows
