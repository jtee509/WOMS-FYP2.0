# WOMS Web API Documentation

All API endpoints are documented here. When creating or modifying an API, update this file with the endpoint details, request/response format, and which files were changed.

**Base URL:** `http://localhost:8000`
**API Prefix:** `/api/v1`

---

## Authentication

### `POST /api/v1/auth/login`

**Description:** Authenticate a user with email and password. Returns a JWT access token (valid 30 minutes).
**Files:** `backend/app/routers/auth.py`, `backend/app/services/auth.py`, `backend/app/schemas/auth.py`
**Tags:** Authentication

**Request:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string (EmailStr) | Yes | User's email address |
| `password` | string | Yes | Plaintext password |

```json
{
  "email": "admin@admin.com",
  "password": "Admin123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "admin",
  "email": "admin@admin.com",
  "role": "Admin"
}
```

**Error Responses:**
- `401` — Incorrect email or password
- `422` — Invalid email format

---

### `GET /api/v1/auth/me`

**Description:** Get the currently authenticated user's profile. Used to validate stored tokens.
**Files:** `backend/app/routers/auth.py`, `backend/app/dependencies/auth.py`
**Tags:** Authentication
**Auth:** Bearer JWT required

**Request:** No body. Requires `Authorization: Bearer <token>` header.

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "username": "admin",
  "email": "admin@admin.com",
  "first_name": "Admin",
  "last_name": "User",
  "role": "Admin",
  "is_active": true,
  "is_superuser": false,
  "last_login": "2026-02-26T12:00:00+00:00"
}
```

**Error Responses:**
- `401` — Invalid or expired token / no token provided

---

## Health Check Endpoints

### `GET /`

**Description:** Root endpoint — returns app info.
**Files:** `backend/app/main.py`

**Response:**
```json
{
  "app": "WOMS API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### `GET /health`

**Description:** Root-level health check.
**Files:** `backend/app/main.py`

**Response:**
```json
{ "status": "healthy" }
```

---

### `GET /api/v1/health`

**Description:** API v1 health check.
**Files:** `backend/app/main.py`

**Response:**
```json
{ "status": "healthy", "version": "v1" }
```

---

## Order Import

### `POST /api/v1/orders/import`

**Description:** Upload Shopee, Lazada, or TikTok order export file (CSV or Excel) and import into woms_db.
**Files:** `backend/app/routers/order_import.py`, `backend/app/services/order_import/`
**Tags:** Order Import

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string (form) | Yes | `shopee`, `lazada`, or `tiktok` |
| `seller_id` | integer (form) | Yes | FK to seller table |
| `file` | file (upload) | Yes | CSV (.csv) or Excel (.xlsx/.xls), max 10 MB |

**Response:** `200 OK`
```json
{
  "platform": "shopee",
  "seller_id": 1,
  "filename": "Shopee Test Data.csv",
  "import_batch_id": "uuid-string",
  "total_rows": 116,
  "success_rows": 116,
  "skipped_rows": 0,
  "error_rows": 0,
  "errors": []
}
```

**Error Responses:**
- `422` — Unsupported platform, invalid file type, or empty file
- `413` — File exceeds 10 MB limit
- `500` — Import pipeline failure

---

## Reference Data

### `POST /api/v1/reference/load-platforms`

**Description:** Upsert platform records from Excel/CSV file.
**Files:** `backend/app/routers/reference.py`, `backend/app/services/reference_loader/loader.py`
**Tags:** Reference Data

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file (upload) | Yes | Platform reference file (.xlsx or .csv), max 20 MB |

**Expected file columns:** Platform_ID, Platform_Name, Address, Postcode
**Upsert key:** platform_name (unique)

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "4 platforms loaded (2 created, 2 updated)",
  "created": 2,
  "updated": 2,
  "total": 4
}
```

---

### `POST /api/v1/reference/load-sellers`

**Description:** Upsert seller records from Excel/CSV file.
**Files:** `backend/app/routers/reference.py`, `backend/app/services/reference_loader/loader.py`
**Tags:** Reference Data

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sellers_file` | file (upload) | Yes | Seller reference file (.xlsx or .csv) |
| `platforms_file` | file (upload) | No | Optional platform file for resolving Platform_ID codes |

