"""
WOMS Delivery Schemas

Request/response models for DeliveryTrip, Driver, and fleet management endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Company / Firm
# ---------------------------------------------------------------------------

class CompanyFirmRead(BaseModel):
    """Response body for a logistics company."""
    firm_id: int
    firm_name: str
    roc: Optional[str] = None
    contact_info: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

class DriverCreate(BaseModel):
    """POST /drivers request body."""
    full_name: str = Field(..., max_length=200)
    phone_number: Optional[str] = Field(None, max_length=50)
    warehouse_id: Optional[int] = None
    firm_id: Optional[int] = None
    user_id: Optional[int] = None
    role_id: Optional[int] = None
    is_active: bool = True


class DriverUpdate(BaseModel):
    """PATCH /drivers/{id} request body."""
    full_name: Optional[str] = Field(None, max_length=200)
    phone_number: Optional[str] = Field(None, max_length=50)
    warehouse_id: Optional[int] = None
    firm_id: Optional[int] = None
    is_active: Optional[bool] = None


class DriverRead(BaseModel):
    """Response body for a driver."""
    driver_id: int
    full_name: str
    phone_number: Optional[str] = None
    warehouse_id: Optional[int] = None
    user_id: Optional[int] = None
    role_id: Optional[int] = None
    firm_id: Optional[int] = None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Delivery Trip
# ---------------------------------------------------------------------------

class DeliveryTripCreate(BaseModel):
    """POST /delivery/trips request body."""
    team_id: int
    scheduled_start: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)


class DeliveryTripUpdate(BaseModel):
    """PATCH /delivery/trips/{id} request body."""
    scheduled_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    returned_date: Optional[datetime] = None
    trip_status: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)


class DeliveryTripRead(BaseModel):
    """Response body for a delivery trip."""
    trip_id: int
    team_id: int
    scheduled_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    returned_date: Optional[datetime] = None
    trip_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
