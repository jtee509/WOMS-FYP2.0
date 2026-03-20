# WOMS Web API Documentation

All API endpoints are documented here. When creating or modifying an API, update this file with the endpoint details, request/response format, and which files were changed.

**Base URL:** `http://localhost:8000`
**API Prefix:** `/api/v1`

---

## Authentication

### `POST /api/v1/auth/login`

**Description:** Authenticate a user with email and password. Returns a JWT access token (8 hours), a refresh token (7 days), and sets the refresh token as an httpOnly cookie.
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
  "refresh_token": "abc123...",
  "token_type": "bearer",
  "expires_in": 28800,
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

### `POST /api/v1/auth/refresh`

**Description:** Exchange a valid refresh token for a new access + refresh token pair. The old refresh token is revoked (rotation). No access token required — this endpoint is for when the access token has expired.
**Files:** `backend/app/routers/auth.py`, `backend/app/services/auth.py`
**Tags:** Authentication

**Request:** Refresh token is read from the `refresh_token` httpOnly cookie (preferred) or from the request body (fallback).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | No | Plaintext refresh token (fallback if cookie unavailable) |

**Response:** `200 OK` — same shape as login response (new access + refresh tokens)

**Error Responses:**
- `401 refresh_token_missing` — No refresh token in cookie or body
- `401 refresh_token_invalid` — Expired, revoked, or unrecognized refresh token

**Security:** If a revoked refresh token is reused, ALL tokens for that user are revoked (indicates possible token theft).

---

### `POST /api/v1/auth/logout`

**Description:** Revoke all refresh tokens for the current user and clear the httpOnly cookie.
**Files:** `backend/app/routers/auth.py`, `backend/app/services/auth.py`
**Tags:** Authentication
**Auth:** Bearer JWT required

**Response:** `200 OK`
```json
{
  "detail": "Logged out",
  "tokens_revoked": 3
}
```

**Error Responses:**
- `401` — Invalid or expired access token

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
- `401 token_expired` — Access token has expired (frontend should call /auth/refresh)
- `401 token_invalid` — Token signature invalid or malformed (frontend should redirect to login)

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
| GET | `/api/v1/items/resolve-barcode?barcode=XXX` | Yes | Universal barcode lookup → item + optional variation (searches Item.barcode, master_sku, variation barcode in JSONB) |
| GET | `/api/v1/items` | No | List items (paginated, search, filter by is_active/category/brand) |
| GET | `/api/v1/items/{item_id}` | No | Get single item with nested lookups |
| POST | `/api/v1/items` | Yes | Create item |
| PATCH | `/api/v1/items/{item_id}` | Yes | Update item (partial) |
| DELETE | `/api/v1/items/{item_id}` | Yes | Soft-delete item (sets deleted_at) |
| POST | `/api/v1/items/{item_id}/restore` | Yes | Restore soft-deleted item (clears deleted_at) |
| POST | `/api/v1/items/upload-image` | Yes | Upload item image (multipart, returns URL) |
| GET | `/api/v1/items/counts` | No | Get tab counts (all, live, unpublished, deleted) |
| GET | `/api/v1/items/types` | No | List all live item types (excludes soft-deleted) |
| POST | `/api/v1/items/types` | Yes | Create item type (201, 409 on duplicate) |
| PATCH | `/api/v1/items/types/{item_type_id}` | Yes | Update item type (404/409) |
| DELETE | `/api/v1/items/types/{item_type_id}` | Yes | Soft-delete item type (204, sets deleted_at) |
| POST | `/api/v1/items/types/{item_type_id}/restore` | Yes | Restore soft-deleted item type |
| GET | `/api/v1/items/categories` | No | List all live categories (excludes soft-deleted) |
| POST | `/api/v1/items/categories` | Yes | Create category (201, 409 on duplicate) |
| PATCH | `/api/v1/items/categories/{category_id}` | Yes | Update category (404/409) |
| DELETE | `/api/v1/items/categories/{category_id}` | Yes | Soft-delete category (204, sets deleted_at) |
| POST | `/api/v1/items/categories/{category_id}/restore` | Yes | Restore soft-deleted category |
| GET | `/api/v1/items/brands` | No | List all live brands (excludes soft-deleted) |
| POST | `/api/v1/items/brands` | Yes | Create brand (201, 409 on duplicate) |
| PATCH | `/api/v1/items/brands/{brand_id}` | Yes | Update brand (404/409) |
| DELETE | `/api/v1/items/brands/{brand_id}` | Yes | Soft-delete brand (204, sets deleted_at) |
| POST | `/api/v1/items/brands/{brand_id}/restore` | Yes | Restore soft-deleted brand |
| GET | `/api/v1/items/uoms` | No | List all live base UOMs (excludes soft-deleted) |
| POST | `/api/v1/items/uoms` | Yes | Create UOM (201, 409 on duplicate) |
| PATCH | `/api/v1/items/uoms/{uom_id}` | Yes | Update UOM (404/409) |
| DELETE | `/api/v1/items/uoms/{uom_id}` | Yes | Soft-delete UOM (204, sets deleted_at) |
| POST | `/api/v1/items/uoms/{uom_id}/restore` | Yes | Restore soft-deleted UOM |
| GET | `/api/v1/items/bundles` | No | List bundle items with component counts (paginated, filter by search/is_active/category/brand/include_deleted) |
| GET | `/api/v1/items/bundles/counts` | No | Bundle tab counts: { all, live, unpublished, deleted } |
| GET | `/api/v1/items/bundles/{item_id}` | No | Get single bundle with full components (BundleReadResponse) |
| POST | `/api/v1/items/bundles` | Yes | Create bundle item + BundleComponent rows in one transaction (201, 409/422) |
| PATCH | `/api/v1/items/bundles/{item_id}` | Yes | Update bundle metadata and/or replace components (200, 404/409/422) |
| DELETE | `/api/v1/items/bundles/{item_id}` | Yes | Soft-delete bundle (204, sets deleted_at; BOM rows preserved) |
| POST | `/api/v1/items/bundles/{item_id}/restore` | Yes | Restore soft-deleted bundle (clears deleted_at, returns BundleReadResponse) |

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
| `barcode` | string / null | System-generated reference code from sequence engine. Read-only, immutable after first assignment. Not present in create/update payloads. Auto-generated on item creation when ITEMS convention has `auto_apply_on_create` enabled. |
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

### `POST /api/v1/items/import`

**Description:** Bulk-import items from a CSV or Excel file. Each row is validated independently — valid rows are inserted and invalid rows are reported with per-row error messages. A partial success (some rows OK, some errored) returns `200 OK` with `error_rows > 0`.
**Files:** `backend/app/routers/items.py`, `backend/app/services/items_import/` (parser, validator, importer)
**Tags:** Items
**Auth:** Bearer JWT required

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | CSV or Excel file (`.csv`, `.xlsx`, `.xls`) |

**File validation (server-side):**
- Allowed extensions: `.csv`, `.xlsx`, `.xls`
- Maximum file size: 10 MB

**Supported column headers (case-insensitive, aliases resolved automatically):**

| Canonical name | Accepted header aliases | Required? |
|----------------|------------------------|-----------|
| `item_name` | `item_name`, `product name`, `name` | **Yes** |
| `master_sku` | `master_sku`, `internal code (main code)`, `internal code`, `sku`, `sku code` | **Yes** |
| `sku_name` | `sku_name`, `sku name`, `variant name` | No |
| `description` | `description`, `desc` | No |
| `uom` | `uom`, `base uom`, `baseuom`, `unit` | No |
| `brand` | `brand`, `brand name` | No |
| `category` | `category`, `category name` | No |
| `item_type` | `item_type`, `item type`, `type` | No |
| `is_active` | `is_active`, `is active`, `active`, `status` | No (default: `true`) |

**`is_active` accepted values:** `true`, `false`, `1`, `0`, `yes`, `no` (case-insensitive).

**Per-row validation rules:**
1. `item_name` must be present and ≤ 500 characters
2. `master_sku` must be present, ≤ 100 characters, no whitespace
3. `master_sku` must not already exist in the database
4. `master_sku` must be unique within the uploaded file
5. FK name values (`uom`, `brand`, `category`, `item_type`) must match an existing record name (case-insensitive); unknown names produce a row error

**Response:** `200 OK`

```json
{
  "total_rows": 50,
  "success_rows": 47,
  "error_rows": 3,
  "errors": [
    { "row": 5,  "master_sku": "SHIRT-001", "error": "Duplicate master_sku in this file" },
    { "row": 12, "master_sku": "PANTS-999", "error": "master_sku already exists in the database" },
    { "row": 31, "master_sku": "HAT-005",   "error": "Unknown uom: 'Kilograms'" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_rows` | integer | Total rows parsed from the file (excluding header) |
| `success_rows` | integer | Rows successfully inserted into the database |
| `error_rows` | integer | Rows that failed validation and were not inserted |
| `errors` | array | List of per-row error objects |
| `errors[].row` | integer | 1-based row number in the uploaded file |
| `errors[].master_sku` | string | Master SKU value from that row (or `""` if missing) |
| `errors[].error` | string | Human-readable error description |

