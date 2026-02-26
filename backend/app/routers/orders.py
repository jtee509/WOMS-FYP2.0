"""
WOMS Orders Router

CRUD endpoints for the Orders domain (Order + OrderDetail).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies.auth import require_current_user
from app.models.orders import Order, OrderDetail
from app.models.users import User
from app.schemas.common import PaginatedResponse
from app.schemas.orders import (
    OrderCreate,
    OrderDetailRead,
    OrderDetailUpdate,
    OrderListItem,
    OrderRead,
    OrderUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Order list + get
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse[OrderListItem])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform_id: int | None = Query(None),
    store_id: int | None = Query(None),
    order_status: str | None = Query(None),
    search: str | None = Query(None, description="Search by platform_order_id or recipient_name"),
    session: AsyncSession = Depends(get_session),
):
    """List orders with pagination and optional filters."""
    query = select(Order)

    if platform_id is not None:
        query = query.where(Order.platform_id == platform_id)
    if store_id is not None:
        query = query.where(Order.store_id == store_id)
    if order_status is not None:
        query = query.where(Order.order_status == order_status)
    if search:
        query = query.where(
            (Order.platform_order_id.ilike(f"%{search}%"))
            | (Order.recipient_name.ilike(f"%{search}%"))
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Order.order_date.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    orders = result.scalars().all()

    pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[
            OrderListItem(
                order_id=o.order_id,
                store_id=o.store_id,
                platform_id=o.platform_id,
                platform_order_id=o.platform_order_id,
                assigned_warehouse_id=o.assigned_warehouse_id,
                recipient_name=o.recipient_name,
                order_status=o.order_status,
                cancellation_status=o.cancellation_status,
                order_date=o.order_date,
                created_at=o.created_at,
            )
            for o in orders
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a single order with all details."""
    query = (
        select(Order)
        .where(Order.order_id == order_id)
        .options(selectinload(Order.details))
    )
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_to_read(order)


# ---------------------------------------------------------------------------
# Order create + update
# ---------------------------------------------------------------------------

@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Create a new order with optional line items."""
    details_data = body.details
    order_data = body.model_dump(exclude={"details"})

    if order_data.get("order_date") is None:
        order_data["order_date"] = datetime.now(timezone.utc)

    order = Order(**order_data)
    session.add(order)
    await session.flush()  # get order_id

    for d in details_data:
        detail = OrderDetail(order_id=order.order_id, **d.model_dump())
        session.add(detail)

    await session.flush()
    await session.refresh(order)

    # Reload with details
    query = (
        select(Order)
        .where(Order.order_id == order.order_id)
        .options(selectinload(Order.details))
    )
    result = await session.execute(query)
    order = result.scalar_one()
    return _order_to_read(order)


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: int,
    body: OrderUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update an order. Only provided fields are changed."""
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    order.updated_at = datetime.now(timezone.utc)

    await session.flush()

    # Reload with details
    query = (
        select(Order)
        .where(Order.order_id == order.order_id)
        .options(selectinload(Order.details))
    )
    result = await session.execute(query)
    order = result.scalar_one()
    return _order_to_read(order)


# ---------------------------------------------------------------------------
# Order Detail update
# ---------------------------------------------------------------------------

@router.patch("/{order_id}/details/{detail_id}", response_model=OrderDetailRead)
async def update_order_detail(
    order_id: int,
    detail_id: int,
    body: OrderDetailUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    """Update a single order line item."""
    query = select(OrderDetail).where(
        OrderDetail.detail_id == detail_id,
        OrderDetail.order_id == order_id,
    )
    result = await session.execute(query)
    detail = result.scalar_one_or_none()
    if detail is None:
        raise HTTPException(status_code=404, detail="Order detail not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(detail, key, value)
    detail.updated_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(detail)
    return _detail_to_read(detail)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detail_to_read(d: OrderDetail) -> OrderDetailRead:
    return OrderDetailRead(
        detail_id=d.detail_id,
        order_id=d.order_id,
        platform_sku_data=d.platform_sku_data,
        resolved_item_id=d.resolved_item_id,
        paid_amount=d.paid_amount,
        shipping_fee=d.shipping_fee,
        discount=d.discount,
        courier_type=d.courier_type,
        tracking_number=d.tracking_number,
        tracking_source=d.tracking_source,
        quantity=d.quantity,
        fulfillment_status=d.fulfillment_status,
        is_cancelled=d.is_cancelled,
        cancelled_quantity=d.cancelled_quantity,
        return_status=d.return_status,
        returned_quantity=d.returned_quantity,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _order_to_read(o: Order) -> OrderRead:
    return OrderRead(
        order_id=o.order_id,
        store_id=o.store_id,
        platform_id=o.platform_id,
        platform_order_id=o.platform_order_id,
        assigned_warehouse_id=o.assigned_warehouse_id,
        raw_import_id=o.raw_import_id,
        phone_number=o.phone_number,
        recipient_name=o.recipient_name,
        shipping_address=o.shipping_address,
        shipping_postcode=o.shipping_postcode,
        shipping_state=o.shipping_state,
        country=o.country,
        billing_address=o.billing_address,
        platform_raw_data=o.platform_raw_data,
        order_status=o.order_status,
        cancellation_status=o.cancellation_status,
        cancelled_at=o.cancelled_at,
        order_date=o.order_date,
        created_at=o.created_at,
        updated_at=o.updated_at,
        details=[_detail_to_read(d) for d in (o.details or [])],
    )
