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

# Schemas will be imported here as they are implemented
# from app.schemas.items import ItemCreate, ItemRead, ItemUpdate
# from app.schemas.warehouse import WarehouseCreate, WarehouseRead
# from app.schemas.orders import OrderCreate, OrderRead
# from app.schemas.delivery import TripCreate, TripRead
# from app.schemas.users import UserCreate, UserRead, Token
