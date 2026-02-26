"""
WOMS Platform & Seller Schemas

Request/response models for Platform and Seller CRUD endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------

class PlatformCreate(BaseModel):
    """POST /platforms request body."""
    platform_name: str = Field(..., max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    postcode: Optional[str] = Field(None, max_length=20)
    api_endpoint: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class PlatformUpdate(BaseModel):
    """PATCH /platforms/{id} request body."""
    platform_name: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    postcode: Optional[str] = Field(None, max_length=20)
    api_endpoint: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class PlatformRead(BaseModel):
    """Response body for a single platform."""
    platform_id: int
    platform_name: str
    address: Optional[str] = None
    postcode: Optional[str] = None
    api_endpoint: Optional[str] = None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Seller
# ---------------------------------------------------------------------------

class SellerCreate(BaseModel):
    """POST /sellers request body."""
    store_name: str = Field(..., max_length=200)
    platform_id: Optional[int] = None
    platform_store_id: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    is_active: bool = True


class SellerUpdate(BaseModel):
    """PATCH /sellers/{id} request body."""
    store_name: Optional[str] = Field(None, max_length=200)
    platform_id: Optional[int] = None
    platform_store_id: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class SellerRead(BaseModel):
    """Response body for a single seller."""
    seller_id: int
    store_name: str
    platform_id: Optional[int] = None
    platform_store_id: Optional[str] = None
    company_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    # Nested
    platform: Optional[PlatformRead] = None