**Error Responses:**
- `401` — Not authenticated
- `413` — File exceeds 10 MB
- `422` — Unsupported file extension, or file has no data rows, or file cannot be decoded

### `POST /api/v1/items/bundles/import`

**Description:** Bulk-import bundles from a CSV or Excel file. Each row represents one component of a bundle. Rows sharing the same `bundle_sku` are grouped into a single bundle. Metadata (name, category, brand, etc.) is taken from the first row per group. The backend validates component SKU existence, resolves FKs, enforces bundle composition rules, and creates Item + BundleComponent records per bundle. Platform-independent — no platform_id or seller_id required.
**Files:** `backend/app/routers/items.py`, `backend/app/services/items_import/bundle_importer.py`
**Tags:** Items
**Auth:** Bearer JWT required

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | CSV or Excel file (`.csv`, `.xlsx`, `.xls`) |

**Supported column headers (case-insensitive, aliases resolved automatically):**

| Canonical name | Accepted header aliases | Required? |
|----------------|------------------------|-----------|
| `bundle_name` | `bundle_name`, `bundle name`, `item_name`, `name` | **Yes** |
| `bundle_sku` | `bundle_sku`, `bundle sku`, `master_sku`, `sku` | **Yes** |
| `component_sku` | `component_sku`, `component sku`, `comp_sku` | **Yes** |
| `component_qty` | `component_qty`, `component qty`, `qty`, `quantity` | **Yes** |
| `sku_name` | `sku_name`, `sku name`, `display name` | No |
| `description` | `description`, `desc` | No |
| `category` | `category`, `category name` | No |
| `brand` | `brand`, `brand name` | No |
| `uom` | `uom`, `base uom`, `unit` | No |
| `is_active` | `is_active`, `active`, `status` | No (default: `true`) |

**Grouping:** Rows with the same `bundle_sku` are grouped. The first row's metadata is used.

**Validation rules (per bundle group):**
1. `bundle_name` required, ≤ 500 characters
2. `bundle_sku` required, ≤ 100 characters, no spaces, unique in DB and file
3. Each `component_sku` must exist as an active item in the database
4. `component_qty` must be a positive integer (defaults to 1 if empty)
5. Bundle must have >1 distinct components, or a single component with qty > 1

**Response:** Same `ImportResult` schema as items import (counts are bundles, not rows).

**Error Responses:**
- `401` — Not authenticated
- `413` — File exceeds 10 MB
- `422` — Unsupported file extension, no data rows, or "Bundle" item type not found

---

### `GET /api/v1/items/bundles`

**Description:** List all bundle-type items with component counts. Returns `BundleListItem` objects which extend `ItemRead` with `component_count` (distinct component entries) and `total_quantity` (sum of component quantities). Component counts are computed via LEFT JOIN on `bundle_components` table. Only valid bundles are returned (>1 distinct components or any component with qty > 1).
**Files:** `backend/app/routers/items.py`, `backend/app/schemas/items.py`
**Tags:** Items
**Auth:** None required

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | 1 | Page number (>= 1) |
| `page_size` | integer | 20 | Items per page (1-100) |
| `search` | string | null | Search by bundle name or master_sku |
| `is_active` | boolean | null | Filter by active status |
| `category_id` | integer | null | Filter by category |
| `brand_id` | integer | null | Filter by brand |
| `include_deleted` | boolean | false | If true, show only soft-deleted bundles |

**Response:** `200 OK` — `PaginatedResponse[BundleListItem]`

```json
{
  "items": [
    {
      "item_id": 42,
      "item_name": "Summer Pack",
      "master_sku": "BUNDLE-SUMMER-001",
      "is_active": true,
      "category": { "id": 3, "name": "Electronics" },
      "brand": { "id": 1, "name": "TechBrand" },
      "component_count": 3,
      "total_quantity": 7,
      "..."
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

### `GET /api/v1/items/bundles/counts`

**Description:** Get bundle counts for tab filters, scoped to Bundle item type only.
**Files:** `backend/app/routers/items.py`
**Tags:** Items
**Auth:** None required

**Response:** `200 OK`
```json
{ "all": 12, "live": 10, "unpublished": 2, "deleted": 1 }
```

### `GET /api/v1/items/bundles/{item_id}`

**Description:** Get a single bundle by item_id with its full component list. Returns the same `BundleReadResponse` shape as create/update endpoints.
**Files:** `backend/app/routers/items.py`
**Tags:** Items
**Auth:** None required

**Response:** `200 OK` — `BundleReadResponse`

**`BundleComponentRead` schema (used in all bundle responses):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | BundleComponent row PK |
| `item_id` | integer | Component item ID |
| `item_name` | string | Component item name |
| `master_sku` | string | Component item master SKU |
| `quantity` | integer | Quantity in the bundle |
| `sort_order` | integer | Display order (0-based) |
| `barcode` | string / null | Item-level barcode |
| `image_url` | string / null | Item image URL |
| `variation_sku` | string / null | Specific variation SKU (null = whole item) |
| `variation_label` | string / null | Human-readable variation label (e.g., "Red / M"), resolved at read time from JSONB |
| `variation_barcode` | string / null | Barcode from the variation combination's JSONB |
| `orphaned` | boolean | `true` if the `variation_sku` no longer exists in the parent item's `variations_data` |

**Error Responses:**
- `404` — Bundle not found
- `422` — Item is not a Bundle type
- `500` — "Bundle" item type not seeded

### `POST /api/v1/items/bundles`

**Description:** Create a bundle item and its BOM (Bill of Materials) in a single atomic transaction. Inserts into `items` (with `item_type = "Bundle"`) and creates `bundle_components` rows. Platform-independent — no platform_id or seller_id required. Supports variation-level components via `variation_sku`. The `trg_items_history_on_insert` trigger automatically creates an audit trail record in `items_history`.
**Files:** `backend/app/routers/items.py`, `backend/app/schemas/items.py`
**Tags:** Items
**Auth:** Bearer JWT required

**Request:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_name` | string | Yes | Bundle display name |
| `master_sku` | string | Yes | Unique SKU for the bundle (max 100 chars) |
| `sku_name` | string | No | Optional SKU display name |
| `description` | string | No | Bundle description |
| `image_url` | string | No | Image URL/path |
| `uom_id` | integer | No | Unit of measure FK |
| `brand_id` | integer | No | Brand FK |
| `category_id` | integer | No | Category FK |
| `is_active` | boolean | No | Default `true` |
| `components` | array | Yes | At least 1 component; must have >1 distinct items/variations or single item with qty > 1 |
| `components[].item_id` | integer | Yes | Existing item ID (must not be deleted) |
| `components[].variation_sku` | string | No | If set, references a specific variation by SKU inside the item's `variations_data.combinations[]`. NULL means the whole item. |
| `components[].quantity` | integer | Yes | Quantity of this component in the bundle (>= 1) |

```json
{
  "item_name": "Summer Essentials Pack",
  "master_sku": "BUNDLE-SUMMER-001",
  "category_id": 2,
  "components": [
    { "item_id": 10, "variation_sku": "TSHIRT-RED-M", "quantity": 2 },
    { "item_id": 25, "quantity": 1 },
    { "item_id": 42, "variation_sku": "SUN-BLACK", "quantity": 1 }
  ]
}
```

**Response:** `201 Created`

```json
{
  "item": {
    "item_id": 150,
    "item_name": "Summer Essentials Pack",
    "master_sku": "BUNDLE-SUMMER-001",
    "item_type_id": 7,
    "item_type": { "id": 7, "name": "Bundle" },
    "is_active": true,
    "created_at": "2026-03-18T12:00:00",
    "updated_at": "2026-03-18T12:00:00"
  },
  "components": [
    {
      "id": 1, "item_id": 10, "item_name": "T-Shirt", "master_sku": "TSHIRT-001",
      "variation_sku": "TSHIRT-RED-M", "variation_label": "Red / M", "variation_barcode": "8901234567890",
      "quantity": 2, "sort_order": 0, "barcode": "ITEM-000010", "image_url": null, "orphaned": false
    },
    {
      "id": 2, "item_id": 25, "item_name": "Cap Black", "master_sku": "CAP-B-001",
      "variation_sku": null, "variation_label": null, "variation_barcode": null,
      "quantity": 1, "sort_order": 1, "barcode": "ITEM-000025", "image_url": null, "orphaned": false
    },
    {
      "id": 3, "item_id": 42, "item_name": "Sunglasses", "master_sku": "SUN-001",
      "variation_sku": "SUN-BLACK", "variation_label": "Black", "variation_barcode": "8907654321000",
      "quantity": 1, "sort_order": 2, "barcode": "ITEM-000042", "image_url": null, "orphaned": false
    }
  ]
}
```

