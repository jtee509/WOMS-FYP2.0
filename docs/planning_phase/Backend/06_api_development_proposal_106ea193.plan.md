---
name: API Development Proposal
overview: A proposal to restructure the WOMS backend API and database layer to reduce confusing naming, clarify domain boundaries, and establish a consistent API development pattern.
todos: []
isProject: false
---

# API Development Proposal for WOMS Backend

## Problem Statement

The current backend creates confusion through:

1. **Overlapping "raw import" concepts** – `PlatformRawImport` (table: `platform_raw_imports`) vs `OrderImportRaw` (table: `order_import.order_import_raw`) both store raw platform data but serve different architectural roles that are not documented
2. **Monolithic model files** – [app/models/orders.py](backend/app/models/orders.py) mixes Platform, Seller, PlatformRawImport, PlatformSKU, Order, OrderDetail, CancellationReason, OrderCancellation (10 models in one 740-line file)
3. **Inconsistent API path semantics** – `order_import` router lives under `/api/v1/orders` but handles import, not order CRUD; "orders" implies main order endpoints
4. **Sparse schema layer** – [app/schemas/\_\_init\_\_.py](backend/app/schemas/__init__.py) is empty; no Pydantic schemas for request/response validation
5. **No authentication** – JWT config exists in [app/config.py](backend/app/config.py) (lines 114-126) but no auth middleware, login endpoint, or user dependency injection. 12+ FK fields across models reference `*_by_user_id` and cannot be populated without auth.
6. **Migration naming** – Long hashes (`c4d5e6f7a8b9`, `ff701cb6b558`) in filenames make it hard to infer purpose at a glance

---

## Proposed Structure

### 1. Flat API Layout

Organize API by **domain** using flat paths. Use OpenAPI tags for logical grouping in Swagger docs rather than URL nesting.

> **Note:** Flat paths match the existing stubs already commented out in `main.py:207-211`. This avoids redesigning paths that are already planned.

```mermaid
flowchart TB
    subgraph api [API v1]
        subgraph auth [Auth]
            Login[/auth/login]
            Register[/auth/register]
            Refresh[/auth/refresh]
        end

        subgraph items_domain [Items]
            Items[/items]
            Categories[/categories]
        end

        subgraph marketplace [Marketplace]
            Platforms[/platforms]
            Sellers[/sellers]
        end

        subgraph orders [Orders]
            OrdersCRUD[/orders]
            OrderDetails[/orders/:id/details]
            Import[/orders/import]
            Returns[/orders/returns]
            Exchanges[/orders/exchanges]
            Modifications[/orders/modifications]
        end

        subgraph warehouse [Warehouse]
            Warehouses[/warehouses]
            Inventory[/inventory]
        end

        subgraph delivery [Delivery]
            Trips[/delivery/trips]
            Drivers[/drivers]
        end

        subgraph users_domain [Users]
            Users[/users]
        end
    end
```

**Proposed path layout:**

| Path                       | Purpose                                | Status       |
| -------------------------- | -------------------------------------- | ------------ |
| `/api/v1/auth/login`       | JWT login (returns access + refresh)   | To implement |
| `/api/v1/auth/register`    | User registration                      | To implement |
| `/api/v1/auth/refresh`     | Refresh access token                   | To implement |
| `/api/v1/items`            | Item CRUD                              | To implement |
| `/api/v1/categories`       | Category CRUD                          | To implement |
| `/api/v1/platforms`        | Platform CRUD                          | To implement |
| `/api/v1/sellers`          | Seller CRUD                            | To implement |
| `/api/v1/orders`           | Order CRUD (list, get, create, update) | To implement |
| `/api/v1/orders/import`    | File upload → order_import schema      | Exists       |
| `/api/v1/orders/returns`   | Return workflow                        | To implement |
| `/api/v1/orders/exchanges` | Exchange workflow                      | To implement |
| `/api/v1/warehouses`       | Warehouse CRUD                         | To implement |
| `/api/v1/inventory`        | Stock levels, movements                | To implement |
| `/api/v1/delivery/trips`   | Delivery trips                         | To implement |
| `/api/v1/drivers`          | Driver management                      | To implement |
| `/api/v1/users`            | User management                        | To implement |
| `/api/v1/reference/load-*` | Bulk load (platforms, sellers, items)  | Exists       |
| `/api/v1/ml/*`             | ML sync                                | Exists       |

