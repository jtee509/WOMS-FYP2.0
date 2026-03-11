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
| POST | `/api/v1/items/bundles` | Yes | Create bundle item + components in one transaction (201, 409/422) |
| PATCH | `/api/v1/items/bundles/{item_id}` | Yes | Update bundle metadata and/or replace components (200, 404/409/422) |
| DELETE | `/api/v1/items/bundles/{item_id}` | Yes | Soft-delete bundle (204, sets deleted_at + deactivates PlatformSKU listing) |
| POST | `/api/v1/items/bundles/{item_id}/restore` | Yes | Restore soft-deleted bundle (re-activates PlatformSKU listing, returns BundleReadResponse) |

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

**Description:** Bulk-import bundles from a CSV or Excel file. Each row represents one component of a bundle. Rows sharing the same `bundle_sku` are grouped into a single bundle. Metadata (name, category, brand, etc.) is taken from the first row per group. The backend validates component SKU existence, resolves FKs, enforces bundle composition rules, and creates Item + PlatformSKU + ListingComponent records per bundle.
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
- `422` — Unsupported file extension, no data rows, no active platform/seller, or "Bundle" item type not found

---

### `GET /api/v1/items/bundles`

**Description:** List all bundle-type items with component counts. Returns `BundleListItem` objects which extend `ItemRead` with `component_count` (distinct items) and `total_quantity` (sum of component quantities). Component counts are computed via LEFT JOIN on `listing_component` / `platform_sku` tables.
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

**Error Responses:**
- `404` — Bundle not found
- `422` — Item is not a Bundle type
- `500` — "Bundle" item type not seeded

### `POST /api/v1/items/bundles`

**Description:** Create a bundle item and its listing components in a single atomic transaction. Inserts into `items` (with `item_type = "Bundle"`), creates a `platform_sku` listing, and inserts component rows into `listing_component`. The `trg_items_history_on_insert` trigger automatically creates an audit trail record in `items_history`.
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
| `platform_id` | integer | Yes | Platform FK for the listing |
| `seller_id` | integer | Yes | Seller FK for the listing |
| `components` | array | Yes | At least 1 component; must have >1 distinct items or single item with qty > 1 |
| `components[].item_id` | integer | Yes | Existing item ID (must not be deleted) |
| `components[].quantity` | integer | Yes | Quantity of this item in the bundle (>= 1) |

```json
{
  "item_name": "Summer Essentials Pack",
  "master_sku": "BUNDLE-SUMMER-001",
  "category_id": 2,
  "platform_id": 1,
  "seller_id": 1,
  "components": [
    { "item_id": 10, "quantity": 2 },
    { "item_id": 25, "quantity": 1 },
    { "item_id": 42, "quantity": 1 }
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
    "created_at": "2026-03-09T12:00:00",
    "updated_at": "2026-03-09T12:00:00"
  },
  "listing_id": 55,
  "platform_sku": "BUNDLE-SUMMER-001",
  "components": [
    { "id": 1, "item_id": 10, "item_name": "T-Shirt White", "master_sku": "TSHIRT-W-001", "quantity": 2 },
    { "id": 2, "item_id": 25, "item_name": "Cap Black", "master_sku": "CAP-B-001", "quantity": 1 },
    { "id": 3, "item_id": 42, "item_name": "Sunglasses", "master_sku": "SUN-001", "quantity": 1 }
  ]
}
```

**Validation Rules:**
1. `master_sku` must be unique across ALL items (409 if duplicate)
2. Bundle composition: must have >1 distinct component items, OR a single item with quantity > 1 (422 otherwise)
3. All component `item_id`s must exist and not be soft-deleted (422 if missing)
4. Item type "Bundle" must exist in `item_type` seed data (500 if missing)

**Error Responses:**
- `401` — Not authenticated
- `409` — Master SKU already exists
- `422` — Invalid bundle composition or component item_ids not found
- `500` — "Bundle" item type not seeded

### `PATCH /api/v1/items/bundles/{item_id}`

**Description:** Update a bundle's metadata (name, SKU, category, etc.) and/or replace its components. Uses a **delete-and-reinsert** strategy for components: when `components` is provided, all existing `listing_component` rows for this bundle are removed and replaced with the new set. Changing the bundle's `master_sku` only affects the bundle item — component item SKUs are never modified.
**Files:** `backend/app/routers/items.py`, `backend/app/schemas/items.py`
**Tags:** Items
**Auth:** Bearer JWT required

