"""
WOMS Models Package

Exports all SQLModel models for the Warehouse Order Management System.
Models are organized into logical modules:
- items: Item management, categories, brands, variations
- warehouse: Warehouse locations, inventory tracking, stock management
- order_import: Lazada/Shopee order uploads (raw + staging)
- orders: Orders, platforms, sellers, listings
- order_operations: Returns, exchanges, modifications, price adjustments
- delivery: Drivers, trips, delivery status
- users: User accounts, roles, audit logging

DB initialization utilities (called by database.run_migrations()):
- triggers: apply_triggers(conn) — all PostgreSQL trigger functions
- views: apply_views(conn) — all reporting views
- seed: seed_database(session) — lookup table seed data
"""

# =============================================================================
# Items Module
# =============================================================================
from app.models.items import (
    Status,
    ItemType,
    Category,
    Brand,
    BaseUOM,
    Item,
    ItemsHistory,
)

# =============================================================================
# Warehouse Module
# =============================================================================
from app.models.warehouse import (
    Warehouse,
    InventoryType,
    InventoryLocation,
    MovementType,
    InventoryMovement,
    InventoryTransaction,
    StockLot,
    InventoryLevel,
    InventoryReplenishmentHistory,
    InventoryAlert,
    SellerWarehouse,
)

# =============================================================================
# Order Import Module (Lazada/Shopee uploads)
# =============================================================================
from app.models.order_import import (
    OrderImportRaw,
    OrderImportStaging,
)

# =============================================================================
# Orders Module
# =============================================================================
from app.models.orders import (
    Platform,
    Seller,
    PlatformSKU,
    ListingComponent,
    CustomerPlatform,
    PlatformRawImport,
    CancellationReason,
    OrderCancellation,
    Order,
    OrderDetail,
)

# =============================================================================
# Order Operations Module (Returns, Exchanges, Modifications)
# =============================================================================
from app.models.order_operations import (
    ReturnReason,
    OrderReturn,
    ExchangeReason,
    OrderExchange,
    OrderModification,
    OrderPriceAdjustment,
)

# =============================================================================
# Delivery Module
# =============================================================================
from app.models.delivery import (
    CompanyFirm,
    Lorry,
    Driver,
    DriverCredential,
    DriverTeam,
    DeliveryTrip,
    TripOrder,
    DeliveryStatus,
    TrackingStatus,
)

# =============================================================================
# Users Module
# =============================================================================
from app.models.users import (
    ActionType,
    Role,
    User,
    AuditLog,
)


# =============================================================================
# DB Initialization Utilities
# =============================================================================
from app.models.triggers import apply_triggers
from app.models.views import apply_views
from app.models.seed import seed_database


# =============================================================================
# All Models Export
# =============================================================================
__all__ = [
    # Items
    "Status",
    "ItemType",
    "Category",
    "Brand",
    "BaseUOM",
    "Item",
    "ItemsHistory",
    # Warehouse
    "Warehouse",
    "InventoryType",
    "InventoryLocation",
    "MovementType",
    "InventoryMovement",
    "InventoryTransaction",
    "StockLot",
    "InventoryLevel",
    "InventoryReplenishmentHistory",
    "InventoryAlert",
    "SellerWarehouse",
    # Order Import
    "OrderImportRaw",
    "OrderImportStaging",
    # Orders
    "Platform",
    "Seller",
    "PlatformSKU",
    "ListingComponent",
    "CustomerPlatform",
    "PlatformRawImport",
    "CancellationReason",
    "OrderCancellation",
    "Order",
    "OrderDetail",
    # Order Operations
    "ReturnReason",
    "OrderReturn",
    "ExchangeReason",
    "OrderExchange",
    "OrderModification",
    "OrderPriceAdjustment",
    # Delivery
    "CompanyFirm",
    "Lorry",
    "Driver",
    "DriverCredential",
    "DriverTeam",
    "DeliveryTrip",
    "TripOrder",
    "DeliveryStatus",
    "TrackingStatus",
    # Users
    "ActionType",
    "Role",
    "User",
    "AuditLog",
    # DB init utilities
    "apply_triggers",
    "apply_views",
    "seed_database",
]