---

### 2. Naming Clarification: Raw Import Tables

These two tables are **not duplicates** — they serve distinct architectural roles:

| Table                               | Role                        | Mutable? | FK to orders?                          | Used by                       |
| ----------------------------------- | --------------------------- | -------- | -------------------------------------- | ----------------------------- |
| `platform_raw_imports`              | **Processing/linkage table** — raw data with `status` workflow field + `normalized_order_id` FK back to `orders` | Yes (status updates) | Yes — `Order.raw_import_id` points here | Future order normalization flow |
| `order_import.order_import_raw`     | **Immutable audit log** — exact copy of what was uploaded, never modified | No       | No                                     | Import pipeline (current)      |
| `order_import.order_import_staging` | Parsed/cleaned staging data for mapping to orders | Yes      | No                                     | Import pipeline (current)      |

**Recommendation:** Keep both tables. Add cross-referencing docstrings to both model classes:
- In `PlatformRawImport`: "Processing table with status workflow. See also `order_import.order_import_raw` for the immutable audit log of uploads."
- In `OrderImportRaw`: "Immutable audit record. See also `platform_raw_imports` for the processing/linkage table with status tracking."

> **Important:** Do NOT deprecate `platform_raw_imports` — `Order.raw_import_id` FK depends on it.

---

### 3. Authentication & Authorization

**Why this is needed:** 12+ FK fields across models reference `*_by_user_id` (e.g. `cancelled_by_user_id` on Order, `initiated_by_user_id` on OrderReturn, `changed_by_user_id` on AuditLog). Without authentication, new CRUD endpoints cannot populate these fields and audit logging is impossible.

**Existing infrastructure** (already in codebase):
- `config.py:114-126` — `secret_key` (auto-generated), `algorithm` (HS256), `access_token_expire_minutes` (30), `refresh_token_expire_days` (7)
- `models/users.py` — `User` (with `password_hash`, `is_superuser`, `is_active`), `Role` (with JSONB `permissions`), `AuditLog`
- `main.py:211` — commented-out `users` router at `/api/v1/users`
- `requirements.txt` — `python-jose[cryptography]`, `passlib[bcrypt]`, `bcrypt` already listed

**New components to create:**

```
app/auth/
├── __init__.py
├── jwt.py            # create_access_token(), create_refresh_token(), decode_token()
├── password.py       # hash_password(), verify_password() using passlib/bcrypt
└── dependencies.py   # get_current_user() → FastAPI Depends(), get_current_active_user()
```

**Auth router:**

```python
# routers/auth.py
@router.post("/auth/login")       # → Token (access_token + refresh_token + token_type)
@router.post("/auth/register")    # → UserRead
@router.post("/auth/refresh")     # → Token (new access_token from refresh_token)
```

**Mounting in main.py:**

```python
app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{prefix}/users", tags=["Users"])
```

---

### 4. Model File Reorganization

Split [app/models/orders.py](backend/app/models/orders.py) (740 lines, 10 models) by domain:

| New File                        | Models                                                                    | Rationale                                    |
| ------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------- |
| `models/platform.py`            | Platform, Seller, PlatformSKU, ListingComponent, CustomerPlatform         | Marketplace concepts; Seller FK → Platform   |
| `models/orders.py`              | PlatformRawImport, Order, OrderDetail                                     | Core order entities + processing linkage     |
| `models/order_cancellations.py` | CancellationReason, OrderCancellation                                     | Or merge into order_operations               |
| `models/order_import.py`        | OrderImportRaw, OrderImportStaging                                        | Already separate                             |
| `models/order_operations.py`    | ReturnReason, OrderReturn, ExchangeReason, OrderExchange, OrderModification, OrderPriceAdjustment | Already separate            |

