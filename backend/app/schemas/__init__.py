"""
WOMS Pydantic Schemas Package

This package contains Pydantic schemas for API request/response validation.
Schemas are organized by domain matching the models structure.

Schema naming conventions:
- {Model}Create: For POST request bodies
- {Model}Update: For PUT/PATCH request bodies
- {Model}Read: For response bodies
- {Model}InDB: For internal use with DB fields

Example:
    class ItemCreate(BaseModel):
        item_name: str
        master_sku: str
        
    class ItemRead(ItemCreate):
        item_id: int
        created_at: datetime
"""

# Auth
from app.schemas.auth import LoginRequest, TokenResponse, TokenPayload  # noqa: F401

# Common
from app.schemas.common import PaginatedResponse, ErrorResponse, MessageResponse  # noqa: F401

# Items
from app.schemas.items import ItemCreate, ItemRead, ItemUpdate  # noqa: F401

# Orders
from app.schemas.orders import OrderCreate, OrderRead, OrderUpdate, OrderListItem  # noqa: F401

# Platform / Seller
from app.schemas.platform import PlatformCreate, PlatformRead, SellerCreate, SellerRead  # noqa: F401

# Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, InventoryLevelRead  # noqa: F401

# Delivery
from app.schemas.delivery import DeliveryTripCreate, DeliveryTripRead, DriverCreate, DriverRead  # noqa: F401

# Users
from app.schemas.users import UserCreate, UserRead, UserUpdate, RoleRead  # noqa: F401