**Expected sellers_file columns:** Seller_ID, Seller Name, Company Name, Platform_ID
**Upsert key:** Seller_ID (stored as platform_store_id)

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "8 sellers loaded (8 created, 0 updated)",
  "created": 8,
  "updated": 0,
  "total": 8
}
```

---

### `POST /api/v1/reference/load-items`

**Description:** Upsert items from Item Master Excel into the items table.
**Files:** `backend/app/routers/reference.py`, `backend/app/services/reference_loader/loader.py`
**Tags:** Reference Data

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file (upload) | Yes | Item Master Excel file (.xlsx), max 20 MB |

**Expected format:** Multi-sheet Excel with headers in row 4.
**Expected columns per sheet:** No., Product Name, SKU Name, Internal CODE (Main code), BaseUOM
**Upsert key:** items.master_sku (Internal CODE, unique)

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "499 items loaded (499 created, 0 updated)",
  "created": 499,
  "updated": 0,
  "total": 499
}
```

---

## ML Staging

### `POST /api/v1/ml/sync`

**Description:** Copy order_import_staging rows from woms_db to ml_woms_db.
**Files:** `backend/app/routers/ml_sync.py`, `backend/app/services/ml_sync/sync.py`
**Tags:** ML Staging

**Request:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform_source` | string | No | Filter: `shopee`, `lazada`, or `tiktok` |
| `seller_id` | integer | No | Filter by seller ID |

```json
{
  "platform_source": "tiktok",
  "seller_id": null
}
```

**Response:** `200 OK`
```json
{
  "platform_source": "tiktok",
  "seller_id": null,
  "staging_synced": 281,
  "staging_skipped": 0,
  "platforms_synced": 1,
  "sellers_synced": 3,
  "has_errors": false,
  "errors": []
}
```

---

### `POST /api/v1/ml/init-schema`

**Description:** Create all tables in ml_woms_db (one-time setup).
**Files:** `backend/app/routers/ml_sync.py`, `backend/app/ml_database.py`
**Tags:** ML Staging

**Request:** No body required.

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "ml_woms_db schema initialized"
}
```

---

## Items CRUD