**Validation Rules:**
1. `master_sku` must be unique across ALL items (409 if duplicate)
2. Bundle composition: must have >1 distinct component entries (counting `(item_id, variation_sku)` as distinct), OR a single component with quantity > 1 (422 otherwise)
3. All component `item_id`s must exist and not be soft-deleted (422 if missing)
4. If `variation_sku` is provided, the parent item must have `has_variation = true` and the SKU must exist in `variations_data.combinations[].sku` (422 if invalid)
5. Item type "Bundle" must exist in `item_type` seed data (500 if missing)

**Error Responses:**
- `401` — Not authenticated
- `409` — Master SKU already exists
- `422` — Invalid bundle composition or component item_ids not found
- `500` — "Bundle" item type not seeded

### `PATCH /api/v1/items/bundles/{item_id}`

**Description:** Update a bundle's metadata (name, SKU, category, etc.) and/or replace its components. Uses a **delete-and-reinsert** strategy for components: when `components` is provided, all existing `bundle_components` rows for this bundle are removed and replaced with the new set. Supports variation-level components via `variation_sku`.
**Files:** `backend/app/routers/items.py`, `backend/app/schemas/items.py`
**Tags:** Items
**Auth:** Bearer JWT required

**Request:** `application/json` — all fields optional

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_name` | string | No | New bundle name |
| `master_sku` | string | No | New unique SKU for the bundle (max 100 chars) |
| `sku_name` | string | No | New SKU display name |
| `description` | string | No | Updated description |
| `image_url` | string | No | Updated image URL/path |
| `uom_id` | integer | No | Unit of measure FK |
| `brand_id` | integer | No | Brand FK |
| `category_id` | integer | No | Category FK |
| `is_active` | boolean | No | Toggle active status |
| `components` | array | No | If provided, replaces ALL existing components. Must satisfy bundle rules. |
| `components[].item_id` | integer | Yes* | Component item ID (must exist, not deleted) |
| `components[].variation_sku` | string | No* | Specific variation SKU (null = whole item) |
| `components[].quantity` | integer | Yes* | Quantity >= 1 |

```json
{
  "master_sku": "BUNDLE-SUMMER-V2",
  "sku_name": "Summer Pack V2",
  "components": [
    { "item_id": 10, "variation_sku": "TSHIRT-RED-L", "quantity": 3 },
    { "item_id": 25, "quantity": 1 },
    { "item_id": 50, "variation_sku": "SHORTS-BLUE-M", "quantity": 2 }
  ]
}
```

**Response:** `200 OK` — same `BundleReadResponse` shape as POST

**Data Integrity:**
- Changing `master_sku` updates the bundle's items row only — component item SKUs are never touched
- Component replacement is atomic — if any validation fails, no components are changed
- Same validation rules as POST (variation_sku must exist in parent item's JSONB)

**Error Responses:**
- `401` — Not authenticated
- `404` — Bundle item not found
- `409` — New master_sku already exists on another item
- `422` — Item is not a Bundle type, invalid component composition, component item_ids not found, or variation_sku invalid
- `500` — "Bundle" item type not seeded

### `DELETE /api/v1/items/bundles/{item_id}`

**Description:** Soft-delete a bundle. Sets `deleted_at` and `deleted_by` on the items row. The `bundle_components` rows are preserved so the bundle can be fully restored later. The PostgreSQL trigger `trg_items_history_on_update` automatically records a `SOFT_DELETE` history entry in `items_history`.
**Files:** `backend/app/routers/items.py`
**Tags:** Items
**Auth:** Bearer JWT required

**Response:** `204 No Content`

**Error Responses:**
- `401` — Not authenticated
- `404` — Bundle not found (or already soft-deleted)
- `422` — Item is not a Bundle type
- `500` — "Bundle" item type not seeded

### `POST /api/v1/items/bundles/{item_id}/restore`

**Description:** Restore a previously soft-deleted bundle. Clears `deleted_at` and `deleted_by` on the items row. BundleComponent rows are still intact from the original soft-delete. The trigger records a `RESTORE` history entry.
**Files:** `backend/app/routers/items.py`
**Tags:** Items
**Auth:** Bearer JWT required

**Response:** `200 OK` — `BundleReadResponse` (same shape as create/update)

**Error Responses:**
- `400` — Bundle is not deleted
- `401` — Not authenticated
- `404` — Bundle not found
- `422` — Item is not a Bundle type
- `500` — "Bundle" item type not seeded

---

## Orders CRUD

**Files:** `backend/app/routers/orders.py`, `backend/app/schemas/orders.py`
**Tags:** Orders
**Auth:** Write operations require Bearer JWT.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/orders` | No | List orders (paginated, enriched with platform/store names, detail count, total paid) |
| GET | `/api/v1/orders/{order_id}` | No | Get single order with all details |
| POST | `/api/v1/orders` | Yes | Create order with optional line items |
| PATCH | `/api/v1/orders/{order_id}` | Yes | Update order (partial) |
| PATCH | `/api/v1/orders/{order_id}/details/{detail_id}` | Yes | Update a single order line item |
| POST | `/api/v1/orders/bulk-ship` | Yes | Bulk ship orders: updates status to shipped, assigns tracking numbers |

**List params:** `?page=1&page_size=20&platform_id=1&store_id=2&order_status=pending&search=term&date_from=2026-01-01&date_to=2026-03-11&assigned_warehouse_id=1&sort_by=order_date&sort_dir=desc`

**Sort columns:** `order_date` (default), `created_at`, `order_status`, `platform_order_id`, `recipient_name`

**Enriched list response fields:** `platform_name`, `store_name` (from JOINs), `detail_count`, `total_paid` (from aggregate subquery)

### `POST /api/v1/orders/bulk-ship`

Bulk-ship orders with tracking assignment. Each order is processed independently — partial failures are possible.

**Request:**
```json
{
  "shipments": [
    {
      "order_id": 123,
      "details": [
        { "detail_id": 456, "tracking_number": "JP001234567", "courier_type": "J&T Express" }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "total": 1,
  "succeeded": 1,
  "failed": 0,
  "results": [
    { "order_id": 123, "success": true }
  ]
}
```

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
| GET | `/api/v1/warehouse` | No | List all warehouses (filter by `is_active`, excludes soft-deleted) |
| GET | `/api/v1/warehouse/{id}` | No | Get single warehouse |
| POST | `/api/v1/warehouse` | Yes | Create warehouse |
| PATCH | `/api/v1/warehouse/{id}` | Yes | Update warehouse |
| DELETE | `/api/v1/warehouse/{id}` | Yes | Soft-delete warehouse + cascade to all locations (204) |
| POST | `/api/v1/warehouse/{id}/restore` | Yes | Restore soft-deleted warehouse + cascade-restore locations |
| GET | `/api/v1/warehouse/{id}/locations` | No | List inventory locations in warehouse (excludes soft-deleted) |
| POST | `/api/v1/warehouse/{id}/locations` | Yes | Create a single inventory location |
| PATCH | `/api/v1/warehouse/locations/{id}` | Yes | Update an inventory location |
| DELETE | `/api/v1/warehouse/locations/{id}` | Yes | Recursive soft-delete: location + all children. Returns `{"deleted": N}` |
| POST | `/api/v1/warehouse/locations/{id}/restore` | Yes | Restore a soft-deleted location |
| DELETE | `/api/v1/warehouse/{id}/locations/subtree` | Yes | Soft-delete locations by hierarchy prefix (section/zone/aisle/rack) |
| PATCH | `/api/v1/warehouse/{id}/locations/rename-level` | Yes | Bulk-rename a hierarchy level (section/zone/aisle/rack/bin). Body: `level`, `old_value`, `new_value`, optional `section`, `zone`, `aisle`, `rack` |
| POST | `/api/v1/warehouse/{id}/locations/bulk-generate` | Yes | Bulk-generate locations from range specs (Cartesian product, max 10k). Body: `SegmentRange` per hierarchy level |
| GET | `/api/v1/warehouse/{id}/locations/hierarchy` | No | Nested JSON tree (Warehouse > Section > Zone > Aisle > Rack > Bin). Orphans grouped under virtual "Unassigned" node (type=unassigned, is_virtual=true). O(n) |
| GET | `/api/v1/warehouse/{id}/inventory` | No | Enriched inventory levels — joins Item + Location, computed `stock_status`. Paginated. Params: `page`, `page_size`, `item_id`, `location_id`, `search`, `stock_status`. When `location_id` is provided, only returns items at that location with `quantity_available > 0` |
| GET | `/api/v1/warehouse/movement-types` | No | List all movement types (Receipt, Shipment, Transfer, etc.) |
| GET | `/api/v1/warehouse/{id}/movements` | No | Movement history for a warehouse (paginated). Joins through transactions to get item info. Optional `status` query param filters by lifecycle status (pending, in_transit, completed, cancelled) |
| POST | `/api/v1/warehouse/movements` | Yes | Record a stock movement (inbound/outbound/transfer). Creates movement + transactions with status="pending" — stock levels are NOT updated until lifecycle transitions |
| PATCH | `/api/v1/warehouse/movements/{id}/approve` | Yes | Transition pending→in_transit; deducts outbound stock from source location |
| PATCH | `/api/v1/warehouse/movements/{id}/complete` | Yes | Transition in_transit→completed; adds inbound stock at destination location |
| PATCH | `/api/v1/warehouse/movements/{id}/cancel` | Yes | Transition pending\|in_transit→cancelled; reverses outbound deduction if movement was in_transit |
| GET | `/api/v1/warehouse/{id}/alerts` | No | List inventory alerts (filter by `is_resolved`) |
| PATCH | `/api/v1/warehouse/alerts/{id}/resolve` | Yes | Mark an alert as resolved. Stores resolution notes + resolver user |
| POST | `/api/v1/warehouse/reserve` | Yes | Pessimistically reserve stock for a standalone item. Uses row-level lock to prevent oversell. Body: `item_id`, `quantity`, `warehouse_id` |
| POST | `/api/v1/warehouse/release` | Yes | Release a reservation (order cancelled). Body: `item_id`, `quantity`, `warehouse_id` |
| POST | `/api/v1/warehouse/fulfill/bundle` | Yes | Atomic bundle stock deduction. Deducts all BOM components in one transaction. Body: `bundle_item_id`, `bundle_qty_sold`, `warehouse_id`, `order_reference` |
| PATCH | `/api/v1/warehouse/inventory-levels/{level_id}` | Yes | Update inventory level thresholds (reorder_point, safety_stock, max_stock) |
| GET | `/api/v1/warehouse/{warehouse_id}/analytics/movements-per-day` | No | Daily movement counts grouped by type, with date range filtering |
| GET | `/api/v1/warehouse/{warehouse_id}/analytics/top-items` | No | Top N items by total quantity moved, with date range + limit params |
| GET | `/api/v1/warehouse/{warehouse_id}/analytics/stock-health` | No | Item count per stock_status category for the warehouse |

