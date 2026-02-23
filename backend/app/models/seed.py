"""
WOMS Database Seed Data (Python Module)

All initial lookup-table data is defined here as Python data structures and
inserted via SQLAlchemy Core (text() INSERT ... ON CONFLICT DO NOTHING).

WHY Python instead of migrations/004_seed_data.sql:
- No external .sql file dependency.
- `seed_database()` is called from database.init_db_full() so the DB is
  always ready with reference data after initialisation.
- ON CONFLICT DO NOTHING makes every call idempotent — safe to re-run.

Seed tables:
  - action_type       (9 rows)
  - status            (5 rows)  — item statuses
  - item_type         (6 rows)
  - base_uom          (8 rows)
  - inventory_type    (6 rows)
  - movement_type     (7 rows)
  - delivery_status  (12 rows)
  - roles             (7 rows)
  - platform          (4 rows)
  - cancellation_reason (16 rows)
  - return_reason    (20 rows)
  - exchange_reason  (13 rows)
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Seed data definitions
# =============================================================================

_ACTION_TYPES = [
    ("INSERT",      "New record created"),
    ("UPDATE",      "Record modified"),
    ("DELETE",      "Record deleted"),
    ("SOFT_DELETE", "Record soft deleted"),
    ("RESTORE",     "Record restored from soft delete"),
    ("LOGIN",       "User logged in"),
    ("LOGOUT",      "User logged out"),
    ("EXPORT",      "Data exported"),
    ("IMPORT",      "Data imported"),
]

_STATUSES = ["Active", "Inactive", "Discontinued", "Out of Stock", "Pending"]

_ITEM_TYPES = [
    "Raw Material", "Finished Good", "Office Supplies",
    "Component", "Packaging", "Consumable",
]

_BASE_UOMS = ["Each", "PCS", "Box", "Carton", "Kg", "Liter", "Pack", "Set"]

_INVENTORY_TYPES = [
    "Bulk Storage", "Pick Face", "Receiving", "Staging", "Shipping", "Returns",
]

_MOVEMENT_TYPES = [
    "Receipt", "Shipment", "Transfer", "Adjustment",
    "Return", "Cycle Count", "Write Off",
]

_DELIVERY_STATUSES = [
    ("Pending",                "#FFA500"),
    ("Picked Up",              "#2196F3"),
    ("In Transit",             "#9C27B0"),
    ("Out for Delivery",       "#00BCD4"),
    ("In Warehouse",           "#FFD700"),
    ("Delivered",              "#4CAF50"),
    ("Failed",                 "#F44336"),
    ("Cancelled",              "#9E9E9E"),
    ("Return to Sender",       "#FF5722"),
    ("Returned to Warehouse",  "#795548"),
    ("Customer Refused",       "#E91E63"),
    ("Address Invalid",        "#607D8B"),
]

_ROLES = [
    ("Super Admin", "Full system access"),
    ("Admin",       "Administrative access"),
    ("Manager",     "Warehouse manager"),
    ("Staff",       "Warehouse staff"),
    ("Driver",      "Delivery driver"),
    ("Picker",      "Order picker"),
    ("Packer",      "Order packer"),
]

_PLATFORMS = ["Shopee", "Lazada", "TikTok Shop", "Manual"]

# (reason_code, reason_name, reason_type, requires_inspection, auto_restock)
_CANCELLATION_REASONS = [
    ("CUSTOMER_REQUEST",       "Customer requested cancellation",   "customer",  False, True),
    ("CUSTOMER_CHANGED_MIND",  "Customer changed mind",             "customer",  False, True),
    ("CUSTOMER_DUPLICATE_ORDER","Customer duplicate order",         "customer",  False, True),
    ("SELLER_CANCEL",          "Seller cancelled order",            "seller",    False, True),
    ("OUT_OF_STOCK",           "Item out of stock",                 "seller",    False, False),
    ("PRICING_ERROR",          "Pricing error",                     "seller",    False, True),
    ("PLATFORM_REFUND",        "Platform refund approved",          "platform",  True,  False),
    ("PLATFORM_RETURN",        "Platform return request approved",  "platform",  True,  False),
    ("PLATFORM_DISPUTE",       "Platform dispute resolved",         "platform",  True,  False),
    ("DELIVERY_FAILED",        "Multiple delivery attempts failed", "delivery",  True,  False),
    ("CUSTOMER_REFUSED",       "Customer refused delivery",         "delivery",  True,  False),
    ("ADDRESS_INVALID",        "Invalid or unreachable address",    "delivery",  False, True),
    ("CUSTOMER_UNAVAILABLE",   "Customer unavailable",              "delivery",  True,  False),
    ("FRAUD_SUSPECTED",        "Suspected fraudulent order",        "system",    True,  False),
    ("PAYMENT_FAILED",         "Payment verification failed",       "system",    False, True),
    ("OTHER",                  "Other reason",                      "system",    True,  False),
]

# (reason_code, reason_name, reason_type, requires_inspection)
_RETURN_REASONS = [
    ("WRONG_ITEM",              "Wrong item received",                          "customer",  True),
    ("WRONG_SIZE",              "Wrong size received",                          "customer",  True),
    ("WRONG_COLOR",             "Wrong color received",                         "customer",  True),
    ("DAMAGED_RECEIVED",        "Item damaged on arrival",                      "customer",  True),
    ("NOT_AS_DESCRIBED",        "Item not as described",                        "customer",  True),
    ("CHANGED_MIND",            "Customer changed mind",                        "customer",  True),
    ("DUPLICATE_ORDER",         "Duplicate order received",                     "customer",  False),
    ("QUALITY_ISSUE",           "Quality does not meet expectations",           "quality",   True),
    ("PLATFORM_RETURN_REQUEST", "Platform return request approved",             "platform",  True),
    ("PLATFORM_REFUND_APPROVED","Platform refund approved",                     "platform",  True),
    ("PLATFORM_DISPUTE_RESOLVED","Platform dispute resolved in buyer favor",    "platform",  True),
    ("DELIVERY_FAILED",         "Multiple delivery attempts failed",            "delivery",  True),
    ("CUSTOMER_REFUSED",        "Customer refused delivery",                    "delivery",  True),
    ("UNDELIVERABLE_ADDRESS",   "Address undeliverable",                        "delivery",  False),
    ("CUSTOMER_UNAVAILABLE",    "Customer unavailable for delivery",            "delivery",  True),
    ("RETURN_TO_SENDER",        "Return to sender requested",                   "delivery",  True),
    ("DEFECTIVE_PRODUCT",       "Defective product",                            "quality",   True),
    ("MANUFACTURING_DEFECT",    "Manufacturing defect",                         "quality",   True),
    ("MISSING_PARTS",           "Missing parts or accessories",                 "quality",   True),
    ("EXPIRED_PRODUCT",         "Product expired or near expiry",               "quality",   True),
    ("OTHER_RETURN",            "Other return reason",                          "customer",  True),
]

# (reason_code, reason_name, requires_return)
_EXCHANGE_REASONS = [
    ("EXCHANGE_WRONG_SIZE",        "Exchange for different size",        True),
    ("EXCHANGE_BETTER_FIT",        "Exchange for better fit",            True),
    ("EXCHANGE_WRONG_COLOR",       "Exchange for different color",       True),
    ("EXCHANGE_DIFFERENT_VARIANT", "Exchange for different variant",     True),
    ("EXCHANGE_DEFECTIVE",         "Exchange due to defect",             True),
    ("EXCHANGE_DAMAGED",           "Exchange due to damage",             True),
    ("EXCHANGE_QUALITY_ISSUE",     "Exchange due to quality issue",      True),
    ("EXCHANGE_CUSTOMER_PREFERENCE","Customer preference change",        True),
    ("EXCHANGE_UPGRADE",           "Upgrade to better product",          True),
    ("EXCHANGE_DOWNGRADE",         "Downgrade to cheaper product",       True),
    ("EXCHANGE_WRONG_ITEM_SENT",   "Wrong item was sent",                True),
    ("EXCHANGE_MISSING_ITEM",      "Item was missing from order",        False),
    ("EXCHANGE_OTHER",             "Other exchange reason",              True),
]


# =============================================================================
# Public API
# =============================================================================

async def seed_database(session: AsyncSession) -> None:
    """
    Insert all seed / reference data into lookup tables.

    Every INSERT uses ON CONFLICT DO NOTHING so this is fully idempotent —
    safe to call on a DB that already has data.

    Called by database.init_db_full() after triggers and views are applied.
    """

    # action_type
    await session.execute(
        text(
            "INSERT INTO action_type (action_name, description, created_at) "
            "VALUES (:name, :desc, NOW()) ON CONFLICT (action_name) DO NOTHING"
        ),
        [{"name": n, "desc": d} for n, d in _ACTION_TYPES],
    )

    # status (item statuses)
    await session.execute(
        text("INSERT INTO status (status_name) VALUES (:name) ON CONFLICT (status_name) DO NOTHING"),
        [{"name": s} for s in _STATUSES],
    )

    # item_type
    await session.execute(
        text("INSERT INTO item_type (item_type_name) VALUES (:name) ON CONFLICT (item_type_name) DO NOTHING"),
        [{"name": t} for t in _ITEM_TYPES],
    )

    # base_uom
    await session.execute(
        text("INSERT INTO base_uom (uom_name) VALUES (:name) ON CONFLICT (uom_name) DO NOTHING"),
        [{"name": u} for u in _BASE_UOMS],
    )

    # inventory_type
    await session.execute(
        text("INSERT INTO inventory_type (inventory_type_name) VALUES (:name) ON CONFLICT (inventory_type_name) DO NOTHING"),
        [{"name": t} for t in _INVENTORY_TYPES],
    )

    # movement_type
    await session.execute(
        text("INSERT INTO movement_type (movement_name) VALUES (:name) ON CONFLICT (movement_name) DO NOTHING"),
        [{"name": t} for t in _MOVEMENT_TYPES],
    )

    # delivery_status
    await session.execute(
        text(
            "INSERT INTO delivery_status (status_name, status_color) "
            "VALUES (:name, :color) ON CONFLICT (status_name) DO NOTHING"
        ),
        [{"name": n, "color": c} for n, c in _DELIVERY_STATUSES],
    )

    # roles
    await session.execute(
        text(
            "INSERT INTO roles (role_name, description, created_at) "
            "VALUES (:name, :desc, NOW()) ON CONFLICT (role_name) DO NOTHING"
        ),
        [{"name": n, "desc": d} for n, d in _ROLES],
    )

    # platform
    await session.execute(
        text(
            "INSERT INTO platform (platform_name, is_active, created_at) "
            "VALUES (:name, TRUE, NOW()) ON CONFLICT (platform_name) DO NOTHING"
        ),
        [{"name": p} for p in _PLATFORMS],
    )

    # cancellation_reason
    await session.execute(
        text(
            "INSERT INTO cancellation_reason "
            "(reason_code, reason_name, reason_type, requires_inspection, auto_restock, is_active, created_at) "
            "VALUES (:code, :name, :rtype, :insp, :restock, TRUE, NOW()) "
            "ON CONFLICT (reason_code) DO NOTHING"
        ),
        [
            {"code": c, "name": n, "rtype": t, "insp": i, "restock": r}
            for c, n, t, i, r in _CANCELLATION_REASONS
        ],
    )

    # return_reason
    await session.execute(
        text(
            "INSERT INTO return_reason "
            "(reason_code, reason_name, reason_type, requires_inspection, is_active, created_at) "
            "VALUES (:code, :name, :rtype, :insp, TRUE, NOW()) "
            "ON CONFLICT (reason_code) DO NOTHING"
        ),
        [
            {"code": c, "name": n, "rtype": t, "insp": i}
            for c, n, t, i in _RETURN_REASONS
        ],
    )

    # exchange_reason
    await session.execute(
        text(
            "INSERT INTO exchange_reason "
            "(reason_code, reason_name, requires_return, is_active, created_at) "
            "VALUES (:code, :name, :ret, TRUE, NOW()) "
            "ON CONFLICT (reason_code) DO NOTHING"
        ),
        [{"code": c, "name": n, "ret": r} for c, n, r in _EXCHANGE_REASONS],
    )

    await session.commit()
    print("[OK] Seed data inserted (all ON CONFLICT DO NOTHING - idempotent)")
