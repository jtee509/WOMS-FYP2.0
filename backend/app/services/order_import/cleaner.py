"""
Order Import Cleaner

Data cleaning functions applied to raw rows before mapping to the staging schema.
Handles encoding issues, inconsistent date formats, type coercions, and the
column-misalignment quirks found in the test datasets.
"""

import re
from datetime import date, datetime
from typing import Any

# Fullwidth comma (U+FF0C) found in Lazada address fields
_FULLWIDTH_COMMA = "\uff0c"

# Date patterns tried in order (most specific first)
_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",   # 2025-12-24T16:24:00
    "%Y-%m-%d %H:%M:%S",   # 2025-12-24 16:24:00
    "%Y-%m-%d",            # 2025-12-24
    "%d/%m/%Y %H:%M:%S",   # 24/12/2025 16:24:00  (TikTok full)
    "%d/%m/%Y %H:%M",      # 23/12/2025 20:52     (Shopee/Lazada, no seconds)
    "%d.%m.%Y",            # 24.12.2025
    "%d/%m/%Y",            # 24/12/2025
    "%-d.%-m.%Y",          # 1.1.2024  (Linux)
    "%#d.%#m.%Y",          # 1.1.2024  (Windows)
]

# Regex to quickly reject values that cannot be a date (e.g. driver names)
_DATE_LIKE_RE = re.compile(r"[\d]{1,4}[.\-/T: ][\d]{1,2}")


def normalize_address(text: str | None) -> str | None:
    """Replace fullwidth commas (U+FF0C) with ASCII commas."""
    if not text:
        return text
    return text.replace(_FULLWIDTH_COMMA, ",")


def parse_flexible_date(value: Any) -> date | None:
    """
    Parse a date value from multiple formats. Returns None if unparseable.

    Handles:
    - pandas Timestamp / datetime objects
    - ISO strings (2025-12-24T16:24:00)
    - European dot-separated (24.12.2025, 1.1.2024)
    - Slash-separated (24/12/2025)
    - Non-date strings (driver names, tracking codes) → None
    """
    if value is None:
        return None

    # Already a date/datetime object
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "nat"):
        return None

    # Quick reject: if it doesn't look like it contains digits arranged as a date
    if not _DATE_LIKE_RE.search(text):
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def parse_phone(value: Any) -> str | None:
    """
    Normalise a phone number to a plain string.

    Excel often stores phone numbers as floats (e.g. 60123456789.0).
    Strips the trailing '.0' and returns a string.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none"):
        return None
    # Remove trailing .0 from numeric representation
    if text.endswith(".0"):
        text = text[:-2]
    return text or None


def parse_decimal(value: Any) -> str | None:
    """Return value as a plain string for Decimal fields, or None if blank."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none"):
        return None
    return text


def parse_int(value: Any) -> int | None:
    """Parse an integer field, returning None if blank or unparseable."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none"):
        return None
    try:
        return int(float(text))
    except (ValueError, OverflowError):
        return None


def parse_str(value: Any, max_len: int | None = None) -> str | None:
    """Clean a string field: strip whitespace, return None for blanks."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none"):
        return None
    if max_len:
        text = text[:max_len]
    return text


# ---------------------------------------------------------------------------
# Per-platform row cleaners
# ---------------------------------------------------------------------------

