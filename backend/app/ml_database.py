"""
WOMS ML Staging Database

Separate async engine and session factory for ml_woms_db — an isolated
PostgreSQL database used for ML model training and inference.

ml_woms_db uses the same SQLModel schema as woms_db. Data is copied
into it via the /api/v1/ml/sync endpoint so ML workloads never touch
the production database.

Usage:
    from app.ml_database import get_ml_session, init_ml_db
"""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from app.config import settings


# =============================================================================
# ML Database Engine
# =============================================================================

ml_engine = create_async_engine(
    settings.async_ml_database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
)

ml_session_maker = async_sessionmaker(
    ml_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Session Dependency
# =============================================================================

async def get_ml_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for ML database sessions.

    Usage:
        @router.post("/ml/sync")
        async def sync(ml_session: AsyncSession = Depends(get_ml_session)):
            ...
    """
    async with ml_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# ML DB Initialization
# =============================================================================

async def init_ml_db() -> None:
    """
    Create all tables in ml_woms_db using the shared SQLModel metadata.

    Creates the order_import PostgreSQL schema first (required for
    OrderImportRaw and OrderImportStaging), then runs create_all().

    This is a one-time setup operation — safe to re-run (CREATE IF NOT EXISTS).

    Usage:
        python -c "
        import asyncio
        from app.ml_database import init_ml_db
        asyncio.run(init_ml_db())
        "
    """
    # Import all models so SQLModel.metadata has every table registered
    from app.models import (
        Item, Status, ItemType, Category, Brand, BaseUOM, ItemsHistory,
        Warehouse, InventoryLocation, InventoryType, InventoryTransaction,
        InventoryLevel, StockLot, InventoryMovement, MovementType,
        InventoryReplenishmentHistory, InventoryAlert, SellerWarehouse,
        Platform, Seller, PlatformSKU, ListingComponent, CustomerPlatform,
        PlatformRawImport, CancellationReason, OrderCancellation, Order, OrderDetail,
        CompanyFirm, Lorry, Driver, DriverCredential, DriverTeam,
        DeliveryTrip, TripOrder, TrackingStatus, DeliveryStatus,
        ActionType, User, Role, AuditLog,
        OrderImportRaw, OrderImportStaging,
    )

    async with ml_engine.begin() as conn:
        # Create the order_import PostgreSQL schema (required for the import tables)
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS order_import"))
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)

    print("[OK] ML database schema initialized (ml_woms_db)")


async def check_ml_db_connection() -> bool:
    """Check if the ML database connection is healthy."""
    try:
        async with ml_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"ML database connection failed: {e}")
        return False
