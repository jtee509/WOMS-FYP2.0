"""
WOMS Database Module

Provides database connection, session management, and schema initialization.
Uses SQLModel with async PostgreSQL support via asyncpg.
"""

import os
from pathlib import Path
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.config import settings
from app.models.triggers import apply_triggers
from app.models.views import apply_views
from app.models.seed import seed_database


# Project root (three levels above: backend/app/database.py → project root)
# SQL migrations are at backend/app/migrations/ (deprecated reference files only)
PROJECT_ROOT = Path(__file__).parent.parent.parent


# =============================================================================
# Database Engine Configuration
# =============================================================================

# Create async engine with connection pooling
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before use
    # Use NullPool for serverless/testing, otherwise use default pooling
    # poolclass=NullPool,
)

# Session factory for creating database sessions
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Database Session Dependency
# =============================================================================

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields an async session and ensures proper cleanup.
    
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    
    Usage:
        async with get_session_context() as session:
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Schema Initialization (One-Step Creation)
# =============================================================================

async def init_db() -> None:
    """
    Initialize database schema.
    
    Creates all tables defined in SQLModel models.
    This is the "one-step" schema creation function.
    
    IMPORTANT: Import all models before calling this function
    to ensure they are registered with SQLModel.metadata.
    
    Usage:
        from app.models import *  # Import all models
        await init_db()
    """
    # Import all models to register them with SQLModel.metadata
    # This ensures all tables are created
    from app.models import (
        # Items module
        Item, Status, ItemType, Category, Brand, BaseUOM, ItemsHistory,
        # Warehouse module
        Warehouse, InventoryLocation, InventoryType, InventoryTransaction,
        InventoryLevel, StockLot, InventoryMovement, MovementType,
        InventoryReplenishmentHistory, InventoryAlert, SellerWarehouse,
        # Orders module
        Platform, Seller, PlatformSKU, ListingComponent, CustomerPlatform,
        PlatformRawImport, CancellationReason, OrderCancellation, Order, OrderDetail,
        # Delivery module
        CompanyFirm, Lorry, Driver, DriverCredential, DriverTeam,
        DeliveryTrip, TripOrder, TrackingStatus, DeliveryStatus,
        # Users module
        ActionType, User, Role, AuditLog,
    )
    
    async with engine.begin() as conn:
        # Create the order_import PostgreSQL schema (required for OrderImportRaw/Staging tables)
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS order_import"))
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)

    print("[OK] Database schema initialized successfully")


async def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data! Use with caution.
    Only for development/testing purposes.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    print("[OK] All database tables dropped")


async def reset_db() -> None:
    """
    Reset database by dropping and recreating all tables.
    
    WARNING: This will delete all data! Use with caution.
    Only for development/testing purposes.
    """
    await drop_db()
    await init_db()
    print("[OK] Database reset complete")


# =============================================================================
# SQL Migrations (Triggers, Indexes, Views)
# =============================================================================

async def run_sql_file(sql_file: Path) -> None:
    """
    Execute a SQL file against the database.
    
    Handles multiple SQL statements by splitting on semicolons.
    Asyncpg doesn't support multiple statements in a single execute.
    
    Args:
        sql_file: Path to the SQL file to execute
    """
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file}")
    
    sql_content = sql_file.read_text(encoding='utf-8')
    
    # Split statements by semicolon, filter out empty ones and comments
    statements = []
    for stmt in sql_content.split(';'):
        # Remove comments and whitespace
        lines = []
        for line in stmt.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        clean_stmt = '\n'.join(lines).strip()
        if clean_stmt:
            statements.append(clean_stmt)
    
    async with engine.begin() as conn:
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[!] Statement failed: {stmt[:50]}... Error: {e}")
                raise
    
    print(f"[OK] Executed: {sql_file.name} ({len(statements)} statements)")


async def run_migrations() -> None:
    """
    Apply triggers, views, and seed data using the Python modules in app/models/.

    Previously this function executed the migrations/*.sql files directly.
    All SQL content has been converted to Python so the DB logic lives in one
    codebase and is applied automatically without external file dependencies.

    Execution order:
    1. apply_triggers() — CREATE OR REPLACE FUNCTION + trigger registrations
    2. apply_views()    — CREATE OR REPLACE VIEW for all reporting views
    3. seed_database()  — INSERT … ON CONFLICT DO NOTHING for lookup tables

    All operations are idempotent: safe to call on any live database.
    """
    print("\nRunning DB post-init steps (triggers / views / seed)...")

    async with engine.begin() as conn:
        await apply_triggers(conn)
        await apply_views(conn)

    async with async_session_maker() as session:
        await seed_database(session)

    print("All post-init steps complete.\n")


async def init_db_full() -> None:
    """
    Full database initialization: schema + triggers + indexes + views.
    
    This is the "one-step" complete setup function that:
    1. Creates all tables from SQLModel models
    2. Runs all SQL migrations (triggers, indexes, views)
    
    Usage:
        await init_db_full()
    
    Or from command line:
        python -c "import asyncio; from app.database import init_db_full; asyncio.run(init_db_full())"
    """
    await init_db()
    await run_migrations()
    print("[OK] Full database initialization complete")


async def reset_db_full() -> None:
    """
    Full database reset: drop everything and reinitialize.
    
    WARNING: This will delete all data! Use with caution.
    
    This:
    1. Drops all tables
    2. Recreates all tables
    3. Runs all SQL migrations
    """
    await drop_db()
    await init_db()
    await run_migrations()
    print("[OK] Full database reset complete")


# =============================================================================
# Health Check
# =============================================================================

async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
