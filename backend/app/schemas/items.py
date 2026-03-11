"""
WOMS Item Schemas

Request/response models for Items, Categories, Brands, BaseUOM endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared nested shape — used inside ItemRead for all lookup relations.
# Matches the frontend AttributeItem interface { id, name }.
# ---------------------------------------------------------------------------

class AttributeItemRead(BaseModel):
    id: int
    name: str


# ---------------------------------------------------------------------------
# Lookup tables — Read / Create / Update
# ---------------------------------------------------------------------------

class ItemTypeRead(BaseModel):
    item_type_id: int
    item_type_name: str
    deleted_at: Optional[datetime] = None

class ItemTypeCreate(BaseModel):
    item_type_name: str = Field(..., max_length=100)

class ItemTypeUpdate(BaseModel):
    item_type_name: Optional[str] = Field(None, max_length=100)


class CategoryRead(BaseModel):
    category_id: int
    category_name: str
    deleted_at: Optional[datetime] = None

class CategoryCreate(BaseModel):
    category_name: str = Field(..., max_length=100)

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = Field(None, max_length=100)


class BrandRead(BaseModel):
    brand_id: int
    brand_name: str
    deleted_at: Optional[datetime] = None

class BrandCreate(BaseModel):
    brand_name: str = Field(..., max_length=200)

class BrandUpdate(BaseModel):
    brand_name: Optional[str] = Field(None, max_length=200)


class BaseUOMRead(BaseModel):
    uom_id: int
    uom_name: str
    deleted_at: Optional[datetime] = None

class BaseUOMCreate(BaseModel):
    uom_name: str = Field(..., max_length=50)

class BaseUOMUpdate(BaseModel):
    uom_name: Optional[str] = Field(None, max_length=50)


# ---------------------------------------------------------------------------
# Item CRUD
# ---------------------------------------------------------------------------

class ItemCreate(BaseModel):
    """POST /items request body."""
    item_name: str = Field(..., max_length=500)
    master_sku: str = Field(..., max_length=100)
    sku_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    image_url: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    item_type_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: bool = True
    parent_id: Optional[int] = None
    has_variation: bool = False
    variations_data: Optional[dict[str, Any]] = None


class ItemUpdate(BaseModel):
    """PATCH /items/{id} request body. All fields optional."""
    item_name: Optional[str] = Field(None, max_length=500)
    sku_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    image_url: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    item_type_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    has_variation: Optional[bool] = None
    variations_data: Optional[dict[str, Any]] = None


class ItemRead(BaseModel):
    """Response body for a single item."""
    item_id: int
    parent_id: Optional[int] = None
    item_name: str
    master_sku: str
    sku_name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    item_type_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: bool = True
    has_variation: bool
    variations_data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    # Nested lookups — serialised as { id, name } to match frontend AttributeItem
    uom: Optional[AttributeItemRead] = None
    brand: Optional[AttributeItemRead] = None
    item_type: Optional[AttributeItemRead] = None
    category: Optional[AttributeItemRead] = None


# ---------------------------------------------------------------------------
# Mass Import
# ---------------------------------------------------------------------------

class ImportRowError(BaseModel):
    row: int
    master_sku: str
    error: str


class ImportResult(BaseModel):
    total_rows: int
    success_rows: int
    error_rows: int
    errors: list[ImportRowError]


# ---------------------------------------------------------------------------
# Bundle Creation
# ---------------------------------------------------------------------------

class BundleComponentInput(BaseModel):
    """A single component in a bundle: an existing item and its quantity."""
    item_id: int = Field(..., description="ID of the component item (must exist in items table)")
    quantity: int = Field(..., ge=1, description="Quantity of this item in the bundle")


class BundleCreateRequest(BaseModel):
    """
    POST /items/bundles request body.

    Creates a bundle item + its listing components in a single transaction.
    Requires platform_id and seller_id because listing_component
    is linked through the platform_sku table.
    """
    item_name: str = Field(..., max_length=500)
    master_sku: str = Field(..., max_length=100, description="Must be unique across all items")
    sku_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    image_url: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: bool = True

    platform_id: Optional[int] = Field(None, description="Platform for the bundle listing (optional)")
    seller_id: Optional[int] = Field(None, description="Seller for the bundle listing (optional)")

    components: list[BundleComponentInput] = Field(
        ...,
        min_length=1,
        description="At least one component; a bundle must have >1 distinct items or qty > 1",
    )


class BundleComponentRead(BaseModel):
    """A resolved component in a bundle response."""
    id: int
    item_id: int
    item_name: str
    master_sku: str
    quantity: int


class BundleReadResponse(BaseModel):
    """Response body for bundle creation and update."""
    item: ItemRead
    listing_id: Optional[int] = None
    platform_sku: Optional[str] = None
    components: list[BundleComponentRead]


class BundleListItem(BaseModel):
    """Response body for the bundles list view — ItemRead plus component counts."""
    item_id: int
    parent_id: Optional[int] = None
    item_name: str
    master_sku: str
    sku_name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    item_type_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: bool = True
    has_variation: bool = False
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    uom: Optional[AttributeItemRead] = None
    brand: Optional[AttributeItemRead] = None
    item_type: Optional[AttributeItemRead] = None
    category: Optional[AttributeItemRead] = None

    component_count: int = 0
    total_quantity: int = 0


class BundleUpdateRequest(BaseModel):
    """
    PATCH /items/bundles/{item_id} request body.

    All fields are optional. Only provided fields are changed.
    When `components` is provided, the existing listing_component rows
    for this bundle are deleted and replaced with the new set
    (delete-and-reinsert strategy).
    """
    item_name: Optional[str] = Field(None, max_length=500)
    master_sku: Optional[str] = Field(None, max_length=100, description="New unique SKU for the bundle itself")
    sku_name: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    image_url: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None

    components: Optional[list[BundleComponentInput]] = Field(
        None,
        min_length=1,
        description="If provided, replaces ALL existing components (delete-and-reinsert). "
                    "Must still satisfy bundle rules (>1 items or qty > 1).",
    )
