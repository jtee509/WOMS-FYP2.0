"""
WOMS Delivery Router

CRUD endpoints for DeliveryTrip, Driver, and fleet management.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.delivery import DeliveryTrip, Driver
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.delivery import (
    DeliveryTripCreate,
    DeliveryTripRead,
    DeliveryTripUpdate,
    DriverCreate,
    DriverRead,
    DriverUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

@router.get("/drivers", response_model=PaginatedResponse[DriverRead])
async def list_drivers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None, description="Search by full_name"),
    session: AsyncSession = Depends(get_session),
):
    """List drivers with pagination and optional filters."""
    query = select(Driver)

    if warehouse_id is not None:
        query = query.where(Driver.warehouse_id == warehouse_id)
    if is_active is not None:
        query = query.where(Driver.is_active == is_active)
    if search:
        query = query.where(Driver.full_name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Driver.driver_id).offset(offset).limit(page_size)
    result = await session.execute(query)
    drivers = result.scalars().all()

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[_driver_to_read(d) for d in drivers],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/drivers/{driver_id}", response_model=DriverRead)
async def get_driver(
    driver_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single driver by ID."""
    driver = await session.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found")
    return _driver_to_read(driver)


@router.post("/drivers", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
async def create_driver(
    body: DriverCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new driver record."""
    driver = Driver(**body.model_dump())
    session.add(driver)
    await session.flush()
    await session.refresh(driver)
    return _driver_to_read(driver)


@router.patch("/drivers/{driver_id}", response_model=DriverRead)
async def update_driver(
    driver_id: int,
    body: DriverUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a driver. Only provided fields are changed."""
    driver = await session.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(driver, key, value)

    await session.flush()
    await session.refresh(driver)
    return _driver_to_read(driver)


# ---------------------------------------------------------------------------
# Delivery Trips
# ---------------------------------------------------------------------------

@router.get("/trips", response_model=PaginatedResponse[DeliveryTripRead])
async def list_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    trip_status: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """List delivery trips with pagination."""
    query = select(DeliveryTrip)

    if trip_status is not None:
        query = query.where(DeliveryTrip.trip_status == trip_status)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(DeliveryTrip.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    trips = result.scalars().all()

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[_trip_to_read(t) for t in trips],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/trips/{trip_id}", response_model=DeliveryTripRead)
async def get_trip(
    trip_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single delivery trip by ID."""
    trip = await session.get(DeliveryTrip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Delivery trip not found")
    return _trip_to_read(trip)


@router.post("/trips", response_model=DeliveryTripRead, status_code=status.HTTP_201_CREATED)
async def create_trip(
    body: DeliveryTripCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new delivery trip."""
    trip = DeliveryTrip(**body.model_dump())
    session.add(trip)
    await session.flush()
    await session.refresh(trip)
    return _trip_to_read(trip)


@router.patch("/trips/{trip_id}", response_model=DeliveryTripRead)
async def update_trip(
    trip_id: int,
    body: DeliveryTripUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a delivery trip. Only provided fields are changed."""
    trip = await session.get(DeliveryTrip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Delivery trip not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(trip, key, value)
    trip.updated_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(trip)
    return _trip_to_read(trip)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _driver_to_read(d: Driver) -> DriverRead:
    return DriverRead(
        driver_id=d.driver_id,
        full_name=d.full_name,
        phone_number=d.phone_number,
        warehouse_id=d.warehouse_id,
        user_id=d.user_id,
        role_id=d.role_id,
        firm_id=d.firm_id,
        is_active=d.is_active,
        created_at=d.created_at,
    )


def _trip_to_read(t: DeliveryTrip) -> DeliveryTripRead:
    return DeliveryTripRead(
        trip_id=t.trip_id,
        team_id=t.team_id,
        scheduled_start=t.scheduled_start,
        actual_start=t.actual_start,
        returned_date=t.returned_date,
        trip_status=t.trip_status,
        notes=t.notes,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )
