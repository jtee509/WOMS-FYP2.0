"""
WOMS - Warehouse Order Management System
FastAPI Application Entry Point

This is the main entry point for the WOMS API.
It configures the FastAPI application with:
- CORS middleware
- Database lifecycle management
- API versioning
- Health check endpoints
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, check_db_connection


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize database, verify connection
    - Shutdown: Cleanup resources
    """
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    
    # Initialize database schema (optional - comment out if using Alembic)
    if settings.debug:
        try:
            await init_db()
            print("[OK] Database schema initialized")
        except Exception as e:
            print(f"[WARN] Database initialization skipped: {e}")

    # Verify database connection
    if await check_db_connection():
        print("[OK] Database connection verified")
    else:
        print("[WARN] Database connection failed - check your configuration")
    
    yield
    
    # Shutdown
    print(f"Shutting down {settings.app_name}")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## WOMS - Warehouse Order Management System API
    
    A comprehensive API for managing warehouse operations including:
    
    * **Items Management** - Products, variations, categories, brands
    * **Inventory Control** - Stock levels, locations, movements, lots
    * **Order Processing** - Orders, platforms, sellers, listings
    * **Delivery Management** - Drivers, trips, tracking, status
    * **User Administration** - Users, roles, audit logs
    
    ### Features
    - Full CRUD operations for all entities
    - JSONB-based version control snapshots
    - Multi-platform e-commerce integration ready
    - Comprehensive audit logging
    
    ### Documentation
    - **Swagger UI**: `/docs`
    - **ReDoc**: `/redoc`
    - **OpenAPI JSON**: `/openapi.json`
    """,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# =============================================================================
# Middleware Configuration
# =============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get(
    "/",
    tags=["Health"],
    summary="Root endpoint",
    response_class=JSONResponse,
)
async def root():
    """
    Root endpoint - returns API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    response_class=JSONResponse,
)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        - status: "healthy" or "unhealthy"
        - database: connection status
    """
    db_healthy = await check_db_connection()
    
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "version": settings.app_version,
        }
    )


@app.get(
    f"{settings.api_v1_prefix}/health",
    tags=["Health"],
    summary="API v1 Health check",
)
async def api_health():
    """
    API v1 health check endpoint.
    """
    return {
        "status": "healthy",
        "api_version": "v1",
        "app_version": settings.app_version,
    }


# =============================================================================
# API Routers
# =============================================================================

from app.routers import order_import as order_import_router
from app.routers import reference as reference_router
from app.routers import ml_sync as ml_sync_router

app.include_router(
    order_import_router.router,
    prefix=f"{settings.api_v1_prefix}/orders",
    tags=["Order Import"],
)

app.include_router(
    reference_router.router,
    prefix=f"{settings.api_v1_prefix}/reference",
    tags=["Reference Data"],
)

app.include_router(
    ml_sync_router.router,
    prefix=f"{settings.api_v1_prefix}/ml",
    tags=["ML Staging"],
)

# Future routers (uncomment as implemented):
# from app.routers import items, warehouse, orders, delivery, users
# app.include_router(items.router, prefix=f"{settings.api_v1_prefix}/items", tags=["Items"])
# app.include_router(warehouse.router, prefix=f"{settings.api_v1_prefix}/warehouse", tags=["Warehouse"])
# app.include_router(orders.router, prefix=f"{settings.api_v1_prefix}/orders", tags=["Orders"])
# app.include_router(delivery.router, prefix=f"{settings.api_v1_prefix}/delivery", tags=["Delivery"])
# app.include_router(users.router, prefix=f"{settings.api_v1_prefix}/users", tags=["Users"])


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
    )
