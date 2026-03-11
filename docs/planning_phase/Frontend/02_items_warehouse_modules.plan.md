---
name: Items and Warehouse Modules Plan
overview: Frontend plan for the Items (Master Catalog) and Warehouse (Inventory and Locations) modules. Defines component layouts, routes, and React Query API hooks for highly interactive item management and real-time inventory visibility.
todos: []
isProject: false
---

# Items and Warehouse Modules Plan

## Overview

This plan defines the frontend implementation for two core WOMS modules:

1. **Items Module (Master Catalog)** – Highly interactive UI for creating and managing items with variations (size, color, etc.)
2. **Warehouse Module (Inventory and Locations)** – Real-time visibility and action-taking for stock levels, movements, and alerts

---

## 1. Items Module (Master Catalog)

This module requires a highly interactive UI because creating and managing items—especially those with variations (size, color, etc.)—is typically the most complex data entry task for users.

### A. Component Layouts

#### `/catalog/items` (Master List)

| Aspect | Specification |
|--------|---------------|
| **Component** | `AdvancedDataTable` |
| **Features** | Server-side pagination, global search (`item_name` or `master_sku`), column filters (Brand, Category, Status) |
| **UX Detail** | **Row Expansion** – Clicking a parent item row drops down to reveal child variations (items where `parent_id` matches the clicked row's `item_id`) |

> **Note on search**: The backend `GET /api/v1/items` endpoint accepts a `search` query param that searches `item_name` or `master_sku` (not `sku_name`). Column filters map to `brand_id`, `category_id`, and `status_id` query params.

#### `/catalog/items/new` (Creation Wizard)

| Aspect | Specification |
|--------|---------------|
| **Component** | `ItemBuilderForm` (powered by React Hook Form) |
| **Layout** | Tabbed or multi-step layout |

**Tab 1: Basic Info**

- Name (`item_name`), SKU (`master_sku`), SKU Name (`sku_name`), Description, Type (`item_type_id`), Category (`category_id`), Brand (`brand_id`), UOM (`uom_id`)

**Tab 2: Variations**

- Dynamic field array where users define attributes (e.g. "Color") and values (e.g. "Red", "Blue")
- Frontend automatically generates a preview grid of the resulting SKUs to be saved in the `variations_data` JSONB column
- When `has_variation = true`, child items are created with `parent_id` pointing to this item

#### Attribute Management (Reference Data)

> **Already implemented.** The Settings page at `/settings` (v0.5.3) provides full CRUD for all 5 item attribute lookup tables: **Statuses**, **Item Types**, **Categories**, **Brands**, and **Units of Measure**. See `src/pages/SettingsPage.tsx` and `src/components/settings/AttributeCard.tsx`. No separate `/catalog/attributes` route is needed.

### B. API Hook Definitions (React Query Pattern)

| Hook | Method | Endpoint | Purpose |
|------|--------|----------|---------|
| `useGetItems(params)` | `GET` | `/api/v1/items?page=&page_size=&search=&category_id=&brand_id=&status_id=` | Fetches paginated item list. Response: `PaginatedResponse<ItemRead>` |
| `useGetItem(id)` | `GET` | `/api/v1/items/{item_id}` | Fetches single item with eager-loaded lookups (uom, brand, status, item_type, category) |
| `useGetItemAttributes()` | Parallel | `/api/v1/items/statuses`, `/api/v1/items/types`, `/api/v1/items/categories`, `/api/v1/items/brands`, `/api/v1/items/uoms` | Fetches all active attribute lists for `ItemBuilderForm` dropdowns. Reuses the existing functions from `src/api/base/items.ts` (`listStatuses`, `listItemTypes`, `listCategories`, `listBrands`, `listUOMs`) |
| `useCreateItem()` | `POST` | `/api/v1/items` | Submits `ItemCreate` payload. Auth required. On success, invalidate `useGetItems` cache |
| `useUpdateItem()` | `PATCH` | `/api/v1/items/{item_id}` | Submits `ItemUpdate` payload (partial update, only changed fields). Auth required |
| `useDeleteItem()` | `DELETE` | `/api/v1/items/{item_id}` | Soft-deletes the item (sets `deleted_at` + `deleted_by`). Auth required |

---

## 2. Warehouse Module (Inventory and Locations)

This module is less about data entry and more about real-time visibility and action-taking (movements, alerts).

> **PREREQUISITE:** The warehouse router exists at `backend/app/routers/warehouse.py` but is **currently commented out** in `backend/app/main.py` (line 222). It must be uncommented and registered before any warehouse frontend work begins:
> ```python
> from app.routers import warehouse
> app.include_router(warehouse.router, prefix=f"{settings.api_v1_prefix}/warehouse", tags=["Warehouse"])
> ```

### A. Component Layouts

#### `/inventory/levels` (Stock Matrix)

| Aspect | Specification |
|--------|---------------|
| **Component** | `InventoryGrid` |
| **Features** | Maps `inventory_levels` joined with `items` and `inventory_location`. Clearly shows `quantity_available` vs `reorder_point` |
| **Visuals** | Use `index.css` warning colors to highlight rows by stock status: `CRITICAL` (qty <= `safety_stock`), `LOW` (qty <= `reorder_point`), `OVERSTOCK` (qty >= `max_stock`), `OUT_OF_STOCK` (qty = 0) |
| **UX Detail** | Requires a warehouse selector dropdown first — the API is scoped per warehouse (`/warehouse/{warehouse_id}/inventory`) |

#### `/inventory/movements` (Stock Transactions)

| Aspect | Specification |
|--------|---------------|
| **Component** | `TransactionHistoryTable` |
| **Data** | Maps `inventory_transactions` and `inventory_movements` tables |
| **Action Modal** | `InventoryTransferModal` – A transfer creates an `InventoryMovement` record with `movement_type_id` (e.g. "Transfer"), then two `InventoryTransaction` records: one outbound (`is_inbound=false`) from source location and one inbound (`is_inbound=true`) to destination location. `quantity_change` is always positive. |

> **Backend gap:** No `POST /api/v1/warehouse/.../movements` endpoint exists yet. This must be implemented before the frontend modal can function. See Section 4.

#### `/inventory/alerts` (Action Center)

| Aspect | Specification |
|--------|---------------|
| **Component** | `AlertsKanban` or `AlertsList` |
| **Features** | Consumes `inventory_alerts` for a selected warehouse. Users click an alert to view details and click "Resolve", which opens a prompt to enter `resolution_notes` before marking `is_resolved = true` |
| **Alert Types** | `low_stock`, `out_of_stock`, `critical`, `overstock` |

> **Backend gap:** No resolve endpoint (`PATCH .../alerts/{id}/resolve`) exists yet. See Section 4.

#### `/inventory/warehouses` (Topology)

| Aspect | Specification |
|--------|---------------|
| **Component** | `LocationTreeViewer` |
| **Features** | Nested list or tree view showing hierarchy: **Section** → Zone → Aisle → Rack → Bin (`inventory_location` model). Each node in the tree maps to the `section`, `zone`, `aisle`, `rack`, `bin` columns. |
| **Data** | Fetched via `GET /api/v1/warehouse/{warehouse_id}/locations` |

### B. API Hook Definitions (React Query Pattern)

> **Important:** All warehouse endpoints are nested under `/api/v1/warehouse/{warehouse_id}/...` — they require a `warehouse_id` path param, not flat `/inventory/...` paths.

| Hook | Method | Endpoint | Purpose |
|------|--------|----------|---------|
| `useGetWarehouses(filters?)` | `GET` | `/api/v1/warehouse?is_active=true` | Lists all warehouses. Used for warehouse selector dropdown |
| `useGetWarehouse(id)` | `GET` | `/api/v1/warehouse/{warehouse_id}` | Single warehouse details |
| `useGetLocations(warehouseId)` | `GET` | `/api/v1/warehouse/{warehouse_id}/locations` | All locations in a warehouse for tree view |
| `useGetInventoryLevels(warehouseId, filters)` | `GET` | `/api/v1/warehouse/{warehouse_id}/inventory?page=&page_size=&item_id=` | Paginated stock levels. Response: `PaginatedResponse<InventoryLevelRead>` |
| `useGetAlerts(warehouseId, isResolved?)` | `GET` | `/api/v1/warehouse/{warehouse_id}/alerts?is_resolved=false` | Fetches active (or historical) alerts for a warehouse |
| `useProcessMovement()` | `POST` | `/api/v1/warehouse/movements` (**TO IMPLEMENT**) | Records inbound, outbound, or transfers. Payload creates an `InventoryMovement` + associated `InventoryTransaction` records |
| `useResolveAlert()` | `PATCH` | `/api/v1/warehouse/alerts/{id}/resolve` (**TO IMPLEMENT**) | Submits `{ resolved_by_user_id, resolution_notes }` to mark alert resolved |

---

## 3. Route Summary

| Route | Component | Module |
|-------|-----------|--------|
| `/catalog/items` | AdvancedDataTable | Items |
| `/catalog/items/new` | ItemBuilderForm | Items |
| `/catalog/items/:id/edit` | ItemBuilderForm (edit mode) | Items |
| `/inventory/levels` | InventoryGrid | Warehouse |
| `/inventory/movements` | TransactionHistoryTable + InventoryTransferModal | Warehouse |
| `/inventory/alerts` | AlertsKanban / AlertsList | Warehouse |
| `/inventory/warehouses` | LocationTreeViewer | Warehouse |

> **Removed:** `/catalog/attributes` — already covered by the Settings page at `/settings` (v0.5.3).
> **Added:** `/catalog/items/:id/edit` — reuses `ItemBuilderForm` in edit mode for existing item updates.

---

## 4. Backend API Dependencies

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/items` | `GET` | **Implemented** | Paginated, filterable by `search`, `status_id`, `category_id`, `brand_id` |
| `/api/v1/items/{item_id}` | `GET` | **Implemented** | Returns `ItemRead` with eager-loaded lookups |
| `/api/v1/items` | `POST` | **Implemented** | Auth required. Accepts `ItemCreate` |
| `/api/v1/items/{item_id}` | `PATCH` | **Implemented** | Auth required. Partial update via `ItemUpdate` |
| `/api/v1/items/{item_id}` | `DELETE` | **Implemented** | Auth required. Soft-delete (sets `deleted_at`) |
| `/api/v1/items/statuses` | `GET` | **Implemented** | List all statuses |
| `/api/v1/items/types` | `GET` | **Implemented** | List all item types |
| `/api/v1/items/categories` | `GET` | **Implemented** | List all categories |
| `/api/v1/items/brands` | `GET` | **Implemented** | List all brands |
| `/api/v1/items/uoms` | `GET` | **Implemented** | List all UOMs |
| `/api/v1/warehouse` | `GET` | **Router exists, commented out in main.py** | List warehouses. Activate router first |
| `/api/v1/warehouse/{id}/locations` | `GET` | **Router exists, commented out in main.py** | List locations in warehouse |
| `/api/v1/warehouse/{id}/inventory` | `GET` | **Router exists, commented out in main.py** | Paginated inventory levels |
| `/api/v1/warehouse/{id}/alerts` | `GET` | **Router exists, commented out in main.py** | List alerts by warehouse |
| `/api/v1/warehouse/movements` | `POST` | **To implement** | Create movement + transactions |
| `/api/v1/warehouse/alerts/{id}/resolve` | `PATCH` | **To implement** | Resolve alert with notes |

**Note:** The Settings page (`/settings`) already provides CRUD for Status, ItemType, Category, Brand, and BaseUOM via `src/api/base/items.ts`. The `useGetItemAttributes()` hook reuses these existing API functions with `Promise.allSettled` for parallel loading.

---

## 5. Implementation Order

### Phase 1: Backend Activation
1. **Uncomment warehouse router** in `backend/app/main.py` (line 222)
2. **Implement** `POST /warehouse/movements` endpoint (create movement + transactions)
3. **Implement** `PATCH /warehouse/alerts/{id}/resolve` endpoint
4. **Test** all warehouse endpoints via Swagger UI

### Phase 2: Frontend Types and API Client
1. **Add TypeScript types** — `ItemRead`, `ItemCreate`, `ItemUpdate`, `WarehouseRead`, `InventoryLocationRead`, `InventoryLevelRead`, `InventoryAlertRead` in `src/api/base_types/`
2. **Add item CRUD functions** — `listItems`, `getItem`, `createItem`, `updateItem`, `deleteItem` in `src/api/base/items.ts`
3. **Add warehouse API functions** — new `src/api/base/warehouse.ts` with `listWarehouses`, `getWarehouse`, `listLocations`, `listInventoryLevels`, `listAlerts`, `processMovement`, `resolveAlert`

### Phase 3: Items Module Components
1. `AdvancedDataTable` — paginated master list with search, filters, row expansion for variations
2. `ItemBuilderForm` — multi-step creation/edit form with Tab 1 (Basic Info) and Tab 2 (Variations)

### Phase 4: Warehouse Module Components
1. `InventoryGrid` — stock matrix with warehouse selector and status-colored rows
2. `TransactionHistoryTable` + `InventoryTransferModal` — movement history and transfer action
3. `AlertsKanban` / `AlertsList` — alert action center with resolve workflow
4. `LocationTreeViewer` — warehouse topology tree view

### Phase 5: Routing and Navigation
1. **Add routes** — `/catalog/*` and `/inventory/*` in `App.tsx`
2. **Add nav items** — Catalog and Inventory groups in `MainLayout.tsx` sidebar

---

## 6. Changelog

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-02 | Initial plan created | Define scope for items + warehouse frontend modules |
| 2026-03-02 | **Review and corrections** | Cross-referenced plan against actual backend code. Fixed: (1) search field `sku_name` → `item_name`, (2) `PUT` → `PATCH` for item updates, (3) warehouse API paths from flat `/inventory/...` to nested `/warehouse/{id}/...`, (4) location hierarchy "Warehouse → Zone" → "Section → Zone", (5) removed duplicate `/catalog/attributes` route (already at `/settings`), (6) updated backend dependency statuses (many already implemented), (7) corrected movement payload to match backend model (separate inbound/outbound transactions via `is_inbound` flag), (8) added warehouse router activation prerequisite, (9) added edit route `/catalog/items/:id/edit` |