> **Note on `warehouse.py`:** At 483 lines with 11 models, `warehouse.py` is comparable in size to `orders.py`. If the model split proves valuable, consider splitting it into `warehouse.py` (Warehouse, InventoryType, InventoryLocation, SellerWarehouse) and `inventory.py` (MovementType, InventoryMovement, InventoryTransaction, StockLot, InventoryLevel, InventoryReplenishmentHistory, InventoryAlert) in a future pass.

#### Circular Import Resolution

Splitting `orders.py` requires care due to FK cross-dependencies:
- `PlatformRawImport` (in `orders.py`) has FK to `orders.order_id`
- `Order` (in `orders.py`) has FK to `platform.platform_id` and `seller.seller_id` (in `platform.py`)

**Solution** (already used in the codebase at `orders.py:730-740`):
1. Use **string-based FK refs**: `foreign_key="platform.platform_id"` — SQLAlchemy resolves these at runtime, no Python import needed
2. Use **`TYPE_CHECKING` blocks** for type hints: `if TYPE_CHECKING: from .platform import Platform`
3. **Import order in `models/__init__.py` matters**: import `platform.py` before `orders.py` so that all table metadata is registered before relationship resolution

---

### 5. Schema (Pydantic) Layer

Create schemas as flat files mirroring the model structure:

```
app/schemas/
├── __init__.py
├── common.py            # PaginatedResponse[T], ErrorResponse, ErrorDetail
├── items.py             # ItemCreate, ItemRead, ItemUpdate
├── orders.py            # OrderCreate, OrderRead, OrderList
├── order_import.py      # ImportResultRead (convert existing dataclass)
├── order_operations.py  # ReturnCreate, ExchangeCreate
├── platform.py          # PlatformRead, SellerRead
├── warehouse.py         # WarehouseRead, InventoryLevelRead
├── delivery.py          # TripCreate, TripRead, DriverRead
└── users.py             # UserCreate, UserRead, Token, TokenData
```

**Naming convention:** `{Entity}Create`, `{Entity}Read`, `{Entity}Update`, `{Entity}List` (for list responses with pagination).

#### Existing dataclasses to convert

These already exist and should be converted to Pydantic `BaseModel` (or thin wrappers created):

| Existing | Location | Action |
|----------|----------|--------|
| `ImportResult` (dataclass) | `services/order_import/importer.py` | Convert to `schemas/order_import.py::ImportResultRead` |
| `SyncRequest` (Pydantic) | `services/ml_sync/sync.py` | Already Pydantic — move to `schemas/ml_sync.py` or reuse as-is |
| `SyncResult` (dataclass) | `services/ml_sync/sync.py` | Convert to `schemas/ml_sync.py::SyncResultRead` |

#### Standard response formats

Define in `schemas/common.py` for frontend (React + MUI + axios) consistency:

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

> **Note:** All three existing routers raise `HTTPException` with bare `detail` strings. New endpoints should return structured `ErrorResponse` for consistent frontend error handling.

---

### 6. Router Organization

```
app/routers/
├── __init__.py
├── auth.py            # Login, register, refresh (NEW)
├── items.py           # Item CRUD
├── platform.py        # Platform + Seller CRUD
├── orders.py          # Order CRUD
├── order_import.py    # POST /import (keep; mount under orders) (existing)
├── order_operations.py # Returns, exchanges, modifications
├── warehouse.py       # Warehouse + inventory
├── delivery.py        # Trips, drivers
├── users.py           # User management
├── reference.py       # Bulk load (existing)
└── ml_sync.py         # ML (existing)
```