**Request:** `application/json` — all fields optional

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_name` | string | No | New bundle name |
| `master_sku` | string | No | New unique SKU for the bundle (max 100 chars). Updates PlatformSKU in sync. |
| `sku_name` | string | No | New SKU display name |
| `description` | string | No | Updated description |
| `image_url` | string | No | Updated image URL/path |
| `uom_id` | integer | No | Unit of measure FK |
| `brand_id` | integer | No | Brand FK |
| `category_id` | integer | No | Category FK |
| `is_active` | boolean | No | Toggle active status |
| `components` | array | No | If provided, replaces ALL existing components. Must satisfy bundle rules. |
| `components[].item_id` | integer | Yes* | Component item ID (must exist, not deleted) |
| `components[].quantity` | integer | Yes* | Quantity >= 1 |

```json
{
  "master_sku": "BUNDLE-SUMMER-V2",
  "sku_name": "Summer Pack V2",
  "components": [
    { "item_id": 10, "quantity": 3 },
    { "item_id": 25, "quantity": 1 },
    { "item_id": 50, "quantity": 2 }
  ]
}
```

**Response:** `200 OK` — same `BundleReadResponse` shape as POST

**Data Integrity:**
- Changing `master_sku` updates the bundle's items row AND the linked `platform_sku.platform_sku` — component item SKUs are never touched
- Changing `item_name` syncs to `platform_sku.platform_seller_sku_name`
- Changing `is_active` syncs to `platform_sku.is_active`
- Component replacement is atomic — if any validation fails, no components are changed

**Error Responses:**
- `401` — Not authenticated
- `404` — Bundle item not found, or no PlatformSKU listing found
- `409` — New master_sku already exists on another item
- `422` — Item is not a Bundle type, invalid component composition, or component item_ids not found
- `500` — "Bundle" item type not seeded

### `DELETE /api/v1/items/bundles/{item_id}`

**Description:** Soft-delete a bundle. Sets `deleted_at` and `deleted_by` on the items row and deactivates the associated PlatformSKU listing. The `listing_component` rows are preserved so the bundle can be fully restored later. The PostgreSQL trigger `trg_items_history_on_update` automatically records a `SOFT_DELETE` history entry in `items_history`.
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

**Description:** Restore a previously soft-deleted bundle. Clears `deleted_at` and `deleted_by` on the items row and re-activates the PlatformSKU listing. Components are still intact from the original soft-delete. The trigger records a `RESTORE` history entry.
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
| GET | `/api/v1/warehouse/{id}/inventory` | No | Enriched inventory levels — joins Item + Location, computed `stock_status`. Paginated. Params: `page`, `page_size`, `item_id`, `search`, `stock_status` |
| GET | `/api/v1/warehouse/movement-types` | No | List all movement types (Receipt, Shipment, Transfer, etc.) |
| GET | `/api/v1/warehouse/{id}/movements` | No | Movement history for a warehouse (paginated). Joins through transactions to get item info |
| POST | `/api/v1/warehouse/movements` | Yes | Record a stock movement (inbound/outbound/transfer). Creates movement + transactions, updates inventory levels |
| GET | `/api/v1/warehouse/{id}/alerts` | No | List inventory alerts (filter by `is_resolved`) |
| PATCH | `/api/v1/warehouse/alerts/{id}/resolve` | Yes | Mark an alert as resolved. Stores resolution notes + resolver user |
| POST | `/api/v1/warehouse/reserve` | Yes | Pessimistically reserve stock for a standalone item. Uses row-level lock to prevent oversell. Body: `item_id`, `quantity`, `warehouse_id` |
| POST | `/api/v1/warehouse/release` | Yes | Release a reservation (order cancelled). Body: `item_id`, `quantity`, `warehouse_id` |
| POST | `/api/v1/warehouse/fulfill/bundle` | Yes | Atomic bundle stock deduction. Deducts all BOM components in one transaction. Body: `bundle_item_id`, `bundle_qty_sold`, `warehouse_id`, `order_reference` |

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
- `InventoryMovementCreate` — body: `warehouse_id`, `movement_type_id`, `item_id`, `transactions[]` (each: `location_id`, `is_inbound`, `quantity_change`), optional `reference_number`, `notes`
- `AlertResolveRequest` — body: optional `resolution_notes`
- `ReserveResponse` — `item_id`, `quantity_reserved`, `warehouse_id`
- `BulkGenerateRequest` — body: optional `SegmentRange` for each of `section`, `zone`, `aisle`, `rack`, `bin`; each range has `prefix`, `start`, `end`, `pad` (range mode) or `values` (list mode); plus optional `inventory_type_id`, `is_active`
- `BulkGenerateResponse` — `warehouse_id`, `total_requested`, `created`, `skipped`, `errors[]` (each: `location`, `reason`)

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
| `frontend/src/api/base_types/warehouse.ts` | — | TypeScript types for all warehouse/inventory entities |
| `frontend/src/api/base/warehouse.ts` | `GET/POST/PATCH /api/v1/warehouse/*` | `listWarehouses()`, `getWarehouse()`, `createWarehouse()`, `updateWarehouse()`, `listLocations()`, `listInventoryLevels()`, `listAlerts()`, `resolveAlert()`, `listMovementTypes()`, `listMovements()`, `createMovement()` — 11 functions total |

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
