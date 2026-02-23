"""
Order Import Mapper

Defines per-platform field mappings and builds the staging dict from a cleaned
raw row. Each map entry is: staging_field -> source_column_name_in_raw_row.

Special sentinel values:
  LITERAL:<value>  — use a literal value (e.g. LITERAL:1 for Lazada quantity)
  CAST_STR         — cast the source value to string (e.g. Lazada orderNumber is int)
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Field mapping declarations
# ---------------------------------------------------------------------------

# fmt: off
SHOPEE_FIELD_MAP: dict[str, str] = {
    "platform_order_id":     "Order ID",
    "order_date":            "Order Creation Date",
    "recipient_name":        "Receiver Name",
    "phone_number":          "Phone Number",
    "shipping_address":      "Delivery Address",
    "shipping_postcode":     "Zip Code",
    "shipping_state":        "Province",
    "country":               "Country",
    "platform_sku":          "SKU Reference No.",
    "sku_name":              "Product Name",
    "variation_name":        "Variation Name",
    "quantity":              "Quantity",
    "unit_price":            "Original Price",
    "paid_amount":           "Grand Total",
    "shipping_fee":          "Buyer Paid Shipping Fee",
    "discount":              "Seller Discount",
    "courier_type":          "Shipment Method",
    "tracking_number":       "Tracking Number",
    "platform_order_status": "Order Status",
    "manual_status":         "status",
    "manual_driver":         "Driver",
    "manual_date":           "Date",
    "manual_note":           "note",
}

LAZADA_FIELD_MAP: dict[str, str] = {
    "platform_order_id":     "__CAST_STR__orderNumber",
    "order_date":            "createTime",
    "recipient_name":        "shippingName",
    "phone_number":          "shippingPhone",
    "shipping_address":      "shippingAddress",
    "shipping_postcode":     "shippingPostCode",
    "shipping_state":        "shippingCity",
    "country":               "shippingCountry",
    "platform_sku":          "sellerSku",
    "sku_name":              "itemName",
    "variation_name":        "variation",
    "quantity":              "__LITERAL__1",
    "unit_price":            "unitPrice",
    "paid_amount":           "paidPrice",
    "shipping_fee":          "shippingFee",
    "discount":              "sellerDiscountTotal",
    "courier_type":          "shippingProvider",
    "tracking_number":       "trackingCode",
    "platform_order_status": "status_platform",
    "manual_status":         "status_manual",
    "manual_driver":         "Driver",
    "manual_date":           "Date",
    "manual_note":           "note",
}

TIKTOK_FIELD_MAP: dict[str, str] = {
    "platform_order_id":     "Order ID",
    "order_date":            "Created Time",
    "recipient_name":        "Recipient",
    "phone_number":          "Phone #",
    "shipping_address":      "Detail Address",
    "shipping_postcode":     "Zipcode",
    "shipping_state":        "State",
    "country":               "Country",
    "platform_sku":          "Seller SKU",
    "sku_name":              "Product Name",
    "variation_name":        "Variation",
    "quantity":              "Quantity",
    "unit_price":            "SKU Unit Original Price",
    "paid_amount":           "Order Amount",
    "shipping_fee":          "Shipping Fee After Discount",
    "discount":              "SKU Seller Discount",
    "courier_type":          "Shipping Provider Name",
    "tracking_number":       "Tracking ID",
    "platform_order_status": "Order Status",
    "manual_status":         "status",
    "manual_driver":         "Driver",
    "manual_date":           "Date",
    "manual_note":           "note",
}
# fmt: on

_PLATFORM_MAPS: dict[str, dict[str, str]] = {
    "shopee": SHOPEE_FIELD_MAP,
    "lazada": LAZADA_FIELD_MAP,
    "tiktok": TIKTOK_FIELD_MAP,
}


# ---------------------------------------------------------------------------
# Type coercions for staging columns
# ---------------------------------------------------------------------------

def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# Staging columns that require Decimal
_DECIMAL_FIELDS = frozenset({
    "unit_price", "paid_amount", "shipping_fee", "discount",
})

# Staging columns that require int
_INT_FIELDS = frozenset({"quantity"})

# Staging columns that remain as date (already parsed by cleaner)
_DATE_FIELDS = frozenset({"order_date", "manual_date"})


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def map_to_staging(
    platform: str,
    cleaned_row: dict[str, Any],
    seller_id: int,
    raw_import_id: int,
) -> dict[str, Any]:
    """
    Build a dict suitable for inserting into order_import.order_import_staging.

    Args:
        platform: 'shopee', 'lazada', or 'tiktok' (case-insensitive)
        cleaned_row: Row dict already processed by clean_shopee_row / clean_lazada_row
        seller_id: FK to seller table
        raw_import_id: FK to order_import.order_import_raw

    Returns:
        Dict with all staging column keys populated (None for missing values).
    """
    field_map = _PLATFORM_MAPS.get(platform.lower())
    if field_map is None:
        raise ValueError(f"Unknown platform: {platform!r}. Supported: shopee, lazada, tiktok")

    staging: dict[str, Any] = {
        "seller_id": seller_id,
        "platform_source": platform.lower(),
        "raw_import_id": raw_import_id,
        "raw_row_data": cleaned_row,
    }

    for staging_col, source in field_map.items():
        if source.startswith("__LITERAL__"):
            # Hard-coded literal value
            literal = source[len("__LITERAL__"):]
            if staging_col in _INT_FIELDS:
                value: Any = _to_int(literal)
            elif staging_col in _DECIMAL_FIELDS:
                value = _to_decimal(literal)
            else:
                value = literal

        elif source.startswith("__CAST_STR__"):
            # Cast source column value to string
            col_name = source[len("__CAST_STR__"):]
            raw = cleaned_row.get(col_name)
            value = str(raw) if raw is not None else None

        else:
            raw = cleaned_row.get(source)

            if staging_col in _DECIMAL_FIELDS:
                value = _to_decimal(raw)
            elif staging_col in _INT_FIELDS:
                value = _to_int(raw)
            elif staging_col in _DATE_FIELDS:
                # Already a date | None from cleaner
                value = raw if isinstance(raw, date) else None
            else:
                value = raw  # str | None already cleaned

        staging[staging_col] = value

    return staging