**Mounting in main.py:**

```python
# Authentication
app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Authentication"])

# Orders domain: CRUD + import + operations
app.include_router(orders.router, prefix=f"{prefix}/orders", tags=["Orders"])
app.include_router(order_import.router, prefix=f"{prefix}/orders", tags=["Order Import"])
app.include_router(order_operations.router, prefix=f"{prefix}/orders", tags=["Order Operations"])

# Other domains
app.include_router(items.router, prefix=f"{prefix}/items", tags=["Items"])
app.include_router(platform.router, prefix=f"{prefix}/platforms", tags=["Platforms"])
app.include_router(warehouse.router, prefix=f"{prefix}/warehouse", tags=["Warehouse"])
app.include_router(delivery.router, prefix=f"{prefix}/delivery", tags=["Delivery"])
app.include_router(users.router, prefix=f"{prefix}/users", tags=["Users"])
```

---

### 7. Migration Naming Convention

Use descriptive suffixes instead of opaque hashes:

| Current                                                       | Proposed                                           |
| ------------------------------------------------------------- | -------------------------------------------------- |
| `20260220_1600_00_c4d5e6f7a8b9_create_order_import_schema.py` | `20260220_1600_create_order_import_schema.py`      |
| `20260131_0753_23_ff701cb6b558_remove_tracking_...`           | `20260131_0753_remove_tracking_add_action_type.py` |

**Pattern:** `YYYYMMDD_HHMM_description_snake_case.py` – drop the revision hash and seconds from the filename (keep `revision` variable inside the file for Alembic).

**Implementation** — change `backend/alembic.ini` line 9:

```ini
# Current:
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(rev)s_%%(slug)s

# Proposed:
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(slug)s
```

> **Note:** Existing migration files do NOT need renaming — Alembic uses the `revision` variable inside each file, not the filename. This change only affects newly generated migrations.

---

### 8. Implementation Phases

| Phase | Focus | Effort | Details |
|-------|-------|--------|---------|
| **1** | Documentation + naming | 1-2 days | Docstrings for raw import tables, `alembic.ini` template fix, document domain boundaries in `database_structure.md` |
| **2** | Schemas for existing endpoints | 1-2 days | Convert `ImportResult`/`SyncResult` to Pydantic, add `response_model=` to 3 existing routers, create `common.py` |
| **3** | Authentication | 3-5 days | `app/auth/` package, `routers/auth.py`, `schemas/users.py`, `get_current_user` dependency |
| **4** | Order CRUD | 3-5 days | `routers/orders.py`, `schemas/orders.py` — depends on auth for `*_by_user_id` fields |
| **5** | Supporting CRUD APIs | 5-7 days | Items, Platforms/Sellers, Warehouse, Delivery — build as needed |
| **6** | Model file split (optional) | 1-2 days | `orders.py` → `platform.py` + `orders.py`; only valuable with multiple active contributors |

**Phase 1 – Documentation + naming (low risk)**

- Add docstrings to `PlatformRawImport` and `OrderImportRaw` clarifying their distinct roles
- Document domain boundaries in `database_structure.md`
- Update `alembic.ini` `file_template` for future migrations
- No code behaviour changes

**Phase 2 – Schemas for existing endpoints**

- Create `app/schemas/common.py` with `PaginatedResponse`, `ErrorResponse`
- Convert `ImportResult` dataclass → `schemas/order_import.py::ImportResultRead`
- Add `response_model=` to existing routers (order_import, reference, ml_sync)
- Immediate improvement to Swagger documentation

**Phase 3 – Authentication (prerequisite for CRUD)**

- Create `app/auth/` package (jwt.py, password.py, dependencies.py)
- Create `routers/auth.py` (login, register, refresh)
- Create `schemas/users.py` (UserCreate, UserRead, Token, TokenData)
- Add optional `get_current_user` dependency — existing endpoints remain unprotected initially