### Warehouse — Rename Level

- `PATCH /api/v1/warehouse/{warehouse_id}/locations/rename-level` — Bulk-rename a hierarchy level (section/zone/aisle/rack/bin)
  - **Body:** `{ level, old_value, new_value, section?, zone?, aisle?, rack? }`
  - **Description:** Renames all locations with `old_value` in the specified `level` (constrained optionally by ancestor hierarchy). Returns count of updated locations.
  - **Response:** `200 OK` → `{ updated_count, level, old_value, new_value }`

---

**Inventory Guard (v0.5.38):** All destructive warehouse operations now return `400 Bad Request` with message `"Cannot delete: Location contains active stock."` if any affected location (or child location) has stock (qty_available > 0 OR reserved_qty > 0). Protected endpoints:
- `DELETE /warehouse/{id}` — checks all locations in the warehouse
- `DELETE /warehouse/locations/{id}` — checks the target location + all recursive children
- `DELETE /warehouse/{id}/locations/subtree` — checks all locations matching the hierarchy prefix
- `PATCH /warehouse/{id}` (when `is_active=false`) — checks all warehouse locations
- `PATCH /warehouse/locations/{id}` (when `is_active=false`) — checks the target + all children
- `PATCH /warehouse/{id}/toggle-status` (when toggling to inactive) — checks all warehouse locations

**Recursive Soft-Delete (v0.5.38):** `DELETE /warehouse/locations/{id}` now cascades. If the target location is at a higher hierarchy level (e.g. Section), all children (Zones, Aisles, Racks, Bins) sharing the same prefix are also soft-deleted. Returns `{"deleted": N}`.

**Orphan Management (v0.5.38):** `GET /warehouse/{id}/locations/hierarchy` groups locations with section=NULL under a virtual "Unassigned" node at the end of the warehouse children. This node has `type: "unassigned"`, `is_virtual: true`, and `is_orphan: true`. Normal sections are counted separately in the warehouse summary.

GET `/api/v1/warehouse` and GET `/api/v1/warehouse/{id}` include `location_count` field (total non-deleted inventory_location rows in that warehouse).

---

**Key response types (v0.5.12 / v0.5.19):**
- `InventoryLevelEnrichedRead` — includes `item_name`, `master_sku`, `location: LocationSummary`, `quantity_available`, `reserved_quantity`, `stock_status` (based on ATP = available − reserved)
- `InventoryMovementRead` — includes `movement_type: MovementTypeRead`, `item_name`, `master_sku`, `quantity`, `is_inbound`
- `InventoryMovementCreate` — body: `warehouse_id`, `movement_type_id`, `item_id`, `transactions[]` (each: `location_id`, `is_inbound`, `quantity_change`), optional `reference_number`, `notes`. **Note (v0.6.4):** movements are now created with `status="pending"` and stock levels are NOT updated on creation — use the lifecycle endpoints below to transition and trigger stock changes
- `AlertResolveRequest` — body: optional `resolution_notes`
- `ReserveResponse` — `item_id`, `quantity_reserved`, `warehouse_id`
- `BulkGenerateRequest` — body: optional `SegmentRange` for each of `section`, `zone`, `aisle`, `rack`, `bin`; each range has `prefix`, `start`, `end`, `pad` (range mode) or `values` (list mode); plus optional `inventory_type_id`, `is_active`
- `BulkGenerateResponse` — `warehouse_id`, `total_requested`, `created`, `skipped`, `errors[]` (each: `location`, `reason`)
- `InventoryLevelUpdate` — body: optional `reorder_point`, `safety_stock`, `max_stock` (all nullable integers)
- `MovementPerDayRead` — `date` (string), `movement_type` (string), `count` (integer)
- `TopMovedItemRead` — `item_id`, `item_name`, `master_sku`, `total_quantity`
- `StockHealthEntry` — `status` (string), `count` (integer)

### Movement Lifecycle Endpoints (v0.6.4–v0.6.5)

**WHY these exist:** Previously, `POST /warehouse/movements` immediately updated stock levels on creation. In a real warehouse workflow, movements should go through a lifecycle (pending → in_transit → completed) so stock changes are tied to deliberate human actions — not automatic side effects of record creation. These three endpoints manage the transitions and trigger the appropriate stock mutations at each step.

#### `PATCH /api/v1/warehouse/movements/{id}/approve`

**Description:** Transition a movement from `pending` to `in_transit`. Deducts outbound stock from the source location's inventory level. This represents the physical act of picking items from a shelf and loading them for transport.
**Files:** `backend/app/routers/warehouse.py`
**Tags:** Warehouse
**Auth:** Bearer JWT required

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `id` | integer | Movement ID |

**Request:** No body required.

**Response:** `200 OK`
```json
{
  "id": 42,
  "status": "in_transit",
  "message": "Movement approved. Outbound stock deducted from source location."
}
```

**Error Responses:**
- `401` — Not authenticated
- `404` — Movement not found
- `409` — Movement is not in `pending` status (cannot approve)
- `422` — Insufficient stock at source location

#### `PATCH /api/v1/warehouse/movements/{id}/complete`

**Description:** Transition a movement from `in_transit` to `completed`. Adds inbound stock at the destination location's inventory level. This represents the physical receipt of goods at the destination warehouse/location.
**Files:** `backend/app/routers/warehouse.py`
**Tags:** Warehouse
**Auth:** Bearer JWT required

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `id` | integer | Movement ID |

**Request:** No body required.

**Response:** `200 OK`
```json
{
  "id": 42,
  "status": "completed",
  "message": "Movement completed. Inbound stock added at destination location."
}
```

**Error Responses:**
- `401` — Not authenticated
- `404` — Movement not found
- `409` — Movement is not in `in_transit` status (cannot complete)

#### `PATCH /api/v1/warehouse/movements/{id}/cancel`

**Description:** Cancel a movement from either `pending` or `in_transit` status. If the movement was `in_transit` (outbound stock already deducted), the deduction is reversed — stock is added back to the source location. If the movement was `pending` (no stock changes yet), cancellation is a status-only change with no stock mutations.
**Files:** `backend/app/routers/warehouse.py`
**Tags:** Warehouse
**Auth:** Bearer JWT required

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `id` | integer | Movement ID |

**Request:** No body required.

**Response:** `200 OK`
```json
{
  "id": 42,
  "status": "cancelled",
  "message": "Movement cancelled. Outbound stock reversed.",
  "stock_reversed": true
}
```

**Error Responses:**
- `401` — Not authenticated
- `404` — Movement not found
- `409` — Movement is already `completed` or `cancelled` (cannot cancel)

### Movement Item Detail (v0.6.6)

**WHY this exists:** The movements list shows one row per movement, but warehouse staff need to drill into a movement to see which items moved and between which locations. This endpoint returns enriched transaction details with human-readable location codes and item names. For transfers, outbound/inbound pairs are grouped into single rows so users see one clear "from → to" entry per item instead of two confusing separate transactions.

#### `GET /api/v1/warehouse/movements/{id}/items`