**Files:** `backend/app/routers/items.py`, `backend/app/schemas/items.py`
**Tags:** Items
**Auth:** Write operations require Bearer JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/items` | No | List items (paginated, search, filter by is_active/category/brand) |
| GET | `/api/v1/items/{item_id}` | No | Get single item with nested lookups |
| POST | `/api/v1/items` | Yes | Create item |
| PATCH | `/api/v1/items/{item_id}` | Yes | Update item (partial) |
| DELETE | `/api/v1/items/{item_id}` | Yes | Soft-delete item |
| POST | `/api/v1/items/upload-image` | Yes | Upload item image (multipart, returns URL) |
| GET | `/api/v1/items/counts` | No | Get tab counts (all, live, unpublished, deleted) |
| GET | `/api/v1/items/types` | No | List all item types |
| POST | `/api/v1/items/types` | Yes | Create item type (201, 409 on duplicate) |
| PATCH | `/api/v1/items/types/{item_type_id}` | Yes | Update item type (404/409) |
| DELETE | `/api/v1/items/types/{item_type_id}` | Yes | Delete item type (204, 409 if referenced) |
| GET | `/api/v1/items/categories` | No | List all categories |
| POST | `/api/v1/items/categories` | Yes | Create category (201, 409 on duplicate) |
| PATCH | `/api/v1/items/categories/{category_id}` | Yes | Update category (404/409) |
| DELETE | `/api/v1/items/categories/{category_id}` | Yes | Delete category (204, 409 if referenced) |
| GET | `/api/v1/items/brands` | No | List all brands |
| POST | `/api/v1/items/brands` | Yes | Create brand (201, 409 on duplicate) |
| PATCH | `/api/v1/items/brands/{brand_id}` | Yes | Update brand (404/409) |
| DELETE | `/api/v1/items/brands/{brand_id}` | Yes | Delete brand (204, 409 if referenced) |
| GET | `/api/v1/items/uoms` | No | List all base UOMs |
| POST | `/api/v1/items/uoms` | Yes | Create UOM (201, 409 on duplicate) |
| PATCH | `/api/v1/items/uoms/{uom_id}` | Yes | Update UOM (404/409) |
| DELETE | `/api/v1/items/uoms/{uom_id}` | Yes | Delete UOM (204, 409 if referenced) |

**Pagination params:** `?page=1&page_size=20&search=term&is_active=true&category_id=2&brand_id=3&item_type_id=1&include_deleted=false`

### ItemCreate (POST `/api/v1/items` request body)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `item_name` | string (max 500) | Yes | — | Product name |
| `master_sku` | string (max 100) | Yes | — | Internal SKU code (unique) |
| `sku_name` | string (max 500) | No | null | SKU display name |
| `description` | string | No | null | Item description |
| `image_url` | string (max 500) | No | null | URL/path to main product image (from upload endpoint) |
| `uom_id` | integer | No | null | FK to base UOM |
| `brand_id` | integer | No | null | FK to brand |
| `item_type_id` | integer | No | null | FK to item type |
| `category_id` | integer | No | null | FK to category |
| `is_active` | boolean | No | true | Whether the item is active |
| `parent_id` | integer | No | null | FK to parent item (for variations) |
| `has_variation` | boolean | No | false | Whether item has child variations |
| `variations_data` | object (JSON) | No | null | Freeform variation metadata |

### ItemUpdate (PATCH `/api/v1/items/{item_id}` request body)

All fields are optional. Only provided fields are updated.

| Field | Type | Description |
|-------|------|-------------|
| `item_name` | string (max 500) | Product name |
| `sku_name` | string (max 500) | SKU display name |
| `description` | string | Item description |
| `image_url` | string (max 500) | URL/path to main product image |
| `uom_id` | integer | FK to base UOM |
| `brand_id` | integer | FK to brand |
| `item_type_id` | integer | FK to item type |
| `category_id` | integer | FK to category |
| `is_active` | boolean | Whether the item is active |
| `has_variation` | boolean | Whether item has child variations |
| `variations_data` | object (JSON) | Freeform variation metadata |

### ItemRead (response body)

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | integer | Primary key |
| `parent_id` | integer / null | FK to parent item |
| `item_name` | string | Product name |
| `master_sku` | string | Internal SKU code |
| `sku_name` | string / null | SKU display name |
| `description` | string / null | Item description |
| `image_url` | string / null | URL/path to main product image |
| `uom_id` | integer / null | FK to base UOM |
| `brand_id` | integer / null | FK to brand |
| `item_type_id` | integer / null | FK to item type |
| `category_id` | integer / null | FK to category |
| `is_active` | boolean | Whether the item is active |
| `has_variation` | boolean | Whether item has child variations |
| `variations_data` | object / null | Freeform variation metadata |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `deleted_at` | datetime / null | Soft-delete timestamp (null if not deleted) |
| `uom` | BaseUOMRead / null | Nested UOM lookup (when joined) |
| `brand` | BrandRead / null | Nested brand lookup (when joined) |
| `item_type` | ItemTypeRead / null | Nested item type lookup (when joined) |
| `category` | CategoryRead / null | Nested category lookup (when joined) |

### `GET /api/v1/items/counts`

**Description:** Returns item counts for tab-based status filtering UI.
**Files:** `backend/app/routers/items.py`
**Tags:** Items

**Request:** No body. No required params.

**Response:** `200 OK`
```json
{
  "all": 150,
  "live": 120,
  "unpublished": 20,
  "deleted": 10
}
```

| Field | Type | Description |
|-------|------|-------------|
| `all` | integer | Count of non-deleted items (deleted_at IS NULL) |
| `live` | integer | Count of active, non-deleted items (is_active = true, deleted_at IS NULL) |
| `unpublished` | integer | Count of inactive, non-deleted items (is_active = false, deleted_at IS NULL) |
| `deleted` | integer | Count of soft-deleted items (deleted_at IS NOT NULL) |

### `POST /api/v1/items/upload-image`

**Description:** Upload a product image for an item. Returns the URL path to the saved file. Images are stored in `backend/uploads/items/`.
**Files:** `backend/app/routers/items.py`
**Tags:** Items
**Auth:** Bearer JWT required

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Image file (JPEG, PNG, WebP, or GIF) |

**Validation:**
- Allowed content types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`
- Maximum file size: 5 MB

**Response:** `200 OK`
```json
{
  "url": "/uploads/items/a1b2c3d4e5f6_product-photo.jpg"
}
```

**Error Responses:**
- `400` — Invalid file type or file too large
- `401` — Not authenticated

**Static file serving:** Uploaded images are served at `GET /uploads/items/{filename}` via FastAPI StaticFiles mount.

---

## Orders CRUD

**Files:** `backend/app/routers/orders.py`, `backend/app/schemas/orders.py`
**Tags:** Orders
**Auth:** Write operations require Bearer JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/orders` | No | List orders (paginated, filter by platform/store/status, search) |
| GET | `/api/v1/orders/{order_id}` | No | Get single order with all details |
| POST | `/api/v1/orders` | Yes | Create order with optional line items |
| PATCH | `/api/v1/orders/{order_id}` | Yes | Update order (partial) |
| PATCH | `/api/v1/orders/{order_id}/details/{detail_id}` | Yes | Update a single order line item |

**Pagination params:** `?page=1&page_size=20&platform_id=1&store_id=2&order_status=pending&search=term`

---

## Platforms & Sellers CRUD

**Files:** `backend/app/routers/platforms.py`, `backend/app/schemas/platform.py`
**Tags:** Marketplace
**Auth:** Write operations require Bearer JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/platforms` | No | List all platforms (filter by is_active) |
| GET | `/api/v1/platforms/{platform_id}` | No | Get single platform |
| POST | `/api/v1/platforms` | Yes | Create platform |
| PATCH | `/api/v1/platforms/{platform_id}` | Yes | Update platform |
| GET | `/api/v1/sellers` | No | List sellers (paginated, filter by platform/active, search) |
| GET | `/api/v1/sellers/{seller_id}` | No | Get single seller with nested platform |
| POST | `/api/v1/sellers` | Yes | Create seller |
| PATCH | `/api/v1/sellers/{seller_id}` | Yes | Update seller |

