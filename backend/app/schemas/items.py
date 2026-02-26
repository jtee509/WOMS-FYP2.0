"""
WOMS Item Schemas

Request/response models for Items, Categories, Brands, Status, BaseUOM endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Lookup tables (read-only for API — seeded from reference data)
# ---------------------------------------------------------------------------

class StatusRead(BaseModel):
    status_id: int
    status_name: str

class ItemTypeRead(BaseModel):
    item_type_id: int
    item_type_name: str

class CategoryRead(BaseModel):
    category_id: int
    category_name: str

class BrandRead(BaseModel):
    brand_id: int
    brand_name: str

class BaseUOMRead(BaseModel):
    uom_id: int
    uom_name: str


# ---------------------------------------------------------------------------
# Item CRUD
# ---------------------------------------------------------------------------

class ItemCreate(BaseModel):
    """POST /items request body."""
    item_name: str = Field(..., max_length=500)
    master_sku: str = Field(..., max_length=100)
    sku_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    status_id: Optional[int] = None
    item_type_id: Optional[int] = None
    category_id: Optional[int] = None
    parent_id: Optional[int] = None
    has_variation: bool = False
    variations_data: Optional[dict[str, Any]] = None


class ItemUpdate(BaseModel):
    """PATCH /items/{id} request body. All fields optional."""
    item_name: Optional[str] = Field(None, max_length=500)
    sku_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    status_id: Optional[int] = None
    item_type_id: Optional[int] = None
    category_id: Optional[int] = None
    has_variation: Optional[bool] = None
    variations_data: Optional[dict[str, Any]] = None


class ItemRead(BaseModel):
    """Response body for a single item."""
    item_id: int
    parent_id: Optional[int] = None
    item_name: str
    master_sku: str
    sku_name: Optional[str] = None
    product_number: Optional[int] = None
    description: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    status_id: Optional[int] = None
    item_type_id: Optional[int] = None
    category_id: Optional[int] = None
    has_variation: bool
    variations_data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    # Nested lookups (populated when joined)
    uom: Optional[BaseUOMRead] = None
    brand: Optional[BrandRead] = None
    status: Optional[StatusRead] = None
    item_type: Optional[ItemTypeRead] = None
    category: Optional[CategoryRead] = None
