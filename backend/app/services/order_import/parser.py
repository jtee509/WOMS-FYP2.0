"""
Order Import Parser

Reads Shopee, Lazada, and TikTok order export files (CSV or Excel) into
lists of raw row dicts. Handles platform-specific column quirks before
any cleaning or mapping.
"""

import io
from typing import Any

import pandas as pd


def _read_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read CSV or Excel into a DataFrame based on file extension.

    CSV: tries utf-8-sig first (handles BOM), then cp1252 (Windows default),
    then latin-1 (byte-safe fallback that never fails).
    """
    if filename.lower().endswith(".csv"):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(
                    io.BytesIO(file_bytes),
                    dtype=str,
                    keep_default_na=False,
                    encoding=enc,
                )
            except (UnicodeDecodeError, ValueError):
                continue
        # Should never reach here with latin-1, but keep as safety net
        raise ValueError(f"Could not decode CSV file '{filename}' with any known encoding")
    return pd.read_excel(io.BytesIO(file_bytes), header=0, dtype=str)


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to a list of dicts, replacing NaN and empty strings with None."""
    return [
        {
            k: (
                None
                if (isinstance(v, str) and not v)
                or (not isinstance(v, str) and pd.isna(v))
                else v
            )
            for k, v in row.items()
        }
        for row in df.to_dict(orient="records")
    ]


def parse_shopee_file(file_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    """
    Parse a Shopee order export file (CSV or Excel).

    Quirks handled:
    - Column 'Tracking Number*' has a trailing asterisk — stripped to 'Tracking Number'
    - Shopee CSV inserts a headerless phone-number column after 'Receiver Name',
      shifting Province/City/Country/Zip Code labels one position forward. Fixed
      by renaming the unnamed column to 'Phone Number' and correcting the shifted
      location/geo column headers so the field map resolves correctly.
    - NaN values and empty strings replaced with None
    """
    df = _read_dataframe(file_bytes, filename)
    # Strip trailing asterisks and whitespace from all column names
    df.columns = [col.rstrip("* ").strip() for col in df.columns]

    # Fix column misalignment: an unnamed column (the phone number) sits between
    # "Receiver Name" and "Phone Number", pushing geo columns right by 1.
    # All renames are done by exact position index to avoid creating duplicates.
    cols = list(df.columns)
    if "Receiver Name" in cols:
        recv_idx = cols.index("Receiver Name")
        phone_unnamed_idx = recv_idx + 1
        if (
            phone_unnamed_idx < len(cols)
            and cols[phone_unnamed_idx].startswith("Unnamed:")
            and phone_unnamed_idx + 1 < len(cols)
            and cols[phone_unnamed_idx + 1] == "Phone Number"
        ):
            # Rename the unnamed col to "Phone Number" (it holds the actual phone value)
            cols[phone_unnamed_idx] = "Phone Number"
            # Old "Phone Number" col (phone_unnamed_idx+1) holds delivery address data
            cols[phone_unnamed_idx + 1] = "Delivery Address"
            # Old "Delivery Address" col (phone_unnamed_idx+2) is now redundant/empty
            if (
                phone_unnamed_idx + 2 < len(cols)
                and cols[phone_unnamed_idx + 2] == "Delivery Address"
            ):
                cols[phone_unnamed_idx + 2] = "_delivery_addr_orig"
            # Fix the geo columns that are also shifted: Province/City/Country/Zip Code
            if "Province" in cols:
                prov_idx = cols.index("Province")
                # Rename by index to avoid duplicate column names
                if prov_idx + 1 < len(cols) and cols[prov_idx + 1] == "City":
                    cols[prov_idx + 1] = "Province"   # City slot → Province name data
                if prov_idx + 2 < len(cols) and cols[prov_idx + 2] == "Country":
                    cols[prov_idx + 2] = "Zip Code"   # Country slot → zip code data
                if prov_idx + 3 < len(cols) and cols[prov_idx + 3] == "Zip Code":
                    cols[prov_idx + 3] = "_zip_orig"  # original Zip Code slot → unused
                cols[prov_idx] = "Country"            # Province slot → country code data
            df.columns = cols

    return _df_to_records(df)


def parse_lazada_file(file_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    """
    Parse a Lazada order export file (CSV or Excel).

    Quirks handled:
    - Duplicate 'status' column (col 66 = platform status, col 76 = manual status).
      pandas renames the second occurrence to 'status.1' automatically.
      We rename 'status' -> 'status_platform' and 'status.1' -> 'status_manual'
      for clarity before returning.
    - NaN values and empty strings replaced with None
    """
    df = _read_dataframe(file_bytes, filename)

    # Rename duplicate status columns
    cols = list(df.columns)
    first_status = True
    renamed: list[str] = []
    for col in cols:
        if col == "status":
            renamed.append("status_platform" if first_status else "status_manual")
            first_status = False
        elif col == "status.1":
            renamed.append("status_manual")
        else:
            renamed.append(col)
    df.columns = renamed

    return _df_to_records(df)


def parse_tiktok_file(file_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    """
    Parse a TikTok Shop order export file (CSV or Excel).

    Quirks handled:
    - Column header 'Tracking ID<sample_number>' (e.g. 'Tracking ID577729206730130897')
      — TikTok appends a sample tracking code to the column header. Any column whose
      name starts with 'Tracking ID' is renamed to 'Tracking ID'.
    - NaN values and empty strings replaced with None
    """
    df = _read_dataframe(file_bytes, filename)

    # Fix the corrupted "Tracking ID<number>" column header
    df.columns = [
        "Tracking ID" if col.startswith("Tracking ID") else col
        for col in df.columns
    ]

    return _df_to_records(df)