def clean_shopee_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Apply cleaning to a raw Shopee row dict.

    Key issues:
    - The 'Date' manual column (col 59) sometimes contains driver names or
      tracking codes instead of dates — parse_flexible_date() returns None
      for those, preserving the raw value in raw_row_data for traceability.
    - Phone number stored as float.
    - Dates in multiple formats.
    """
    cleaned = dict(row)

    # String fields
    for field in (
        "Order ID", "Order Status", "SKU Reference No.", "Parent SKU Reference No.",
        "Product Name", "Variation Name", "Tracking Number", "Shipment Method",
        "Shipping Option", "Receiver Name", "Delivery Address", "Town",
        "District", "Province", "City", "Country", "Username (Buyer)",
        "Voucher Code", "Remark from buyer",
        # Manual tracking
        "status", "Driver", "note",
    ):
        cleaned[field] = parse_str(cleaned.get(field))

    # Phone number
    cleaned["Phone Number"] = parse_phone(cleaned.get("Phone Number"))

    # Zip code (stored as numeric in Excel → string)
    cleaned["Zip Code"] = parse_str(cleaned.get("Zip Code"))

    # Dates
    for date_field in (
        "Estimated Ship Out Date", "Ship Time",
        "Order Creation Date", "Order Paid Time", "Order Complete Time",
    ):
        cleaned[date_field] = parse_flexible_date(cleaned.get(date_field))

    # Manual Date column — may contain non-date garbage
    cleaned["Date"] = parse_flexible_date(cleaned.get("Date"))

    # Numeric/decimal fields
    for dec_field in (
        "Original Price", "Deal Price", "Product Subtotal",
        "Seller Rebate", "Seller Discount", "Shopee Rebate",
        "Total Amount", "Buyer Paid Shipping Fee", "Shipping Rebate Estimate",
        "Reverse Shipping Fee", "Transaction Fee", "Commission Fee",
        "Service Fee", "Grand Total", "Estimated Shipping Fee",
        "Shopee Voucher", "Seller Voucher", "Seller Absorbed Coin Cashback",
        "Shopee Bundle Discount", "Seller Bundle Discount",
        "Shopee Coins Offset", "Credit Card Discount Total",
    ):
        cleaned[dec_field] = parse_decimal(cleaned.get(dec_field))

    for int_field in ("Quantity", "Returned quantity", "No of product in order"):
        cleaned[int_field] = parse_int(cleaned.get(int_field))

    return cleaned


def clean_tiktok_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Apply cleaning to a raw TikTok Shop row dict.

    Key issues:
    - Dates use DD/MM/YYYY HH:MM:SS format (added to _DATE_FORMATS).
    - Phone field named 'Phone #' (unusual column name).
    - Multiple timestamp columns (Created Time, Paid Time, RTS Time, etc.) —
      all parsed; only Created Time maps to order_date in staging.
    - Manual tracking columns (status, Driver, Date, note) follow the same
      pattern as Shopee/Lazada.
    """
    cleaned = dict(row)

    # String fields
    for field in (
        "Order ID", "Order Status", "Seller SKU", "Product Name", "Variation",
        "Tracking ID", "Recipient", "Detail Address", "State", "Post Town",
        "Zipcode", "Country", "Shipping Provider Name",
        "Package ID", "Warehouse Name", "Seller Note", "Buyer Note",
        "Cancel Reason", "Return/Refund Status",
        # Manual tracking
        "status", "Driver", "note",
    ):
        cleaned[field] = parse_str(cleaned.get(field))

    # Phone number (column named "Phone #" in TikTok exports)
    cleaned["Phone #"] = parse_phone(cleaned.get("Phone #"))

    # Dates — multiple timestamp columns
    for date_field in (
        "Created Time", "Paid Time", "RTS Time",
        "Shipped Time", "Delivered Time", "Cancelled Time",
    ):
        cleaned[date_field] = parse_flexible_date(cleaned.get(date_field))

    # Manual Date column — may contain non-date values
    cleaned["Date"] = parse_flexible_date(cleaned.get("Date"))

    # Decimal fields
    for dec_field in (
        "Order Amount", "SKU Unit Original Price", "SKU Subtotal After Discount",
        "Shipping Fee After Discount", "SKU Seller Discount",
        "Platform Discount", "Seller Voucher", "Shopee Voucher",
    ):
        cleaned[dec_field] = parse_decimal(cleaned.get(dec_field))

    # Integer fields
    cleaned["Quantity"] = parse_int(cleaned.get("Quantity"))

    return cleaned


def clean_lazada_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Apply cleaning to a raw Lazada row dict.

    Key issues:
    - Fullwidth commas (U+FF0C) in address fields.
    - Phone stored as numeric (large integer → float).
    - Many columns are empty/None — handled gracefully.
    - 'status_platform' = platform status (col 66), 'status_manual' = manual (col 76).
    """
    cleaned = dict(row)

    # String fields
    for field in (
        "orderType", "Guarantee", "deliveryType", "sellerSku", "lazadaSku",
        "invoiceNumber", "customerName", "customerEmail",
        "nationalRegistrationNumber",
        "shippingName", "shippingCity", "shippingCountry", "shippingRegion",
        "billingName", "billingCity", "billingCountry",
        "taxCode", "payMethod", "itemName", "variation",
        "cdShippingProvider", "shippingProvider", "shipmentTypeName",
        "shippingProviderType", "cdTrackingCode", "trackingCode",
        "trackingUrl", "shippingProviderFM", "trackingCodeFM", "trackingUrlFM",
        "premium", "status_platform", "status_manual",
        "buyerFailedDeliveryReturnInitiator", "buyerFailedDeliveryReason",
        "buyerFailedDeliveryDetail", "buyerFailedDeliveryUserName",
        "sellerNote",
        # Manual tracking
        "Driver", "note",
    ):
        cleaned[field] = parse_str(cleaned.get(field))

    # Address fields — normalize fullwidth commas
    for addr_field in (
        "shippingAddress", "shippingAddress2", "shippingAddress3",
        "shippingAddress4", "shippingAddress5",
        "billingAddr", "billingAddr2", "billingAddr3",
        "billingAddr4", "billingAddr5",
    ):
        raw = parse_str(cleaned.get(addr_field))
        cleaned[addr_field] = normalize_address(raw)

    # Phone numbers
    for phone_field in ("shippingPhone", "shippingPhone2", "billingPhone", "billingPhone2"):
        cleaned[phone_field] = parse_phone(cleaned.get(phone_field))

    # Postcode (numeric in Excel)
    cleaned["shippingPostCode"] = parse_str(cleaned.get("shippingPostCode"))
    cleaned["billingPostCode"] = parse_str(cleaned.get("billingPostCode"))

    # Dates
    for date_field in ("createTime", "updateTime", "rtsSla", "ttsSla",
                       "deliveredDate", "promisedShippingTime"):
        cleaned[date_field] = parse_flexible_date(cleaned.get(date_field))

    # Manual Date column
    cleaned["Date"] = parse_flexible_date(cleaned.get("Date"))

    # Decimal fields
    for dec_field in ("paidPrice", "unitPrice", "sellerDiscountTotal",
                      "shippingFee", "walletCredit", "bundleDiscount", "refundAmount"):
        cleaned[dec_field] = parse_decimal(cleaned.get(dec_field))

    # Integer / ID fields
    for int_field in ("orderItemId", "lazadaId", "orderNumber",
                      "branchNumber", "bundleId"):
        cleaned[int_field] = parse_int(cleaned.get(int_field))

    return cleaned