**Phase 4 – Order CRUD**

- Implement `routers/orders.py` (GET, POST, GET/:id, PATCH/:id)
- Create `schemas/orders.py` (OrderCreate, OrderRead, OrderList)
- Integrate with `get_current_user` for audit fields
- Mount at `/api/v1/orders` alongside existing order_import router

**Phase 5 – Supporting CRUD APIs**

- Items CRUD (`/api/v1/items`)
- Platform + Seller CRUD (`/api/v1/platforms`, `/api/v1/sellers`)
- Warehouse CRUD (`/api/v1/warehouse`)
- Delivery CRUD (`/api/v1/delivery`)
- Build incrementally as frontend or integration needs arise

**Phase 6 – Model file split (optional)**

- Split `orders.py` into `platform.py` + `orders.py`
- Use string-based FK refs + `TYPE_CHECKING` blocks (already in codebase)
- Update `models/__init__.py` import order
- Run `alembic check` to verify no migration drift
- Only valuable when multiple developers are editing models simultaneously

---

### 9. Quick Reference: Current vs Proposed

| Area              | Current                                    | Proposed                                        |
| ----------------- | ------------------------------------------ | ----------------------------------------------- |
| Authentication    | JWT config exists, no implementation       | Full auth: login, register, refresh, dependency  |
| Order import path | `/api/v1/orders/import`                    | Same; `/orders` will also serve CRUD             |
| API paths         | 3 routers, 7 endpoints                     | Flat paths: `/items`, `/platforms`, `/orders`, etc. |
| Raw import tables | 2 tables, roles undocumented               | Keep both; document distinct roles (processing vs audit) |
| orders.py size    | 10 models, 740 lines                       | Split into platform.py + orders.py               |
| Schemas           | Empty                                      | Flat files: Create/Read/Update per domain        |
| Error responses   | Bare `HTTPException` strings               | Structured `ErrorResponse` for frontend          |
| Migration names   | Hash + seconds in filename                 | Descriptive only (`alembic.ini` change)          |

---

### 10. How It Works with the Current Structure

The proposal is **additive** – it extends the current structure without breaking existing behaviour. This section explains how the proposal maps to what exists today.

#### Current Request Flow (Order Import)

```
POST /api/v1/orders/import
    │
    ├─► main.py: order_import_router mounted at prefix="/api/v1/orders"
    │
    ├─► routers/order_import.py: @router.post("/import")
    │       └─► Depends(get_session) → database session
    │       └─► import_excel_file() from services.order_import
    │
    ├─► services/order_import/
    │       ├─ parser.py   → parse Excel/CSV
    │       ├─ cleaner.py  → normalize dates, encoding
    │       ├─ mapper.py   → map to staging schema
    │       └─ importer.py → insert into order_import_raw + order_import_staging
    │
    └─► models/order_import.py
            ├─ OrderImportRaw   → order_import.order_import_raw
            └─ OrderImportStaging → order_import.order_import_staging
```

**Proposal impact:** None. This flow stays unchanged.

#### Component Mapping

| Current Component | Proposal Change | Effect |
|-------------------|-----------------|--------|
| main.py | Add auth + CRUD routers | order_import stays; new routers added alongside |
| routers/order_import.py | No change | Still POST /import; still mounted at /api/v1/orders |
| services/order_import/ | No change | Parser → cleaner → mapper → importer pipeline unchanged |
| models/order_import.py | No change | OrderImportRaw, OrderImportStaging unchanged |
| models/orders.py | Optional split | Split into platform.py + orders.py; update models/__init__.py imports |
| schemas/ | Add schemas | Currently empty; add flat schema files for validation |
| (new) app/auth/ | Create auth package | JWT, password hashing, user dependency |

#### Current vs Proposed API Surface

**Current:**

```
/api/v1/orders/import     ← only order-related endpoint
/api/v1/reference/load-*  ← bulk load
/api/v1/ml/*              ← ML sync
/health                   ← health checks
```