**Description:** Returns per-item transaction detail for a specific movement, enriched with item name, master SKU, and location codes. Transfer movements group outbound/inbound pairs into single rows.
**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`
**Tags:** Warehouse
**Auth:** No

**Path Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Movement ID |

**Response:** `200 OK` — `MovementItemDetailRead[]`
```json
[
  {
    "item_id": 42,
    "item_name": "Widget A",
    "master_sku": "WDG-A-001",
    "location_from": "WH1-A-01-01",
    "location_to": "WH1-B-02-03",
    "quantity": 10,
    "is_inbound": false
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | integer | Item ID |
| `item_name` | string | Item display name |
| `master_sku` | string \| null | Item master SKU code |
| `location_from` | string \| null | Source location code (null for receipts) |
| `location_to` | string \| null | Destination location code (null for shipments) |
| `quantity` | number | Quantity moved |
| `is_inbound` | boolean | Whether this is an inbound transaction |

**Error Responses:**
- `404` — Movement not found

---

### Inventory Level Threshold Update (v0.6.9)

#### `PATCH /api/v1/warehouse/inventory-levels/{level_id}`

**Description:** Update threshold fields on an inventory level record. Allows warehouse operators to adjust reorder_point, safety_stock, and max_stock inline without editing the database directly. Only provided fields are updated (partial update).
**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`
**Tags:** Warehouse
**Auth:** Bearer JWT required

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `level_id` | integer | Inventory level ID |

**Request:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reorder_point` | integer \| null | No | Quantity threshold that triggers reorder alerts |
| `safety_stock` | integer \| null | No | Minimum safety stock buffer |
| `max_stock` | integer \| null | No | Maximum stock capacity for the location |

```json
{
  "reorder_point": 50,
  "safety_stock": 20,
  "max_stock": 500
}
```

**Response:** `200 OK` — Returns the updated `InventoryLevelRead` object with all fields including the updated thresholds.

**Error Responses:**
- `404` — Inventory level not found

---

### Analytics Endpoints (v0.6.9)

**WHY these exist:** Warehouse managers need aggregated, visual insights into movement patterns and stock health to make informed decisions about demand planning, staffing, and reorder timing. Raw movement lists and inventory levels alone do not surface trends or anomalies. These three endpoints provide the data behind the analytics dashboard charts.

#### `GET /api/v1/warehouse/{warehouse_id}/analytics/movements-per-day`

**Description:** Returns daily movement counts grouped by movement type over a date range. Powers the DailyMovementChart stacked bar chart on the analytics dashboard.
**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`
**Tags:** Warehouse
**Auth:** No

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `warehouse_id` | integer | Warehouse ID |

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date_from` | date (YYYY-MM-DD) | No | Start date for the range (inclusive). Defaults to 30 days ago |
| `date_to` | date (YYYY-MM-DD) | No | End date for the range (inclusive). Defaults to today |

**Response:** `200 OK`
```json
[
  {
    "date": "2026-03-01",
    "movement_type": "Receipt",
    "count": 12
  },
  {
    "date": "2026-03-01",
    "movement_type": "Shipment",
    "count": 8
  },
  {
    "date": "2026-03-02",
    "movement_type": "Transfer",
    "count": 3
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `date` | string (date) | The calendar date |
| `movement_type` | string | Name of the movement type |
| `count` | integer | Number of movements of this type on this date |

---

#### `GET /api/v1/warehouse/{warehouse_id}/analytics/top-items`

**Description:** Returns the top N items by total quantity moved within a date range. Powers the TopMovedItemsList ranked display on the analytics dashboard.
**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`
**Tags:** Warehouse
**Auth:** No

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `warehouse_id` | integer | Warehouse ID |

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date_from` | date (YYYY-MM-DD) | No | Start date for the range (inclusive). Defaults to 30 days ago |
| `date_to` | date (YYYY-MM-DD) | No | End date for the range (inclusive). Defaults to today |
| `limit` | integer | No | Number of top items to return. Defaults to 10 |

**Response:** `200 OK`
```json
[
  {
    "item_id": 42,
    "item_name": "Widget A",
    "master_sku": "WDG-A-001",
    "total_quantity": 1250
  },
  {
    "item_id": 17,
    "item_name": "Gadget B",
    "master_sku": "GDG-B-003",
    "total_quantity": 980
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | integer | Item ID |
| `item_name` | string | Item display name |
| `master_sku` | string \| null | Item master SKU code |
| `total_quantity` | number | Sum of all quantities moved (absolute) within the date range |

---

#### `GET /api/v1/warehouse/{warehouse_id}/analytics/stock-health`

**Description:** Returns the count of items in each stock status category for the warehouse. Powers the StockHealthSummary donut chart on the analytics dashboard.
**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`
**Tags:** Warehouse
**Auth:** No

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `warehouse_id` | integer | Warehouse ID |

**Response:** `200 OK`
```json
[
  { "status": "healthy", "count": 142 },
  { "status": "low", "count": 23 },
  { "status": "critical", "count": 5 },
  { "status": "out_of_stock", "count": 2 },
  { "status": "overstock", "count": 8 }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Stock status category (healthy, low, critical, out_of_stock, overstock) |
| `count` | integer | Number of inventory level records in this status |

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
| `frontend/src/api/base_types/warehouse.ts` | — | TypeScript types for all warehouse/inventory entities (includes `MovementPerDay`, `TopMovedItem`, `StockHealthEntry`, `AnalyticsDateRange`, `InventoryLevelUpdatePayload`) |
| `frontend/src/api/base/warehouse.ts` | `GET/POST/PATCH /api/v1/warehouse/*` | `listWarehouses()`, `getWarehouse()`, `createWarehouse()`, `updateWarehouse()`, `listLocations()`, `listInventoryLevels()`, `updateInventoryLevel()`, `listAlerts()`, `resolveAlert()`, `listMovementTypes()`, `listMovements()`, `createMovement()`, `approveMovement()`, `completeMovement()`, `cancelMovement()`, `getMovementItems()`, `getMovementsPerDay()`, `getTopItems()`, `getStockHealth()` — 19 functions total |

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

---

## Stock Check (Cycle Count) — V2

**Status flow:** `DRAFT` → `IN_PROGRESS` → `PENDING_REVIEW` ↔ `RECOUNT_REQUESTED` → `COMPLETED` / `CANCELLED`

**Files:** `backend/app/routers/stock_check.py`, `backend/app/schemas/stock_check.py`, `backend/app/models/stock_check.py`

### `GET /api/v1/stock-check/thresholds/{warehouse_id}`

**Description:** Get approval threshold configuration for a warehouse. Returns defaults if no config exists.
**Response:** `200 OK` — `StockCheckThresholdConfigRead`

### `PUT /api/v1/stock-check/thresholds/{warehouse_id}`

**Description:** Create or update approval thresholds for a warehouse.
**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `l1_always_required` | bool | No | L1 (Supervisor) always required (default: true) |
| `l2_variance_threshold` | int | No | Net variance items to trigger L2 (default: 10) |
| `l2_shrinkage_threshold` | int | No | Shrinkage items to trigger L2 (default: 5) |
| `l3_variance_threshold` | int | No | Net variance items to trigger L3 (default: 50) |

**Response:** `200 OK` — `StockCheckThresholdConfigRead`

### `POST /api/v1/stock-check`

**Description:** Create a new stock check session (status=draft).
**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `warehouse_id` | int | Yes | Target warehouse |
| `title` | string | Yes | Session title (1-200 chars) |
| `notes` | string | No | Optional notes |
| `scope_filters` | object | No | Scope: `{"warehouse_section":"A","zone":"DRY"}` |
| `blind_count_enabled` | bool | No | V2: Hide system qty from counters (default: false) |

**Response:** `201 Created` — `StockCheckRead` object

### `GET /api/v1/stock-check`

**Description:** List stock checks for a warehouse (paginated).
**Query params:** `warehouse_id` (required), `status` (optional filter), `page`, `page_size`
**Response:** `200 OK` — `PaginatedResponse<StockCheckRead>`

### `GET /api/v1/stock-check/{id}`

**Description:** Get stock check detail with all lines, approvals, and enhanced line data.
**Response:** `200 OK` — `StockCheckDetailRead` (includes `lines: StockCheckLineRead[]`, `approvals: StockCheckApprovalRead[]`, `blind_count_enabled`)

### `PATCH /api/v1/stock-check/{id}/start`

**Description:** Start a stock check — snapshots system quantities, populates lines with `line_status = "pending"`. Transitions `draft` → `in_progress`.
**Response:** `200 OK` — `StockCheckDetailRead` with populated lines

### `POST /api/v1/stock-check/{id}/count`

**Description:** Submit physical counts for one or more lines. V2: Stores `first_count`, sets `counted_by`, `line_status = "counted"`, logs audit history.
**Request:** `{ "counts": [{ "line_id": 1, "counted_quantity": 50, "notes": "...", "discrepancy_reason": "damaged" }] }`
**Response:** `200 OK` — `StockCheckDetailRead` with updated counts and variance calculations

### `PATCH /api/v1/stock-check/{id}/review`

**Description:** Submit for review. All lines must be counted. V2: Creates `StockCheckApproval` rows based on warehouse threshold config (L1/L2/L3). Transitions `in_progress` → `pending_review`.
**Response:** `200 OK` — `StockCheckDetailRead` with approvals populated
**Error:** `400` if any lines are uncounted

### `POST /api/v1/stock-check/{id}/approval`

**Description:** V2: Submit an approval action (approve or reject) for a specific level.
**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `approval_level` | string | Yes | L1, L2, or L3 |
| `action` | string | Yes | `approved` or `rejected` |
| `notes` | string | No | Optional notes |

**Response:** `200 OK` — `StockCheckDetailRead`
**Error:** `404` if approval level not found, `400` if already actioned

### `POST /api/v1/stock-check/{id}/recount-request`

**Description:** V2: Approver flags specific lines for blind re-count. Sets `recount_requested = true` on lines, transitions check to `recount_requested`.
**Request:** `{ "line_ids": [1, 2, 3], "notes": "High-value items need verification" }`
**Response:** `200 OK` — `StockCheckDetailRead`
**Error:** `400` if not in `pending_review` status

### `POST /api/v1/stock-check/{id}/recount`

**Description:** V2: Counter submits second counts for flagged lines. Stores `second_count`, sets `recounted_by`, transitions back to `pending_review`.
**Request:** `{ "counts": [{ "line_id": 1, "counted_quantity": 48 }] }`
**Response:** `200 OK` — `StockCheckDetailRead`
**Error:** `400` if not in `recount_requested` status

### `POST /api/v1/stock-check/{id}/reconcile`

**Description:** V2 (REPLACED): Set `final_accepted_qty` per variance line with structured reason codes. Does NOT update inventory — that requires a separate `adjust-inventory` call.
**Request:** `{ "line_actions": [{ "line_id": 1, "final_accepted_qty": 48, "discrepancy_reason": "damaged", "notes": "..." }] }`
**Response:** `200 OK` — `StockCheckDetailRead`
**Error:** `400` if not in `pending_review` or required approvals incomplete

### `POST /api/v1/stock-check/{id}/ghost-items`

**Description:** Capture found/ghost items during a stock check. Creates new lines with `is_ghost_inventory=true`, `system_quantity=0`, `line_status=counted`. Only allowed when status is `in_progress` or `recount_requested`.
**Request body:** `GhostItemBatchCapture` — `{ items: [{ item_id, location_id, counted_quantity, found_item_notes? }] }`
**Response:** `200 OK` — `StockCheckDetailRead` with new ghost lines appended
**Error:** `400` if check is not in countable state

### `POST /api/v1/stock-check/{id}/resolve-ghosts`

**Description:** Batch resolve ghost inventory lines. Each action sets `ghost_resolution` (create_record / flag_for_review / dispose), `ghost_resolved_at`, `ghost_resolved_by`. Only allowed when status is `pending_review`.
**Request body:** `GhostResolutionBatch` — `{ actions: [{ line_id, resolution, notes? }] }`
**Response:** `200 OK` — `StockCheckDetailRead` with resolved ghost lines
**Error:** `400` if line is not a ghost item or already resolved

### `POST /api/v1/stock-check/{id}/adjust-inventory`

**Description:** V2: Final step — creates a Cycle Count `InventoryMovement` with transactions for each reconciled line. Sets `is_reconciled = true`, transitions to `completed`.
**Response:** `200 OK` — `StockCheckRead` with `adjustment_movement_id` set
**Error:** `400` if lines not reconciled; `409` if unresolved ghost items exist (ghost gate)

### `GET /api/v1/stock-check/{id}/history`

**Description:** V2: Get audit trail for a stock check's lines.
**Query params:** `line_id` (optional — filter to a single line)
**Response:** `200 OK` — `StockCheckLineHistoryRead[]`

### `PATCH /api/v1/stock-check/{id}/cancel`

**Description:** Cancel a stock check (no stock changes). Works from `draft`, `in_progress`, `pending_review`, or `recount_requested`.
**Response:** `200 OK` — `StockCheckRead` with status=cancelled

---

## Functional Zone Configuration

**Base path:** `/api/v1/warehouse/{warehouse_id}/zones`
**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`, `backend/app/models/warehouse.py`
**Tags:** Warehouse
**Auth:** All endpoints require Bearer JWT

### `GET /api/v1/warehouse/{warehouse_id}/zones`
**Description:** List all functional zone configs for a warehouse. Returns empty array if none configured.
**Response:** `200 OK` — `FunctionalZoneConfigRead[]`

### `PUT /api/v1/warehouse/{warehouse_id}/zones`
**Description:** Batch upsert — replaces ALL zone configs for this warehouse. Deletes existing, inserts new.
**Request:** `application/json`

```json
{
  "zones": [
    {
      "zone_key": "returns",
      "zone_name": "Returns Processing",
      "description": "Inbound returns inspection",
      "color": "bg-orange-100 text-orange-700 border-orange-200",
      "icon": "undo",
      "mapped_sections": ["SEC-A"],
      "mapped_zones": ["Z1"]
    }
  ]
}
```

**Response:** `200 OK` — `FunctionalZoneConfigRead[]`

---

## Location Occupancy

**Base path:** `/api/v1/warehouse/{warehouse_id}/locations/occupancy`
**Tags:** Warehouse

### `GET /api/v1/warehouse/{warehouse_id}/locations/occupancy`
**Description:** Get occupancy status for all active locations in a warehouse. Returns per-location summary with stock counts, reserved quantities, slot counts, and computed occupancy status.
**Response:** `200 OK` — `LocationOccupancyRead[]`

Each item includes:
| Field | Type | Description |
|-------|------|-------------|
| `location_id` | integer | Location ID |
| `location_code` | string | Display code |
| `warehouse_section` | string? | Section name |
| `zone` | string? | Zone name |
| `aisle` | string? | Aisle name |
| `bay` | string? | Bay name |
| `max_capacity` | integer? | Max capacity (null = unlimited) |
| `total_quantity` | integer | Sum of quantity_available at this location |
| `reserved_quantity` | integer | Sum of reserved_quantity at this location |
| `slot_count` | integer | Number of active slot assignments |
| `occupancy_status` | string | `empty`, `reserved`, `occupied`, or `full` |

---

## Location Allocation (Slotting)

### `GET /api/v1/warehouse/{wh_id}/slots`

**Description:** List all slot assignments for a warehouse (paginated).
**Query params:** `item_id`, `location_id`, `is_active` (all optional), `page`, `page_size`
**Response:** `200 OK` — `PaginatedResponse<LocationSlotRead>`

### `POST /api/v1/warehouse/{wh_id}/slots`

**Description:** Create a slot assignment. Validates item exists, location belongs to warehouse, uniqueness.
**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_id` | int | Yes | Item to assign |
| `location_id` | int | Yes | Target location |
| `is_primary` | bool | No | Primary home (default false) |
| `max_quantity` | int | No | Max units at this slot (null=unlimited) |
| `priority` | int | No | Pick priority, lower=first (default 0) |
| `allocation_source` | string | No | "manual", "ml_suggested", "ml_auto" |
| `notes` | string | No | Assignment notes |

**Response:** `201 Created` — `LocationSlotRead`

### `PATCH /api/v1/warehouse/slots/{id}`

**Description:** Update a slot assignment (is_primary, max_quantity, priority, notes, is_active).
**Response:** `200 OK` — `LocationSlotRead`

### `DELETE /api/v1/warehouse/slots/{id}`

**Description:** Remove a slot assignment. Blocked if stock is present at the location.
**Response:** `204 No Content`
**Error:** `400` if stock still present

### `GET /api/v1/warehouse/{wh_id}/slots/item/{item_id}`

**Description:** Get all active slots for an item in a warehouse, ordered by priority.
**Response:** `200 OK` — `LocationSlotRead[]`

### `GET /api/v1/warehouse/{wh_id}/slots/location/{loc_id}`

**Description:** Get all active slots at a location, ordered by priority.
**Response:** `200 OK` — `LocationSlotRead[]`

### `POST /api/v1/warehouse/{wh_id}/slots/bulk`

**Description:** Bulk assign items to locations.
**Request:** `{ "slots": [{ "item_id": 1, "location_id": 5, "is_primary": true }] }`
**Response:** `200 OK` — `{ "created": N, "failed": M, "results": [...] }`

### `GET /api/v1/warehouse/{wh_id}/capacity`

**Description:** Location capacity overview for all active locations.
**Response:** `200 OK` — `CapacityOverviewItem[]` with location_code, max_capacity, current_utilization, utilization_pct, slot_count

---

## Multi-Item Movement (v2)

### `POST /api/v1/warehouse/movements/v2`

**Description:** Create a multi-item movement. Supports Receipt, Shipment, Transfer, Adjustment, Return, Write Off. Validates stock sufficiency for outbound, allocation enforcement for inbound (items must have LocationSlot at destination), slot capacity, and location capacity.
**Files:** `backend/app/routers/warehouse.py`, `backend/app/schemas/warehouse.py`

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `warehouse_id` | int | Yes | Warehouse context |
| `movement_type_id` | int | Yes | Movement type (from /movement-types) |
| `source_location_id` | int | Conditional | Required for Shipment, Transfer, Adjustment, Write Off |
| `destination_location_id` | int | Conditional | Required for Receipt, Transfer, Return |
| `items` | array | Yes | `[{ "item_id": int, "quantity": int }]` (1-100 items) |
| `reference_number` | string | No | External reference (PO number, etc.) |
| `notes` | string | No | Movement notes |

**Response:** `201 Created` — `InventoryMovementRead`
**Errors:**
- `400` — Item not allocated to destination, capacity exceeded, insufficient stock, duplicate items
- `404` — Movement type, item, or location not found

---

## Reference Number Generation Engine (Sequence)

Base prefix: `/api/v1/sequence`
**Files:** `backend/app/routers/sequence.py`, `backend/app/services/sequence.py`, `backend/app/schemas/sequence.py`, `backend/app/models/system.py`

### `GET /api/v1/sequence/modules`
**Description:** List all supported modules with allowed segment types, table_exists flag, and active config status.
**Response:** `200 OK` — `ModuleInfo[]`

### `GET /api/v1/sequence/stats/{module}`
**Description:** Get counter stats and count of entities missing references for a module.
**Response:** `200 OK` — `ModuleStats`

### `GET /api/v1/sequence/convention?module={name}`
**Description:** Get the active convention for a module.
**Response:** `200 OK` — `ConventionRead` | `404` if no active convention

### `GET /api/v1/sequence/convention/history?module={name}`
**Description:** Get all convention versions for a module (newest first).
**Response:** `200 OK` — `ConventionRead[]`

### `POST /api/v1/sequence/convention`
**Description:** Create a new convention version. Auto-activates and deactivates previous active version. Validates segments against module allowlist.
**Request:** `ConventionCreate` (module_name, name, separator, barcode_format, segments[], padding_length, reset_period, is_gapless, auto_apply_on_create, gs1_company_prefix)
**Response:** `201 Created` — `ConventionRead`

### `POST /api/v1/sequence/convention/{config_id}/activate`
**Description:** Rollback: activate a specific historical convention version.
**Response:** `200 OK` — `ConventionRead`

### `POST /api/v1/sequence/convention/preview`
**Description:** Render preview from draft convention payload. No DB write, no counter increment.
**Request:** `PreviewRequest` (module_name, segments[], separator, padding_length, gs1_company_prefix, sample_entity_id)
**Response:** `200 OK` — `PreviewResponse` (rendered string + segment breakdown)

### `POST /api/v1/sequence/generate/{module}/{entity_id}`
**Description:** Generate and persist a reference number for a single entity. Acquires FOR UPDATE lock, increments counter. For ORDER module: skips if platform_order_id exists.
**Response:** `200 OK` — `GenerateResult` | `409` if ORDER has platform ID | `501` if module table not implemented

### `POST /api/v1/sequence/generate/{module}/bulk`
**Description:** Bulk-generate references for all entities missing one in the target field.
**Response:** `200 OK` — `BulkGenerateResult` (total, success, failed, errors[])

### `POST /api/v1/sequence/reset-offset/{module}`
**Description:** Soft-reset: snapshot current counter as new offset (display counter goes to 0).
**Response:** `200 OK` — `ConventionRead`

---

## Inter-Warehouse Transfers

Base prefix: `/api/v1/transfers`
**Files:** `backend/app/routers/transfer.py`, `backend/app/models/transfer.py`, `backend/app/schemas/transfer.py`

### `POST /api/v1/transfers`
**Description:** Create a transfer draft. Validates warehouses are different and active, items exist, source locations belong to source warehouse. No stock deduction — draft only.
**Request:** `TransferCreate` — `{ source_warehouse_id, destination_warehouse_id, items: [{ item_id, source_location_id, quantity }], notes? }`
**Response:** `201 Created` — `TransferDetailRead`

### `GET /api/v1/transfers`
**Description:** List transfers for a warehouse. Paginated with direction and status filters.
**Query params:** `warehouse_id` (required), `direction` (outgoing|incoming), `status`, `page`, `page_size`
**Response:** `200 OK` — `PaginatedResponse<TransferRead>`

### `GET /api/v1/transfers/{id}`
**Description:** Get transfer detail with all lines (item names, SKUs, barcodes, location codes).
**Response:** `200 OK` — `TransferDetailRead`

### `GET /api/v1/transfers/by-reference/{reference_number}`
**Description:** Look up a transfer by reference number. Key endpoint for barcode scanning at receiving end.
**Response:** `200 OK` — `TransferDetailRead` | `404`

### `GET /api/v1/transfers/incoming/{warehouse_id}`
**Description:** Incoming transfer schedule — lists draft/shipped transfers destined for this warehouse. Shipped items sorted first.
**Query params:** `page`, `page_size`
**Response:** `200 OK` — `PaginatedResponse<TransferRead>`

### `PATCH /api/v1/transfers/{id}/confirm-packing`
**Description:** Confirm that all items for a transfer are packed. Sets packing_confirmed=true. Must be in 'draft' status.
**Request:** `TransferPackingConfirm` — `{ notes? }`
**Response:** `200 OK` — `TransferDetailRead`

### `PATCH /api/v1/transfers/{id}/ship`
**Description:** Ship a draft transfer. Requires packing to be confirmed first. Creates outbound InventoryMovement at source warehouse, deducts stock from source locations. Validates ATP availability before deducting.
**Transition:** `draft` (packed) → `shipped`
**Error:** `400` if packing not confirmed
**Response:** `200 OK` — `TransferDetailRead`

### `POST /api/v1/transfers/{id}/verify`
**Description:** Submit scanned quantities for verification. Computes per-line status (matched/short/over/missing). Now accepts per-line discrepancy reasons.
**Transition:** `shipped` → `received`
**Request:** `TransferVerifyRequest` — `{ lines: [{ line_id, received_quantity, notes?, discrepancy_reason? }] }`
**Response:** `200 OK` — `TransferDetailRead`

### `POST /api/v1/transfers/{id}/complete`
**Description:** Complete a verified transfer. Creates inbound InventoryMovement at destination. Requires `discrepancy_notes` if mismatches. Builds JSONB discrepancy_report snapshot. Saves receiver_notes.
**Transition:** `received` → `completed`
**Request:** `TransferCompleteRequest` — `{ discrepancy_notes?, receiver_notes? }`
**Response:** `200 OK` — `TransferRead`

### `PATCH /api/v1/transfers/{id}/cancel`
**Description:** Cancel a transfer. If already shipped, reverses the outbound movement (restores stock at source).
**Transition:** `draft`/`shipped` → `cancelled`
**Response:** `200 OK` — `TransferRead`

### `GET /api/v1/transfers/{id}/print-data`
**Description:** Get structured data for printing a Transfer Order document. Includes warehouse addresses, all lines, and barcode-ready reference number.
**Response:** `200 OK` — `TransferPrintData`

---

## Receiving Sessions (Inbound Goods Verification)

Base prefix: `/api/v1/receiving`
**Files:** `backend/app/routers/receiving.py`, `backend/app/models/receiving.py`, `backend/app/schemas/receiving.py`

**Lifecycle:** DRAFT → IN_PROGRESS → PENDING_REVIEW → COMPLETED / CANCELLED

### `POST /api/v1/receiving`
**Description:** Create a new receiving session with optional expected item lines.
**Request:** `ReceivingSessionCreate` — `{ warehouse_id, title, supplier_name?, purchase_order_ref?, notes?, source_type? ('supplier_shipment'|'customer_return'|'inter_warehouse'), linked_return_id?, lines?: [{ item_id, expected_quantity, location_id? }] }`
**Response:** `201 Created` — `ReceivingSessionDetailRead`

### `GET /api/v1/receiving`
**Description:** List receiving sessions for a warehouse. Paginated with status filter.
**Query params:** `warehouse_id` (required), `status`, `page`, `page_size`
**Response:** `200 OK` — `PaginatedResponse<ReceivingSessionRead>`

### `GET /api/v1/receiving/{id}`
**Description:** Get session detail with all lines (enriched with item names, SKUs, location codes).
**Response:** `200 OK` — `ReceivingSessionDetailRead`

### `PATCH /api/v1/receiving/{id}/start`
**Description:** Start receiving. Transitions draft → in_progress.
**Response:** `200 OK` — `ReceivingSessionRead`

### `PATCH /api/v1/receiving/{id}/cancel`
**Description:** Cancel the session. No stock changes.
**Response:** `200 OK` — `ReceivingSessionRead`

### `PATCH /api/v1/receiving/{id}/lines/{line_id}/count`
**Description:** Update received quantity for a single line.
**Request:** `ReceivingLineCountUpdate` — `{ received_quantity, notes? }`
**Response:** `200 OK` — `ReceivingLineRead`

### `POST /api/v1/receiving/{id}/scan`
**Description:** Scan a barcode/SKU. Resolves to an item, finds or creates a line, increments count. Auto-starts session if still draft.
**Request:** `ReceivingScanRequest` — `{ barcode, quantity? }`
**Response:** `200 OK` — `ReceivingScanResponse` (includes line_id, item info, updated counts, is_new_line flag)

### `POST /api/v1/receiving/{id}/lines`
**Description:** Add a new item line to the session (for unexpected items).
**Request:** `ReceivingLineAdd` — `{ item_id, received_quantity?, expected_quantity?, location_id?, notes? }`
**Response:** `201 Created` — `ReceivingLineRead`

### `POST /api/v1/receiving/{id}/lines/unexpected`
**Description:** Add an unexpected item discovered during receiving. Sets `is_unexpected=true`, `expected_quantity=0`. Only available in `in_progress` status.
**Request:** `UnexpectedLineCreate` — `{ item_id, received_quantity, location_id?, unexpected_notes? }`
**Response:** `201 Created` — `ReceivingLineRead`

### `POST /api/v1/receiving/{id}/discrepancy-report`
**Description:** Submit a discrepancy report acknowledging unresolved differences. Sets `discrepancy_resolved=true` on the session, which unlocks the completion gate.
**Request:** `DiscrepancyReportCreate` — `{ notes, accept_discrepancies: true }`
**Response:** `200 OK` — `ReceivingSessionRead`

### `PATCH /api/v1/receiving/{id}/complete`
**Description:** Complete the session. Creates Receipt movements for all lines with received_quantity > 0, updates InventoryLevel. Transitions to completed. **Returns 409 Conflict** if there are unresolved discrepancies or unexpected items and `discrepancy_resolved` is still false.
**Response:** `200 OK` — `ReceivingSessionRead` | `409 Conflict` — discrepancy gate

### `GET /api/v1/receiving/{id}/discrepancy-report`
**Description:** Get discrepancy report — lines where expected ≠ received.
**Response:** `200 OK` — `DiscrepancyReport` (summary counts + list of discrepancy lines with difference)

### Document Management

### `POST /api/v1/receiving/{session_id}/documents`
**Description:** Upload a file attachment to a receiving session. Any file type, max 10 MB.
**Request:** `multipart/form-data` — `file` field
**Response:** `201 Created` — `ReceivingDocumentRead` `{ id, session_id, movement_id, file_name, original_name, file_size, mime_type, uploaded_by, uploaded_at, download_url }`

### `POST /api/v1/receiving/documents/movement/{movement_id}`
**Description:** Upload a file attachment to an inventory movement (e.g., quick stock-in). Any file type, max 10 MB.
**Request:** `multipart/form-data` — `file` field
**Response:** `201 Created` — `ReceivingDocumentRead`

### `GET /api/v1/receiving/{session_id}/documents`
**Description:** List all documents attached to a receiving session.
**Response:** `200 OK` — `ReceivingDocumentRead[]`

### `GET /api/v1/receiving/documents/movement/{movement_id}`
**Description:** List all documents attached to an inventory movement.
**Response:** `200 OK` — `ReceivingDocumentRead[]`

### `DELETE /api/v1/receiving/documents/{document_id}`
**Description:** Delete a document — removes file from disk and DB record.
**Response:** `204 No Content`

### Stock-In Verification (Serialized Items)

**Added in v0.11.0.** These endpoints implement the Print → Scan → Reconcile verification workflow for serialized items (`is_serialized=true`). Non-serialized items continue to use the existing quantity-based scan endpoint unchanged.

### `POST /api/v1/receiving/{session_id}/lines/{line_id}/print-labels`
**Description:** Generate N StockLot rows with unique serial numbers + barcodes for a serialized item. Each lot starts in `pending_verification` status. Returns label data for rendering/printing. Auto-starts the session if still in draft.
**Request:** `{ quantity: int (≥1), location_id: int }`
**Response:** `201 Created` — `PrintLabelsResponse { stock_lots: StockLotRead[], total_printed, line_id, item_name, master_sku }`
**Errors:** `400` if item not serialized, session not in draft/in_progress, or line not found

### `POST /api/v1/receiving/{session_id}/scan-serial`
**Description:** Verify a scanned unique barcode from a printed label. Transitions the StockLot from `pending_verification` to `verified`. Increments `ReceivingLine.received_quantity` and updates `InventoryLevel` counters.
**Request:** `{ barcode: string }`
**Response:** `200 OK` — `SerialScanResponse { stock_lot, line_id, item_id, item_name, master_sku, message }`
**Errors:** `409` if already verified (duplicate scan), voided, or belongs to different session; `400` if session not active

### `POST /api/v1/receiving/{session_id}/lots/{lot_id}/void`
**Description:** Void a specific StockLot with a mandatory reason. Adjusts inventory counters and receiving line quantities based on previous status. Requires selecting the exact lot — no "delete all" option.
**Request:** `{ reason: string (1-500 chars) }`
**Response:** `200 OK` — `StockLotRead`
**Errors:** `400` if already voided or lot doesn't belong to session

### `GET /api/v1/receiving/{session_id}/reconciliation`
**Description:** Get per-line reconciliation report showing printed vs scanned vs missing vs voided counts for all serialized items in the session. Used to gate session completion.
**Response:** `200 OK` — `ReconciliationReportRead { session_id, lines: ReconciliationLineRead[], all_reconciled }`

### `GET /api/v1/receiving/{session_id}/lots`
**Description:** List StockLots belonging to a receiving session with optional filters.
**Query params:** `line_id?`, `verification_status?` (pending_verification|verified|voided), `page` (default 1), `page_size` (default 50, max 200)
**Response:** `200 OK` — `PaginatedResponse<StockLotRead>`

### Modified Existing Endpoints (v0.11.0)

- **`POST /scan`** — Now auto-routes serialized items: if barcode is a StockLot serial → delegates to verification service; if barcode is generic item/SKU on a serialized item → returns error "Scan the unique barcode from the printed label"; non-serialized items → existing behavior unchanged. Response now includes `is_serialized: bool`.
- **`PATCH /complete`** — Added serialized reconciliation gate: blocks completion if any serialized lines have unscanned (pending) StockLots unless discrepancy is accepted. For serialized lines, only verified StockLots contribute to `quantity_available`.
- **`PATCH /cancel`** — Now bulk-voids all `pending_verification` StockLots with reason "Session cancelled".
- **`PATCH /lines/{line_id}/count`** — Now blocks manual quantity editing for serialized items with error "Cannot manually edit quantity for serialized items."

---

## Disposal (Stock Write-Off Approval Workflow)

**Base path:** `/api/v1/disposal`
**Files:** `backend/app/routers/disposal.py`, `backend/app/schemas/disposal.py`, `backend/app/models/disposal.py`
**Tags:** Disposal
**Auth:** All endpoints require Bearer JWT

### `POST /api/v1/disposal`
**Description:** Create a new disposal request. Validates stock availability and generates a reference number via the sequence engine. Initial status: `pending_approval`.
**Request:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `warehouse_id` | integer | Yes | Target warehouse ID |
| `item_id` | integer | Yes | Item to dispose |
| `location_id` | integer | No | Specific location (null = any) |
| `quantity` | integer | Yes | Quantity to dispose (min 1) |
| `reason` | string | Yes | One of: `damaged`, `expired`, `quality_failure`, `obsolete`, `contaminated`, `other` |
| `notes` | string | No | Additional notes |

**Response:** `201 Created` — `DisposalApprovalRead`

### `GET /api/v1/disposal`
**Description:** List disposal requests with pagination and filters.
**Query params:** `warehouse_id`, `status`, `requested_by`, `page` (default 1), `page_size` (default 20)
**Response:** `200 OK` — `PaginatedResponse<DisposalApprovalRead>`

### `GET /api/v1/disposal/pending-approval`
**Description:** Manager approval queue — returns only `pending_approval` disposals.
**Query params:** `warehouse_id`, `page`, `page_size`
**Response:** `200 OK` — `PaginatedResponse<DisposalApprovalRead>`

### `GET /api/v1/disposal/{id}`
**Description:** Get disposal detail with resolved names (warehouse, item, requester, approver).
**Response:** `200 OK` — `DisposalApprovalRead`

### `POST /api/v1/disposal/{id}/approve`
**Description:** Approve or reject a pending disposal. Approver can optionally reduce the quantity.
**Request:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `approved` or `rejected` |
| `rejection_reason` | string | If rejected | Reason for rejection |
| `edited_quantity` | integer | No | Reduced quantity (must be ≤ original) |
| `notes` | string | No | Approver notes |

**Response:** `200 OK` — `DisposalApprovalRead`
**Errors:** `400` if not pending, `404` if not found

### `POST /api/v1/disposal/{id}/execute`
**Description:** Execute an approved disposal — creates a Write Off movement, deducts stock from InventoryLevel, creates outbound InventoryTransaction. Status becomes `disposed`.
**Request:** No body
**Response:** `200 OK` — `DisposalApprovalRead`
**Errors:** `400` if not approved, `404` if not found, `400` if Write Off movement type not seeded

### `PATCH /api/v1/disposal/{id}/cancel`
**Description:** Cancel a disposal request. Only allowed when status is `pending_approval` or `rejected`.
**Request:** No body
**Response:** `200 OK` — `DisposalApprovalRead`
**Errors:** `400` if already approved/disposed/cancelled
