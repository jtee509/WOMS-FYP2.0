"""
WOMS Delivery Module Models

This module contains all delivery and driver-related models:
- CompanyFirm: Logistics/transport companies
- Lorry: Vehicles for delivery
- Driver: Driver records
- DriverCredential: Driver documents and licenses
- DriverTeam: Team composition (driver + vehicle)
- DeliveryTrip: Delivery trip records
- TripOrder: Orders assigned to trips
- DeliveryStatus: Delivery status lookup
- TrackingStatus: Order tracking status history
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB


# =============================================================================
# Company & Vehicle Tables
# =============================================================================

class CompanyFirm(SQLModel, table=True):
    """
    Logistics/transport company definitions.
    
    Can be internal fleet or third-party logistics providers.
    """
    __tablename__ = "company_firms"
    __table_args__ = (
        # GIN index on contact_info JSONB — enables phone/email/address queries
        Index("idx_company_contact_gin", "contact_info",
              postgresql_using="gin",
              postgresql_ops={"contact_info": "jsonb_path_ops"}),
    )

    firm_id: Optional[int] = Field(default=None, primary_key=True)
    firm_name: str = Field(max_length=200, unique=True, index=True)
    
    # Company registration
    roc: Optional[str] = Field(
        default=None, 
        max_length=50, 
        unique=True,
        description="Registration of Company number"
    )
    
    # JSONB for flexible contact information
    # Example: {"phone": "...", "email": "...", "address": "..."}
    contact_info: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Contact information in JSONB"
    )
    
    is_active: bool = Field(default=True, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    lorries: List["Lorry"] = Relationship(back_populates="firm")
    drivers: List["Driver"] = Relationship(back_populates="firm")


class Lorry(SQLModel, table=True):
    """
    Vehicle records for delivery fleet.
    """
    __tablename__ = "lorries"
    
    # Plate number as primary key (unique identifier)
    plate_number: str = Field(primary_key=True, max_length=20)
    
    warehouse_id: Optional[int] = Field(default=None, foreign_key="warehouse.id", index=True)
    firm_id: Optional[int] = Field(default=None, foreign_key="company_firms.firm_id", index=True)
    
    # Vehicle details
    vehicle_type: Optional[str] = Field(default=None, max_length=50)
    capacity_kg: Optional[float] = Field(default=None)
    
    is_active: bool = Field(default=True, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    warehouse: Optional["Warehouse"] = Relationship(back_populates="lorries")
    firm: Optional[CompanyFirm] = Relationship(back_populates="lorries")
    teams: List["DriverTeam"] = Relationship(back_populates="lorry")


# =============================================================================
# Driver Tables
# =============================================================================

class Driver(SQLModel, table=True):
    """
    Driver records.
    
    Links to user account and can be associated with a warehouse and firm.
    """
    __tablename__ = "drivers"
    
    driver_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Links to other entities
    warehouse_id: Optional[int] = Field(default=None, foreign_key="warehouse.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.user_id", index=True)
    role_id: Optional[int] = Field(default=None, foreign_key="roles.role_id", index=True)
    firm_id: Optional[int] = Field(default=None, foreign_key="company_firms.firm_id", index=True)
    
    # Driver information
    full_name: str = Field(max_length=200, index=True)
    phone_number: Optional[str] = Field(default=None, max_length=50)
    
    is_active: bool = Field(default=True, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    warehouse: Optional["Warehouse"] = Relationship(back_populates="drivers")
    user: Optional["User"] = Relationship(back_populates="driver")
    role: Optional["Role"] = Relationship(back_populates="drivers")
    firm: Optional[CompanyFirm] = Relationship(back_populates="drivers")
    credentials: List["DriverCredential"] = Relationship(back_populates="driver")
    teams: List["DriverTeam"] = Relationship(back_populates="driver")


class DriverCredential(SQLModel, table=True):
    """
    Driver credentials and documents.
    
    Tracks licenses, certifications, and their expiry dates.
    """
    __tablename__ = "driver_credentials"
    
    # Composite key: driver_id + credential_type
    driver_id: int = Field(foreign_key="drivers.driver_id", primary_key=True)
    credential_type: str = Field(max_length=50, primary_key=True)
    
    # Credential details
    credential_number: str = Field(max_length=100)
    expiry_date: Optional[date] = Field(default=None, index=True)
    
    # Document storage reference
    document_url: Optional[str] = Field(default=None, max_length=500)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    driver: Optional[Driver] = Relationship(back_populates="credentials")
    
    @property
    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if self.expiry_date is None:
            return False
        return self.expiry_date < date.today()


# =============================================================================
# Team & Trip Tables
# =============================================================================

class DriverTeam(SQLModel, table=True):
    """
    Driver team composition.
    
    Links drivers to vehicles for trip assignment.
    Also links to user account for access control.
    """
    __tablename__ = "driver_teams"
    
    team_id: Optional[int] = Field(default=None, primary_key=True)
    plate_number: str = Field(foreign_key="lorries.plate_number", index=True)
    driver_id: int = Field(foreign_key="drivers.driver_id", index=True)
    
    # Link to user account
    user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id",
        index=True,
        description="User account associated with this team assignment"
    )
    
    # Role in the team (e.g., "driver", "helper")
    team_role: Optional[str] = Field(default="driver", max_length=50)
    
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    lorry: Optional[Lorry] = Relationship(back_populates="teams")
    driver: Optional[Driver] = Relationship(back_populates="teams")
    trips: List["DeliveryTrip"] = Relationship(back_populates="team")
    user: Optional["User"] = Relationship(back_populates="driver_teams")


class DeliveryTrip(SQLModel, table=True):
    """
    Delivery trip records.
    
    A trip represents a driver's delivery route with multiple orders.
    """
    __tablename__ = "delivery_trips"
    __table_args__ = (
        # Composite: team + status — trip scheduling / dispatch queries
        Index("idx_delivery_trips_team_status", "team_id", "trip_status"),
    )

    trip_id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="driver_teams.team_id", index=True)
    
    # Trip timing
    scheduled_start: Optional[datetime] = Field(default=None)
    actual_start: Optional[datetime] = Field(default=None)
    returned_date: Optional[datetime] = Field(default=None)
    
    # Trip status
    trip_status: Optional[str] = Field(default="scheduled", max_length=50, index=True)
    
    # Trip notes
    notes: Optional[str] = Field(default=None, max_length=1000)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    team: Optional[DriverTeam] = Relationship(back_populates="trips")
    trip_orders: List["TripOrder"] = Relationship(back_populates="trip")


class TripOrder(SQLModel, table=True):
    """
    Orders assigned to a delivery trip.
    
    Links order details to trips with tracking number.
    """
    __tablename__ = "trips_orders"
    
    # Tracking number as primary key
    tracking_number: str = Field(primary_key=True, max_length=200)
    
    trip_id: int = Field(foreign_key="delivery_trips.trip_id", index=True)
    details_id: int = Field(foreign_key="order_details.detail_id", index=True)
    
    # Delivery sequence in the trip
    delivery_sequence: Optional[int] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    trip: Optional[DeliveryTrip] = Relationship(back_populates="trip_orders")
    order_detail: Optional["OrderDetail"] = Relationship(back_populates="trip_orders")
    tracking_statuses: List["TrackingStatus"] = Relationship(back_populates="trip_order")


# =============================================================================
# Delivery Status Tables
# =============================================================================

class DeliveryStatus(SQLModel, table=True):
    """
    Delivery status lookup table.
    
    Examples: Pending, In Transit, Out for Delivery, Delivered, Failed, Returned
    """
    __tablename__ = "delivery_status"
    
    status_id: Optional[int] = Field(default=None, primary_key=True)
    status_name: str = Field(max_length=100, unique=True, index=True)
    
    # Optional color for UI display
    status_color: Optional[str] = Field(default=None, max_length=20)
    
    # Relationships
    tracking_statuses: List["TrackingStatus"] = Relationship(back_populates="status")


class TrackingStatus(SQLModel, table=True):
    """
    Order tracking status history.
    
    Records status changes with timestamp and location.
    """
    __tablename__ = "tracking_status"
    __table_args__ = (
        # Composite: tracking_number + status_date — status history timeline
        Index("idx_tracking_status_history", "tracking_number", "status_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    tracking_number: str = Field(
        foreign_key="trips_orders.tracking_number", 
        index=True
    )
    warehouse_id: Optional[int] = Field(
        default=None, 
        foreign_key="warehouse.id",
        index=True
    )
    status_id: int = Field(foreign_key="delivery_status.status_id", index=True)
    
    # Status timestamp
    status_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Additional notes
    notes: Optional[str] = Field(default=None, max_length=500)
    
    # Relationships
    trip_order: Optional[TripOrder] = Relationship(back_populates="tracking_statuses")
    status: Optional[DeliveryStatus] = Relationship(back_populates="tracking_statuses")


# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.warehouse import Warehouse
    from app.models.users import User, Role
    from app.models.orders import OrderDetail