**Proposed (additive):**

```
/api/v1/auth/*            ← NEW: login, register, refresh
/api/v1/orders            ← NEW: GET, POST (order CRUD)
/api/v1/orders/import     ← UNCHANGED
/api/v1/orders/returns    ← NEW: return workflow
/api/v1/orders/exchanges  ← NEW: exchange workflow
/api/v1/items             ← NEW (future)
/api/v1/platforms         ← NEW (future)
/api/v1/sellers           ← NEW (future)
/api/v1/warehouses        ← NEW (future)
/api/v1/delivery/*        ← NEW (future)
/api/v1/users             ← NEW (future)
/api/v1/reference/load-*  ← UNCHANGED
/api/v1/ml/*              ← UNCHANGED
```

#### Router Mounting in main.py

**Current:**

```python
app.include_router(order_import_router.router, prefix=f"{settings.api_v1_prefix}/orders", tags=["Order Import"])
app.include_router(reference_router.router, prefix=f"{settings.api_v1_prefix}/reference", tags=["Reference Data"])
app.include_router(ml_sync_router.router, prefix=f"{settings.api_v1_prefix}/ml", tags=["ML Staging"])
```

**Proposed:**

```python
# Authentication (Phase 3)
app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Authentication"])

# Orders domain (Phase 4): CRUD + import + operations
app.include_router(orders.router, prefix=f"{prefix}/orders", tags=["Orders"])
app.include_router(order_import.router, prefix=f"{prefix}/orders", tags=["Order Import"])       # SAME
app.include_router(order_operations.router, prefix=f"{prefix}/orders", tags=["Order Operations"])

# Existing
app.include_router(reference.router, prefix=f"{prefix}/reference", tags=["Reference Data"])     # SAME
app.include_router(ml_sync.router, prefix=f"{prefix}/ml", tags=["ML Staging"])                  # SAME
```

#### Schema Layer Addition

**Current:** order_import returns a plain dict. `ImportResult` exists as a `@dataclass` in `services/order_import/importer.py`. `SyncRequest` in `services/ml_sync/sync.py` is already a Pydantic model.

**Proposed:** Convert existing dataclasses to Pydantic and add `response_model`:

```python
# schemas/order_import.py — convert from existing @dataclass in importer.py
class ImportResultRead(BaseModel):
    platform: str
    seller_id: int
    filename: str
    import_batch_id: str
    total_rows: int
    success_rows: int
    skipped_rows: int
    error_rows: int
    errors: list[str]

# In router:
@router.post("/import", response_model=ImportResultRead)
async def import_orders(...):
```

The endpoint logic stays the same; only the response type becomes explicit and validated.

#### Compatibility Summary

| Aspect | Compatibility |
|--------|---------------|
| Import flow | Unchanged; same path, router, service, models |
| Database | No migrations needed for Phases 1-3 (documentation, schemas, auth uses existing User table) |
| New routers | Additive; mounted alongside existing ones |
| Model split | Optional; can be done later (Phase 6) |
| Schemas | Additive; improves validation and docs without changing behaviour |
| Auth | Only prerequisite change; existing endpoints remain unprotected until opted in |

The proposal is designed to extend the current structure, not replace it. Existing behaviour stays; new behaviour is added in a consistent way.

---

## Summary

The proposal improves the WOMS backend through six incremental changes: (1) documenting the distinct roles of `platform_raw_imports` vs `order_import_raw`, (2) building an authentication foundation using the existing JWT config and User model, (3) organizing flat API paths matching the existing `main.py` stubs, (4) adding a Pydantic schema layer for request/response validation, (5) optionally splitting the 740-line `orders.py` model file by domain, and (6) simplifying migration filenames via an `alembic.ini` template change. Phases 1-2 are low-risk and provide immediate value; Phase 3 (auth) is the critical prerequisite for all new CRUD endpoints.
