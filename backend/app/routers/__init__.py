"""
WOMS API Routers Package

This package contains all API route handlers organized by domain:
- items: Item management endpoints
- warehouse: Warehouse and inventory endpoints
- orders: Order processing endpoints
- delivery: Delivery and driver endpoints
- users: User and authentication endpoints

Example usage in main.py:
    from app.routers import items, warehouse, orders, delivery, users
    
    app.include_router(items.router, prefix="/api/v1/items", tags=["Items"])
"""

# Routers will be imported here as they are implemented
# from app.routers import items
# from app.routers import warehouse
# from app.routers import orders
# from app.routers import delivery
# from app.routers import users