---

## Warehouse & Inventory

**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`
**Tags:** Warehouse
**Auth:** Write operations require Bearer JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/warehouse` | No | List all warehouses (filter by is_active) |
| GET | `/api/v1/warehouse/{id}` | No | Get single warehouse |
| POST | `/api/v1/warehouse` | Yes | Create warehouse |
| PATCH | `/api/v1/warehouse/{id}` | Yes | Update warehouse |
| GET | `/api/v1/warehouse/{id}/locations` | No | List inventory locations in warehouse |
| GET | `/api/v1/warehouse/{id}/inventory` | No | List inventory levels (paginated, filter by item_id) |
| GET | `/api/v1/warehouse/{id}/alerts` | No | List inventory alerts (filter by is_resolved) |

---

## Delivery (Trips & Drivers)

**Files:** `backend/app/routers/delivery.py`, `backend/app/schemas/delivery.py`
**Tags:** Delivery
**Auth:** Write operations require Bearer JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/delivery/drivers` | No | List drivers (paginated, filter, search) |
| GET | `/api/v1/delivery/drivers/{id}` | No | Get single driver |
| POST | `/api/v1/delivery/drivers` | Yes | Create driver |
| PATCH | `/api/v1/delivery/drivers/{id}` | Yes | Update driver |
| GET | `/api/v1/delivery/trips` | No | List trips (paginated, filter by status) |
| GET | `/api/v1/delivery/trips/{id}` | No | Get single trip |
| POST | `/api/v1/delivery/trips` | Yes | Create trip |
| PATCH | `/api/v1/delivery/trips/{id}` | Yes | Update trip |

---

## Users & Roles

**Files:** `backend/app/routers/users.py`, `backend/app/schemas/users.py`
**Tags:** Users
**Auth:** All endpoints require Bearer JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/users` | Yes | List users (paginated, filter by active/role, search) |
| GET | `/api/v1/users/{user_id}` | Yes | Get single user with nested role |
| POST | `/api/v1/users` | Yes | Create user (password is hashed) |
| PATCH | `/api/v1/users/{user_id}` | Yes | Update user (password re-hashed if provided) |
| GET | `/api/v1/users/roles` | Yes | List all roles |

---

## Frontend API Files

The frontend API client is organised as follows:

| Frontend File | Backend Endpoint(s) | Function(s) |
|---|---|---|
| `frontend/src/api/client.ts` | All | Axios instance with base URL, Bearer token injection, 401 redirect |
| `frontend/src/api/auth.ts` | `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | `login(credentials)`, `getMe()` |
| `frontend/src/api/health.ts` | `GET /api/v1/health` | `checkHealth()` |
| `frontend/src/api/orders.ts` | `POST /api/v1/orders/import` | `importOrders(platform, sellerId, file)` |
| `frontend/src/api/reference.ts` | `POST /api/v1/reference/load-*` | `loadPlatforms(file)`, `loadSellers(sellersFile, platformsFile?)`, `loadItems(file)` |
| `frontend/src/api/mlSync.ts` | `POST /api/v1/ml/*` | `syncStaging(request?)`, `initSchema()` |
| `frontend/src/api/base/items.ts` | `GET/POST/PATCH/DELETE /api/v1/items/{types,categories,brands,uoms,statuses}` | `list*()`, `create*(name)`, `update*(id, name)`, `delete*(id)` — 20 functions total |
| `frontend/src/api/base/items.ts` | `GET/POST/PATCH/DELETE /api/v1/items` | `listItems(params)`, `getItem(id)`, `createItem(data)`, `updateItem(id, data)`, `deleteItem(id)` — 5 item CRUD functions |
| `frontend/src/api/base/items.ts` | `GET /api/v1/items/counts` | `getItemCounts()` — returns tab counts for Items list page |

---

## Template for New API Entries

```markdown
### `METHOD /api/v1/path`

**Description:** What this endpoint does.
**Files:** Which backend/frontend files were created or modified.
**Tags:** Category tag

**Request:** Content type

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field_name` | type | Yes/No | Description |

**Response:** `200 OK`
\`\`\`json
{ "example": "response" }
\`\`\`
```
