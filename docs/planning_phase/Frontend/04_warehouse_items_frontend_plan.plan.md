---
name: Warehouse & Items Frontend Architecture Plan (Revised)
overview: |
  Revised architecture plan covering the full Items + Warehouse domains.
  Sections: (1) Entity & relationship analysis of all 19 DB tables, (2) Current frontend coverage audit at v0.5.22,
  (3) Gap analysis with missing pages/components/endpoints, (4) Suggested page map & UI components per entity,
  (5) Complete TypeScript interfaces for every table, (6) Phased implementation order for remaining work.
  Target versions PRE-ALPHA v0.5.23 – v0.5.30.
todos: []
isProject: false
---

# Warehouse & Items Frontend Architecture Plan (Revised)

**Target versions:** PRE-ALPHA v0.5.23 – v0.5.30
**Created:** 2026-03-03 | **Revised:** 2026-03-04
**Supersedes:** Original plan (v0.5.12 – v0.5.16, fully delivered)

---

## 1. Entity & Relationship Analysis

### 1.1 Items Domain — 8 Tables

```
┌──────────────────────────────────────────────────────────────────┐
│                         ITEMS DOMAIN                             │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ ItemType │  │ Category │  │  Brand   │  │ BaseUOM  │        │
│  │ (lookup) │  │ (lookup) │  │ (lookup) │  │ (lookup) │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │              │             │              │               │
│       └──────────┬───┴─────────────┴──────────────┘               │
│                  ▼                                                │
│  ┌───────────────────────────────────────────────┐               │
│  │                    Item                        │               │
│  │  item_id PK                                   │               │
│  │  parent_id FK → self  (variation hierarchy)   │               │
│  │  item_type_id FK → item_type                  │               │
│  │  category_id FK → category                    │               │
│  │  brand_id FK → brand                          │               │
│  │  uom_id FK → base_uom                         │               │
│  │  deleted_by FK → users (soft delete)          │               │
│  │  variations_data JSONB  (GIN indexed)         │               │
│  │  is_active, has_variation, image_url           │               │
│  └──────┬──────────────────┬─────────────────────┘               │
│         │                  │                                      │
│         ▼                  ▼                                      │
│  ┌──────────────┐  ┌───────────────────────┐                     │
│  │ ItemsHistory │  │ ItemBundleComponent   │                     │
│  │ (audit JSONB)│  │ bundle_item_id → Item │                     │
│  │ snapshot_data│  │ component_item_id→Item│                     │
│  └──────────────┘  │ quantity_per_bundle   │                     │
│                    │ (unique per bundle)   │                     │
│                    └───────────────────────┘                     │
└──────────────────────────────────────────────────────────────────┘
```

**Table details:**

| # | Table | PK | Key Columns | Relationships | Purpose |
|---|-------|----|----|----|----|
| 1 | `status` | `status_id` | `status_name` (unique) | — | Legacy lookup (replaced by `is_active` on Item) |
| 2 | `item_type` | `item_type_id` | `item_type_name` (unique) | 1:N → Item | Product classification (Raw Material, Finished Good, Component, Packaging, Consumable, Office Supplies, **Bundle**) |
| 3 | `category` | `category_id` | `category_name` (unique) | 1:N → Item | Product categories |
| 4 | `brand` | `brand_id` | `brand_name` (unique) | 1:N → Item | Manufacturer / brand |
| 5 | `base_uom` | `uom_id` | `uom_name` (unique) | 1:N → Item | Unit of measure (Each, PCS, Box, Carton, Kg, Liter, Pack, Set) |
| 6 | `items` | `item_id` | `master_sku` (unique), `item_name`, `image_url`, `is_active`, `has_variation`, `variations_data` (JSONB), `deleted_at`/`deleted_by` | Self-ref (parent_id), 4 FK lookups, 1:N → ItemsHistory, 1:N → ItemBundleComponent (both sides) | Core product entity with hierarchical variations + soft delete |
| 7 | `items_history` | `history_id` | `reference_id` FK → items, `operation` (INSERT/UPDATE/DELETE), `snapshot_data` (JSONB with previous_values) | N:1 → Item | Version-control audit trail |
| 8 | `item_bundle_components` | `id` | `bundle_item_id` FK → items, `component_item_id` FK → items, `quantity_per_bundle`, `is_active` | N:1 → Item (both columns), unique(bundle, component) | Bill of Materials for Bundle SKUs |

**Key indexes:**
- `idx_items_variations_gin` — GIN on `variations_data` (jsonb_path_ops)
- `idx_items_active` — Partial on (item_id, master_sku) WHERE deleted_at IS NULL
- `idx_items_history_snapshot_gin` — GIN on `snapshot_data`
- `idx_bundle_components_bundle`, `idx_bundle_components_component`

---

### 1.2 Warehouse Domain — 11 Tables

```
┌───────────────────────────────────────────────────────────────────────┐
│                        WAREHOUSE DOMAIN                               │
│                                                                       │
│  ┌──────────────┐      ┌────────────────┐      ┌──────────────┐      │
│  │  Warehouse    │─────▶│InventoryLoc    │◀─────│InventoryType │      │
│  │  id PK        │      │ section / zone /│      │  (lookup)    │      │
│  │  address JSONB│      │ aisle / rack /  │      └──────────────┘      │
│  │  is_active    │      │ bin             │                            │
│  └──┬───┬────────┘      └──────┬──────────┘                            │
│     │   │                      │                                       │
│     │   │         ┌────────────┼────────────────┐                      │
│     │   │         ▼                             ▼                      │
│     │   │  ┌──────────────────┐      ┌────────────────────┐           │
│     │   │  │ InventoryLevel   │      │InventoryTransaction│           │
│     │   │  │ item_id → Item   │      │ item_id → Item     │           │
│     │   │  │ location_id →Loc │      │ location_id → Loc  │           │
│     │   │  │ lot_id →StockLot │      │ movement_id → Mvmt │           │
│     │   │  │ qty_available    │      │ is_inbound, qty    │           │
│     │   │  │ reserved_quantity│      └─────────┬──────────┘           │
│     │   │  │ reorder / safety │                │                      │
│     │   │  │ / max thresholds │      ┌─────────┴──────────┐           │
│     │   │  └──┬───────────────┘      │ InventoryMovement  │           │
│     │   │     │                      │ movement_type_id   │           │
│     │   │     │                      │ reference_id       │           │
│     │   │     ▼                      └─────────┬──────────┘           │
│     │   │  ┌──────────────────┐                │                      │
│     │   │  │ReplenishHistory  │      ┌─────────┴──────────┐           │
│     │   │  │(threshold audit) │      │   MovementType     │           │
│     │   │  └──────────────────┘      │   (lookup)         │           │
│     │   │                            └────────────────────┘           │
│     │   ▼                                                             │
│     │  ┌──────────────┐      ┌──────────────┐                         │
│     │  │InventoryAlert│      │  StockLot    │                         │
│     │  │ item_id→Item │      │ item_id→Item │                         │
│     │  │ warehouse_id │      │ batch_number │                         │
│     │  │ alert_type   │      │ serial_number│                         │
│     │  │ is_resolved  │      │ expiry_date  │                         │
│     │  └──────────────┘      └──────────────┘                         │
│     │                                                                 │
│     ▼                                                                 │
│  ┌────────────────┐                                                   │
│  │SellerWarehouse │                                                   │
│  │ seller_id→Sell │                                                   │
│  │ warehouse_id   │                                                   │
│  │ is_primary     │                                                   │
│  │ priority       │                                                   │
│  └────────────────┘                                                   │
└───────────────────────────────────────────────────────────────────────┘
```

**Table details:**

| # | Table | PK | Key Columns | Relationships | Purpose |
|---|-------|----|----|----|----|
| 1 | `warehouse` | `id` | `warehouse_name` (unique), `address` (JSONB), `is_active` | 1:N → InventoryLocation, InventoryAlert, SellerWarehouse | Physical warehouse location |
| 2 | `inventory_type` | `inventory_type_id` | `inventory_type_name` (unique) | 1:N → InventoryLocation | Location type (Bulk Storage, Pick Face, Receiving, Staging, Shipping, Returns) |
| 3 | `inventory_location` | `id` | `warehouse_id` FK, `section`, `zone`, `aisle`, `rack`, `bin`, `inventory_type_id` FK | N:1 → Warehouse, N:1 → InventoryType, 1:N → InventoryLevel, InventoryTransaction | Specific location (Section > Zone > Aisle > Rack > Bin hierarchy); `full_location_code` property |
| 4 | `movement_type` | `id` | `movement_name` (unique) | 1:N → InventoryMovement | Movement classification (Receipt, Shipment, Transfer, Adjustment, Return, Cycle Count, Write Off) |
| 5 | `inventory_movements` | `id` | `movement_type_id` FK, `reference_id` | N:1 → MovementType, 1:N → InventoryTransaction | Groups related transactions |
| 6 | `inventory_transactions` | `id` | `item_id` FK → items, `location_id` FK, `movement_id` FK, `is_inbound`, `quantity_change` | N:1 → InventoryLocation, N:1 → InventoryMovement | Individual stock movement line |
| 7 | `stock_lots` | `id` | `item_id` FK → items, `batch_number`, `serial_number` (unique), `unique_barcode` (unique), `expiry_date` | 1:N → InventoryLevel | Batch / serial / barcode / expiry tracking |
| 8 | `inventory_levels` | `id` | `location_id` FK, `item_id` FK → items, `lot_id` FK → stock_lots, `quantity_available`, `reserved_quantity`, `reorder_point`, `safety_stock`, `max_stock` | N:1 → InventoryLocation, N:1 → StockLot, 1:N → ReplenishmentHistory, InventoryAlert | Current stock with thresholds; `atp` and `stock_status` computed properties |
| 9 | `inventory_replenishment_history` | `id` | `inventory_level_id` FK, `previous_trigger`, `new_trigger`, `changed_by_user_id` FK, `bot_intervene` | N:1 → InventoryLevel | Threshold change audit trail |
| 10 | `inventory_alerts` | `id` | `inventory_level_id` FK, `item_id` FK, `warehouse_id` FK, `alert_type`, `current_quantity`, `threshold_quantity`, `is_resolved` | N:1 → InventoryLevel, N:1 → Warehouse | Stock breach alerts with resolution tracking |
| 11 | `seller_warehouses` | `id` | `seller_id` FK → seller, `warehouse_id` FK, `is_primary`, `priority`, `is_active` | N:1 → Seller, N:1 → Warehouse | Many-to-many seller ↔ warehouse fulfillment routing |

**Key indexes:**
- `idx_warehouse_address_gin`, `idx_warehouse_active` (partial)
- `idx_transactions_movement_date`, `idx_transactions_item_location`
- `idx_inventory_item_location`, `idx_inventory_location_lot`, `idx_inventory_low_stock` (partial)
- `idx_inventory_alerts_status_type`, `idx_inventory_alerts_warehouse`, `idx_alerts_unresolved` (partial)

---

### 1.3 Cross-Domain Relationships (Item ↔ Warehouse)

| Item Column | Warehouse Table | Relationship |
|---|---|---|
| `item_id` | `inventory_levels.item_id` | Item stock at a location |
| `item_id` | `inventory_transactions.item_id` | Item movement history |
| `item_id` | `inventory_alerts.item_id` | Alerts tied to an item |
| `item_id` | `stock_lots.item_id` | Batch/serial tracking per item |
| `bundle_item_id` | Bundle fulfillment endpoint | Bundle deducts component stock from warehouse |

**ATP flow:**
- `InventoryLevel.atp` = max(0, quantity_available − reserved_quantity)
- `stock_status` computed: OUT_OF_STOCK → CRITICAL → LOW → OVERSTOCK → OK
- Bundle ATP = MIN(component_atp ÷ quantity_per_bundle) across all active components

---

## 2. Current Frontend Coverage Audit (v0.5.22)

### 2.1 Items Domain

| Entity | List | Create | Edit | Detail | Settings | Status |
|---|---|---|---|---|---|---|
| **Item** | `ItemsListPage` (tabs, filters, expandable variations) | `ItemFormPage` (image, variations) | `ItemFormPage` (pre-populated) | *(via edit page)* | — | **Done** |
| **ItemType** | — | — | — | — | `SettingsPage` (AttributeCard) | **Done** |
| **Category** | — | — | — | — | `SettingsPage` (AttributeCard) | **Done** |
| **Brand** | — | — | — | — | `SettingsPage` (AttributeCard) | **Done** |
| **BaseUOM** | — | — | — | — | `SettingsPage` (AttributeCard) | **Done** |
| **ItemBundleComponent** | `BundleComponentsTab` | `BundleFormPage` (BOM picker) | `BundleComponentsTab` (inline) | — | — | **Done** |
| **ItemsHistory** | — | — | — | — | — | **Missing** |
| **Status** (legacy) | — | — | — | — | — | N/A (replaced by `is_active`) |

### 2.2 Warehouse Domain

| Entity | List | Create | Edit | Detail | Settings | Status |
|---|---|---|---|---|---|---|
| **Warehouse** | `WarehouseListPage` (search, status filter) | modal | modal | — | — | **Done** |
| **InventoryLevel** | `InventoryLevelsPage` (stock matrix, filter tabs, Bundle ATP card) | — | — | — | — | **Done** |
| **InventoryMovement** | `InventoryMovementsPage` (history table) | modal (Manual + Bundle Fulfillment) | — | — | — | **Done** |
| **InventoryAlert** | `InventoryAlertsPage` (resolve modal, summary chips) | — | *(resolve)* | — | — | **Done** |
| **InventoryLocation** | *(read-only in dropdowns)* | — | — | — | — | **Missing CRUD** |
| **InventoryType** | — | — | — | — | — | **Missing** |
| **MovementType** | — | — | — | — | — | **Missing** |
| **StockLot** | — | — | — | — | — | **Missing** |
| **InventoryReplenishmentHistory** | — | — | — | — | — | **Missing** |
| **SellerWarehouse** | — | — | — | — | — | **Missing** |

### 2.3 Existing File Structure

```
frontend/src/
├── pages/
│   ├── items/
│   │   ├── ItemsListPage.tsx          ✓ /catalog/items
│   │   ├── ItemFormPage.tsx           ✓ /catalog/items/new & :id/edit
│   │   ├── ItemsMassUploadPage.tsx    ✓ /catalog/items/upload
│   │   ├── BundleComponentsTab.tsx    ✓ BOM editor (edit mode)
│   │   ├── ItemFilters.tsx            ✓ Search + Category + Brand
│   │   ├── VariationBuilder.tsx       ✓ 2-level variation matrix
│   │   ├── VariationBuilder.types.ts  ✓
│   │   └── VariationBuilder.utils.ts  ✓
│   ├── warehouse/
│   │   ├── WarehouseListPage.tsx       ✓ /inventory/warehouses
│   │   ├── InventoryLevelsPage.tsx     ✓ /inventory/levels
│   │   ├── InventoryMovementsPage.tsx  ✓ /inventory/movements
│   │   ├── InventoryAlertsPage.tsx     ✓ /inventory/alerts
│   │   ├── StockStatusBadge.tsx        ✓ Color-coded badge
│   │   └── WarehouseSelector.tsx       ✓ Dropdown reused across pages
│   ├── catalog/
│   │   ├── CatalogBundlesPage.tsx      ✓ /catalog/bundles
│   │   └── BundleFormPage.tsx          ✓ /catalog/bundles/new & :id/edit
│   ├── settings/
│   │   ├── SettingsPage.tsx            ✓ /settings
│   │   └── AttributeCard.tsx           ✓ Reusable CRUD card
│   └── dashboard/                      (placeholder components)
├── components/
│   ├── common/
│   │   └── DataTable.tsx               ✓ Reusable table with pagination
│   └── layout/
│       └── MainLayout.tsx              ✓ Sidebar (Catalog, Inventory submenus)
├── api/
│   ├── base/
│   │   ├── items.ts                    ✓ 20+ functions
│   │   └── warehouse.ts               ✓ 15+ functions
│   └── base_types/
│       ├── items.ts                    ✓ Full item/bundle types
│       └── warehouse.ts               ✓ Full warehouse/inventory types
└── App.tsx                             ✓ 14 routes registered
```

### 2.4 Existing API Endpoints (Backend)

**Items Router** (`/api/v1/items`) — 25+ endpoints:
- CRUD: types, categories, brands, uoms (4 × GET/POST/PATCH/DELETE = 16)
- Items: GET list, GET /:id, POST, PATCH /:id, DELETE /:id, GET /counts
- Image: POST /upload-image
- Bundle: GET /:id/bundle, POST/PUT/DELETE /:id/bundle/components/:cid, GET /:id/bundle/atp, GET /:id/bundle/memberships
- Mass import: POST /import

**Warehouse Router** (`/api/v1/warehouse`) — 12 endpoints:
- GET /movement-types
- Warehouse: GET list, GET /:id, POST, PATCH /:id
- Locations: GET /:id/locations
- Levels: GET /:id/inventory (paginated, enriched)
- Movements: GET /:id/movements, POST /movements
- Alerts: GET /:id/alerts, PATCH /alerts/:id/resolve
- Bundle ops: POST /reserve, POST /release, POST /fulfill/bundle

---

## 3. Gap Analysis — What's Missing

### 3.1 Missing Pages

| # | Entity | Proposed Page | Route | Priority | Why |
|---|--------|----|----|----|----|
| 1 | **InventoryLocation** | `LocationManagerPage` | `/inventory/warehouses/:id/locations` | **High** | Cannot set up warehouse without creating locations; currently read-only |
| 2 | **StockLot** | `StockLotListPage` | `/inventory/lots` | **High** | FEFO/FIFO picking requires batch/serial/expiry tracking UI |
| 3 | **StockLot** | `StockLotFormPage` | `/inventory/lots/new` | **High** | Create lots with barcode + expiry |
| 4 | **ItemsHistory** | `ItemDetailPage` (with History tab) | `/catalog/items/:id` | **Medium** | Compliance audit trail; currently no way to view change history |
| 5 | **InventoryType + MovementType** | `WarehouseSettingsPage` | `/settings/warehouse` | **Medium** | Lookup tables should be admin-editable, not only seed-managed |
| 6 | **SellerWarehouse** | `FulfillmentRoutingPage` | `/settings/fulfillment` | **Medium** | Multi-warehouse seller routing not configurable in UI |
| 7 | **InventoryReplenishmentHistory** | Inline tab on `InventoryLevelsPage` | — (tab, not route) | **Low** | Operational audit; rarely viewed but useful for debugging |
| 8 | **InventoryLevel** (thresholds) | Inline edit on `InventoryLevelsPage` | — (inline action) | **Medium** | Cannot edit reorder_point/safety_stock/max_stock from frontend |

### 3.2 Missing Backend Endpoints

| # | Endpoint | Needed For | Priority |
|---|----------|----|----|
| 1 | `POST /warehouse/:id/locations` | LocationManagerPage — create location | **High** |
| 2 | `PATCH /warehouse/locations/:id` | LocationManagerPage — edit location | **High** |
| 3 | `DELETE /warehouse/locations/:id` | LocationManagerPage — remove location | **High** |
| 4 | `GET /warehouse/inventory-types` | WarehouseSettingsPage — list types | **Medium** |
| 5 | `POST /warehouse/inventory-types` | WarehouseSettingsPage — create type | **Medium** |
| 6 | `PATCH /warehouse/inventory-types/:id` | WarehouseSettingsPage — edit type | **Medium** |
| 7 | `DELETE /warehouse/inventory-types/:id` | WarehouseSettingsPage — delete type | **Medium** |
| 8 | `POST /warehouse/movement-types` | WarehouseSettingsPage — create type | **Medium** |
| 9 | `PATCH /warehouse/movement-types/:id` | WarehouseSettingsPage — edit type | **Medium** |
| 10 | `DELETE /warehouse/movement-types/:id` | WarehouseSettingsPage — delete type | **Medium** |
| 11 | `GET /items/:id/history` | ItemDetailPage — audit trail | **Medium** |
| 12 | `GET /warehouse/stock-lots` | StockLotListPage — list lots | **High** |
| 13 | `POST /warehouse/stock-lots` | StockLotFormPage — create lot | **High** |
| 14 | `PATCH /warehouse/stock-lots/:id` | StockLotListPage — edit lot | **High** |
| 15 | `GET /warehouse/seller-mappings` | FulfillmentRoutingPage — list | **Medium** |
| 16 | `POST /warehouse/seller-mappings` | FulfillmentRoutingPage — create | **Medium** |
| 17 | `PATCH /warehouse/seller-mappings/:id` | FulfillmentRoutingPage — edit | **Medium** |
| 18 | `DELETE /warehouse/seller-mappings/:id` | FulfillmentRoutingPage — delete | **Medium** |
| 19 | `PATCH /warehouse/:id/inventory/:levelId` | InventoryLevelsPage — edit thresholds | **Medium** |
| 20 | `GET /warehouse/:id/inventory/:levelId/replenishment-history` | InventoryLevelsPage — history tab | **Low** |

### 3.3 Missing Frontend Components

| # | Component | Location | Used By | Priority |
|---|-----------|----------|---------|----------|
| 1 | `LocationsGrid` | `pages/warehouse/` | LocationManagerPage — CRUD grid for Section/Zone/Aisle/Rack/Bin | **High** |
| 2 | `LocationBreadcrumb` | `pages/warehouse/` | LocationManagerPage — visual hierarchy display | **High** |
| 3 | `StockLotTable` | `pages/warehouse/` | StockLotListPage — list with expiry highlighting | **High** |
| 4 | `ExpiryBadge` | `pages/warehouse/` | StockLotListPage — days-until-expiry color indicator | **High** |
| 5 | `ItemHistoryTimeline` | `pages/items/` | ItemDetailPage — JSONB snapshot diff viewer | **Medium** |
| 6 | `ThresholdEditor` | `pages/warehouse/` | InventoryLevelsPage — inline edit reorder/safety/max | **Medium** |
| 7 | `BundleATPCard` | `pages/warehouse/` | InventoryLevelsPage — extract inline ATP lookup to component | **Low** |
| 8 | `AlertTypeBadge` | `pages/warehouse/` | InventoryAlertsPage — icon + color per alert type | **Low** |
| 9 | `SellerWarehouseMatrix` | `pages/settings/` | FulfillmentRoutingPage — seller × warehouse grid | **Medium** |
| 10 | `ItemSearchSelect` | `components/common/` | Reused in movements, lots, bundles — async search-select | **Medium** |

---

## 4. Suggested Page Map & UI Components

### 4.1 Complete Route Table

| # | Route | Page Component | Folder | Status |
|---|-------|-------|-------|--------|
| 1 | `/` | `DashboardPage` | `pages/dashboard/` | Placeholder (enhance) |
| 2 | `/catalog/items` | `ItemsListPage` | `pages/items/` | **Done** |
| 3 | `/catalog/items/new` | `ItemFormPage` | `pages/items/` | **Done** |
| 4 | `/catalog/items/:id/edit` | `ItemFormPage` | `pages/items/` | **Done** |
| 5 | `/catalog/items/:id` | **`ItemDetailPage`** | `pages/items/` | **New** |
| 6 | `/catalog/items/upload` | `ItemsMassUploadPage` | `pages/items/` | **Done** |
| 7 | `/catalog/bundles` | `CatalogBundlesPage` | `pages/catalog/` | **Done** |
| 8 | `/catalog/bundles/new` | `BundleFormPage` | `pages/catalog/` | **Done** |
| 9 | `/catalog/bundles/:id/edit` | `BundleFormPage` | `pages/catalog/` | **Done** |
| 10 | `/inventory/warehouses` | `WarehouseListPage` | `pages/warehouse/` | **Done** |
| 11 | `/inventory/warehouses/:id/locations` | **`LocationManagerPage`** | `pages/warehouse/` | **New** |
| 12 | `/inventory/levels` | `InventoryLevelsPage` | `pages/warehouse/` | **Done** (enhance: threshold edit) |
| 13 | `/inventory/movements` | `InventoryMovementsPage` | `pages/warehouse/` | **Done** |
| 14 | `/inventory/alerts` | `InventoryAlertsPage` | `pages/warehouse/` | **Done** |
| 15 | `/inventory/lots` | **`StockLotListPage`** | `pages/warehouse/` | **New** |
| 16 | `/inventory/lots/new` | **`StockLotFormPage`** | `pages/warehouse/` | **New** |
| 17 | `/settings` | `SettingsPage` | `pages/settings/` | **Done** |
| 18 | `/settings/warehouse` | **`WarehouseSettingsPage`** | `pages/settings/` | **New** |
| 19 | `/settings/fulfillment` | **`FulfillmentRoutingPage`** | `pages/settings/` | **New** |

### 4.2 UI Components Per Entity

#### Item

| Component | File | Purpose |
|---|---|---|
| `ItemsListPage` | `pages/items/ItemsListPage.tsx` | DataTable with 4 tabs (All/Live/Unpublished/Deleted), expandable variation rows, inline toggle | **Done** |
| `ItemFormPage` | `pages/items/ItemFormPage.tsx` | Create/edit with image upload, attribute dropdowns, variation builder | **Done** |
| `ItemsMassUploadPage` | `pages/items/ItemsMassUploadPage.tsx` | Drag-drop file upload, SheetJS preview, per-row error table | **Done** |
| `ItemFilters` | `pages/items/ItemFilters.tsx` | Search + Category + Brand filter bar | **Done** |
| `VariationBuilder` | `pages/items/VariationBuilder.tsx` | 2-level variation matrix with combination generator | **Done** |
| **`ItemDetailPage`** | `pages/items/ItemDetailPage.tsx` | Read-only item view + Tabs: Details, Variations, Bundle Components, History | **New** |
| **`ItemHistoryTimeline`** | `pages/items/ItemHistoryTimeline.tsx` | Timeline of `items_history` records with JSONB diff display | **New** |

#### Bundle

| Component | File | Purpose |
|---|---|---|
| `CatalogBundlesPage` | `pages/catalog/CatalogBundlesPage.tsx` | Bundle list with thumbnail, toggle, delete | **Done** |
| `BundleFormPage` | `pages/catalog/BundleFormPage.tsx` | Create/edit with BOM picker, auto-SKU, qty validation | **Done** |
| `BundleComponentsTab` | `pages/items/BundleComponentsTab.tsx` | Inline BOM editor (add/edit qty/toggle/remove) | **Done** |

#### Warehouse

| Component | File | Purpose |
|---|---|---|
| `WarehouseListPage` | `pages/warehouse/WarehouseListPage.tsx` | List + create/edit modal | **Done** |
| `WarehouseSelector` | `pages/warehouse/WarehouseSelector.tsx` | Dropdown reused on Levels/Movements/Alerts | **Done** |
| **`LocationManagerPage`** | `pages/warehouse/LocationManagerPage.tsx` | CRUD for inventory locations within a warehouse | **New** |
| **`LocationsGrid`** | `pages/warehouse/LocationsGrid.tsx` | Editable grid: Section/Zone/Aisle/Rack/Bin + type dropdown | **New** |
| **`LocationBreadcrumb`** | `pages/warehouse/LocationBreadcrumb.tsx` | Visual hierarchy: Section > Zone > Aisle > Rack > Bin | **New** |

#### Inventory Level

| Component | File | Purpose |
|---|---|---|
| `InventoryLevelsPage` | `pages/warehouse/InventoryLevelsPage.tsx` | Stock matrix with status filter tabs, summary chips, Bundle ATP card | **Done** |
| `StockStatusBadge` | `pages/warehouse/StockStatusBadge.tsx` | Color-coded badge (OK/Low/Critical/OOS/Overstock) | **Done** |
| **`ThresholdEditor`** | `pages/warehouse/ThresholdEditor.tsx` | Inline/modal edit for reorder_point, safety_stock, max_stock | **New** |
| **`BundleATPCard`** | `pages/warehouse/BundleATPCard.tsx` | Extracted Bundle ATP lookup (currently inline in LevelsPage) | **New** (refactor) |

#### Inventory Movement

| Component | File | Purpose |
|---|---|---|
| `InventoryMovementsPage` | `pages/warehouse/InventoryMovementsPage.tsx` | History table + Record Movement modal (Manual + Bundle Fulfillment) | **Done** |

#### Stock Lot

| Component | File | Purpose |
|---|---|---|
| **`StockLotListPage`** | `pages/warehouse/StockLotListPage.tsx` | List lots by item, filter by expiry status, search by batch/serial/barcode | **New** |
| **`StockLotFormPage`** | `pages/warehouse/StockLotFormPage.tsx` | Create lot: item picker, batch#, serial#, barcode, expiry date | **New** |
| **`ExpiryBadge`** | `pages/warehouse/ExpiryBadge.tsx` | Color-coded days-until-expiry indicator (expired/expiring-soon/ok) | **New** |

#### Inventory Alert

| Component | File | Purpose |
|---|---|---|
| `InventoryAlertsPage` | `pages/warehouse/InventoryAlertsPage.tsx` | Alert list with resolve modal, summary chips | **Done** |
| **`AlertTypeBadge`** | `pages/warehouse/AlertTypeBadge.tsx` | Icon + color per alert type (low_stock/critical/out_of_stock/overstock) | **New** (extract from inline) |

#### Settings

| Component | File | Purpose |
|---|---|---|
| `SettingsPage` | `pages/settings/SettingsPage.tsx` | Item attributes CRUD (type, category, brand, uom) | **Done** |
| `AttributeCard` | `pages/settings/AttributeCard.tsx` | Reusable CRUD card per lookup table | **Done** |
| **`WarehouseSettingsPage`** | `pages/settings/WarehouseSettingsPage.tsx` | InventoryType + MovementType CRUD (reuses AttributeCard pattern) | **New** |
| **`FulfillmentRoutingPage`** | `pages/settings/FulfillmentRoutingPage.tsx` | SellerWarehouse mapping table with priority/primary toggle | **New** |
| **`SellerWarehouseMatrix`** | `pages/settings/SellerWarehouseMatrix.tsx` | Editable grid: seller rows × warehouse columns | **New** |

#### Dashboard

| Component | File | Purpose |
|---|---|---|
| `DashboardPage` | `pages/DashboardPage.tsx` | Overview hub | Placeholder (enhance) |
| **`StockSummaryCard`** | `pages/dashboard/StockSummaryCard.tsx` | Aggregate stock counts by status across warehouses | **New** |
| **`ActiveAlertsWidget`** | `pages/dashboard/ActiveAlertsWidget.tsx` | Top N unresolved alerts with direct resolve action | **New** |
| **`RecentMovementsWidget`** | `pages/dashboard/RecentMovementsWidget.tsx` | Last 10 movements across all warehouses | **New** |
| **`ExpiringLotsWidget`** | `pages/dashboard/ExpiringLotsWidget.tsx` | Lots expiring within configurable days threshold | **New** |

#### Shared / Cross-cutting

| Component | File | Purpose |
|---|---|---|
| `DataTable` | `components/common/DataTable.tsx` | Paginated table with search, selection, expansion | **Done** |
| **`ItemSearchSelect`** | `components/common/ItemSearchSelect.tsx` | Async search-select dropdown for items (used in movements, lots, bundles, etc.) | **New** |

### 4.3 Sidebar Navigation Update

```
Dashboard
Catalog ▾
  ├── Items
  └── Bundles
Inventory ▾
  ├── Warehouses
  ├── Stock Levels
  ├── Movements
  ├── Alerts
  └── Lot Tracking        ← NEW
Order Import
Reference Data
ML Staging
Settings ▾                 ← NEW (convert to submenu)
  ├── Item Attributes
  ├── Warehouse Settings   ← NEW
  └── Fulfillment Routing  ← NEW
```

---

## 5. Complete TypeScript Interfaces — All 19 Tables

### 5.1 Items Domain

```typescript
// ═══════════════════════════════════════════════
//  ITEMS DOMAIN — 8 tables
// ═══════════════════════════════════════════════

// ---- Lookup: Status (legacy, replaced by is_active) ----
export interface StatusRead {
  status_id: number;
  status_name: string;
}

// ---- Lookup: ItemType ----
export interface ItemTypeRead {
  item_type_id: number;
  item_type_name: string;
}
export interface ItemTypeCreate {
  item_type_name: string; // max 100
}
export interface ItemTypeUpdate {
  item_type_name?: string;
}

// ---- Lookup: Category ----
export interface CategoryRead {
  category_id: number;
  category_name: string;
}
export interface CategoryCreate {
  category_name: string; // max 100
}
export interface CategoryUpdate {
  category_name?: string;
}

// ---- Lookup: Brand ----
export interface BrandRead {
  brand_id: number;
  brand_name: string;
}
export interface BrandCreate {
  brand_name: string; // max 200
}
export interface BrandUpdate {
  brand_name?: string;
}

// ---- Lookup: BaseUOM ----
export interface BaseUOMRead {
  uom_id: number;
  uom_name: string;
}
export interface BaseUOMCreate {
  uom_name: string; // max 50
}
export interface BaseUOMUpdate {
  uom_name?: string;
}

// ---- Normalized attribute shape (used in Item nested relations) ----
export interface AttributeItem {
  id: number;
  name: string;
}

// ---- Item (core entity) ----
export interface ItemRead {
  item_id: number;
  parent_id: number | null;
  item_name: string;
  master_sku: string;
  sku_name: string | null;
  description: string | null;
  image_url: string | null;
  uom_id: number | null;
  brand_id: number | null;
  item_type_id: number | null;
  category_id: number | null;
  is_active: boolean;
  has_variation: boolean;
  variations_data: Record<string, any> | null;
  created_at: string;           // ISO datetime
  updated_at: string;
  deleted_at: string | null;
  // Nested relations (joined server-side)
  uom: AttributeItem | null;
  brand: AttributeItem | null;
  item_type: AttributeItem | null;
  category: AttributeItem | null;
}

export interface ItemCreate {
  item_name: string;            // max 500, required
  master_sku: string;           // max 100, unique, required, no spaces
  sku_name?: string;            // max 500
  description?: string;
  image_url?: string;
  uom_id?: number;
  brand_id?: number;
  item_type_id?: number;
  category_id?: number;
  is_active?: boolean;          // default true
  parent_id?: number;
  has_variation?: boolean;      // default false
  variations_data?: Record<string, any>;
}

export interface ItemUpdate {
  item_name?: string;
  sku_name?: string;
  description?: string;
  image_url?: string;
  uom_id?: number;
  brand_id?: number;
  item_type_id?: number;
  category_id?: number;
  is_active?: boolean;
  has_variation?: boolean;
  variations_data?: Record<string, any>;
}

// ---- ItemsHistory (audit trail) ----
export interface ItemsHistoryRead {
  history_id: number;
  reference_id: number;         // FK → items.item_id
  timestamp: string;            // ISO datetime
  changed_by_user_id: number | null;
  operation: 'INSERT' | 'UPDATE' | 'DELETE';
  snapshot_data: {
    [field: string]: any;       // Changed fields with new values
    previous_values?: Record<string, any>;  // Old values before change
  };
}

// ---- ItemBundleComponent (BOM) ----
export interface BundleComponentRead {
  id: number;
  bundle_item_id: number;
  component_item_id: number;
  component_name: string;       // joined from items.item_name
  component_sku: string;        // joined from items.master_sku
  quantity_per_bundle: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BundleComponentCreate {
  component_item_id: number;
  quantity_per_bundle: number;  // >= 1
}

export interface BundleComponentUpdate {
  quantity_per_bundle?: number; // >= 1
  is_active?: boolean;
}

// ---- Bundle ATP ----
export interface BundleATPRead {
  bundle_item_id: number;
  warehouse_id: number;
  atp: number;                  // MIN(component_atp / qty_per_bundle)
}

// ---- Bundle Membership (which bundles contain this item) ----
export interface BundleMembershipRead {
  bundle_item_id: number;
  bundle_name: string;
  bundle_sku: string;
  quantity_per_bundle: number;
  is_active: boolean;
}

// ---- Mass Import ----
export interface ImportRowError {
  row: number;
  master_sku: string;
  error: string;
}

export interface ItemsImportResult {
  total_rows: number;
  success_rows: number;
  error_rows: number;
  errors: ImportRowError[];
}

// ---- Item Counts ----
export interface ItemCounts {
  all: number;
  live: number;
  unpublished: number;
  deleted: number;
}
```

### 5.2 Warehouse Domain

```typescript
// ═══════════════════════════════════════════════
//  WAREHOUSE DOMAIN — 11 tables
// ═══════════════════════════════════════════════

// ---- Warehouse ----
export interface WarehouseRead {
  id: number;
  warehouse_name: string;
  address: Record<string, string> | null;  // JSONB: {street, city, state, postcode}
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WarehouseCreate {
  warehouse_name: string;       // max 200, unique
  address?: Record<string, string>;
  is_active?: boolean;          // default true
}

export interface WarehouseUpdate {
  warehouse_name?: string;
  address?: Record<string, string>;
  is_active?: boolean;
}

// ---- Lookup: InventoryType ----
export interface InventoryTypeRead {
  inventory_type_id: number;
  inventory_type_name: string;
}

export interface InventoryTypeCreate {
  inventory_type_name: string;  // max 100
}

export interface InventoryTypeUpdate {
  inventory_type_name?: string;
}

// ---- InventoryLocation ----
export interface InventoryLocationRead {
  id: number;
  warehouse_id: number;
  section: string | null;       // max 50 each
  zone: string | null;
  aisle: string | null;
  rack: string | null;
  bin: string | null;
  inventory_type_id: number | null;
  created_at: string;
}

export interface InventoryLocationCreate {
  warehouse_id: number;
  section?: string;
  zone?: string;
  aisle?: string;
  rack?: string;
  bin?: string;
  inventory_type_id?: number;
}

export interface InventoryLocationUpdate {
  section?: string;
  zone?: string;
  aisle?: string;
  rack?: string;
  bin?: string;
  inventory_type_id?: number;
}

export interface LocationSummary {
  id: number;
  code: string;                 // Derived: "S1-Z2-A3-R4-B5"
  section: string | null;
  zone: string | null;
  aisle: string | null;
  rack: string | null;
  bin: string | null;
}

// ---- Lookup: MovementType ----
export interface MovementTypeRead {
  id: number;
  name: string;                 // Receipt, Shipment, Transfer, Adjustment, Return, Cycle Count, Write Off
}

export interface MovementTypeCreate {
  movement_name: string;       // max 100
}

export interface MovementTypeUpdate {
  movement_name?: string;
}

// ---- InventoryMovement (movement grouping) ----
export interface InventoryMovementRead {
  id: number;
  warehouse_id: number;
  movement_type_id: number;
  movement_type: MovementTypeRead;
  item_id: number;
  item_name: string;            // joined from items
  master_sku: string;           // joined from items
  reference_number: string | null;
  notes: string | null;
  quantity: number;             // total quantity across transactions
  is_inbound: boolean;
  created_at: string;
  created_by: number | null;
}

export interface InventoryMovementCreate {
  warehouse_id: number;
  movement_type_id: number;
  item_id: number;
  transactions: InventoryTransactionCreate[];  // min 1
  reference_number?: string;    // max 100
  notes?: string;               // max 500
}

// ---- InventoryTransaction (individual movement line) ----
export interface InventoryTransactionCreate {
  location_id: number;
  is_inbound: boolean;          // true = stock in, false = stock out
  quantity_change: number;      // > 0 always; direction from is_inbound
}

// ---- StockLot (batch / serial / barcode tracking) ----
export interface StockLotRead {
  id: number;
  item_id: number;
  batch_number: string | null;
  serial_number: string | null;  // unique
  unique_barcode: string | null; // unique
  expiry_date: string | null;    // ISO date (YYYY-MM-DD)
  created_at: string;
}

export interface StockLotCreate {
  item_id: number;
  batch_number?: string;        // max 100
  serial_number?: string;       // max 100, unique
  unique_barcode?: string;      // max 200, unique
  expiry_date?: string;         // ISO date
}

export interface StockLotUpdate {
  batch_number?: string;
  serial_number?: string;
  unique_barcode?: string;
  expiry_date?: string;
}

// ---- InventoryLevel (current stock at location) ----
export type StockStatus = 'ok' | 'low' | 'critical' | 'out_of_stock' | 'overstock';

export interface InventoryLevelEnrichedRead {
  id: number;
  location_id: number;
  item_id: number;
  item_name: string;            // joined from items
  master_sku: string;           // joined from items
  location: LocationSummary;    // nested location detail
  lot_id: number | null;
  quantity_available: number;
  reserved_quantity: number;    // allocated to open orders
  reorder_point: number | null;
  safety_stock: number | null;
  max_stock: number | null;
  stock_status: StockStatus;    // computed: ATP-based
  alert_triggered_at: string | null;
  alert_acknowledged: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryLevelUpdate {
  reorder_point?: number | null;
  safety_stock?: number | null;
  max_stock?: number | null;
}

// ---- InventoryReplenishmentHistory (threshold change audit) ----
export interface ReplenishmentHistoryRead {
  id: number;
  inventory_level_id: number;
  previous_trigger: number | null;
  new_trigger: number | null;
  changed_by_user_id: number | null;
  bot_intervene: boolean;       // true if automated system changed threshold
  changed_at: string;
}

// ---- InventoryAlert ----
export type AlertType = 'low_stock' | 'out_of_stock' | 'critical' | 'overstock';

export interface InventoryAlertRead {
  id: number;
  inventory_level_id: number;
  item_id: number;
  warehouse_id: number;
  alert_type: AlertType;
  current_quantity: number;
  threshold_quantity: number;
  alert_message: string | null;
  is_resolved: boolean;
  resolved_at: string | null;
  resolution_notes: string | null;
  resolved_by_user_id: number | null;
  created_at: string;
}

export interface AlertResolveRequest {
  resolution_notes?: string;    // max 500
}

// ---- SellerWarehouse (fulfillment routing) ----
export interface SellerWarehouseRead {
  id: number;
  seller_id: number;
  warehouse_id: number;
  is_primary: boolean;          // primary fulfillment warehouse for seller
  priority: number;             // lower = higher priority
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SellerWarehouseCreate {
  seller_id: number;
  warehouse_id: number;
  is_primary?: boolean;         // default false
  priority?: number;            // default 0
  is_active?: boolean;          // default true
}

export interface SellerWarehouseUpdate {
  is_primary?: boolean;
  priority?: number;
  is_active?: boolean;
}

// ---- Stock Reservation / Release / Bundle Fulfillment ----
export interface ReserveRequest {
  item_id: number;
  quantity: number;             // > 0
  warehouse_id: number;
}

export interface ReserveResponse {
  item_id: number;
  quantity_reserved: number;
  warehouse_id: number;
}

export interface ReleaseRequest {
  item_id: number;
  quantity: number;             // > 0
  warehouse_id: number;
}

export interface BundleFulfillRequest {
  bundle_item_id: number;
  bundle_qty_sold: number;      // > 0
  warehouse_id: number;
  order_reference: string;      // max 100
}
```

### 5.3 Shared Types

```typescript
// ═══════════════════════════════════════════════
//  SHARED / CROSS-CUTTING
// ═══════════════════════════════════════════════

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
```

---

## 6. Page Specifications (New Pages Only)

### 6.1 `/catalog/items/:id` — `ItemDetailPage`

**Purpose:** Read-only item view with change history tab.

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  ← Back to Items        [Edit]  [Delete]                 │
├──────────────────────────────────────────────────────────┤
│  ┌────────┐                                              │
│  │ IMAGE  │  T-Shirt Classic Red                         │
│  │ 120×120│  SKU: TS-RED-001                             │
│  └────────┘  Category: Clothing  |  Brand: Acme          │
│              UOM: Each  |  Type: Finished Good            │
│              Status: ● Active                             │
├──────────────────────────────────────────────────────────┤
│  [Details] [Variations] [Bundle Components] [History]    │
├──────────────────────────────────────────────────────────┤
│  (tab content area)                                       │
│  History tab: ItemHistoryTimeline component               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 2026-03-04 14:22  UPDATE  by admin@admin.com        │ │
│  │   brand_id: 1 → 2  (Acme → Beta Corp)              │ │
│  │   is_active: true → false                           │ │
│  │─────────────────────────────────────────────────────│ │
│  │ 2026-03-03 09:10  INSERT  by admin@admin.com        │ │
│  │   Initial creation                                  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**API:** `GET /items/:id`, `GET /items/:id/history` (new), `GET /items/:id/bundle` (if Bundle type)

---

### 6.2 `/inventory/warehouses/:id/locations` — `LocationManagerPage`

**Purpose:** CRUD for inventory locations within a specific warehouse.

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  ← Warehouse A — Locations                [+ Add Location]│
├──────────────────────────────────────────────────────────┤
│  Search...                         [Type filter ▾]       │
├──────┬────────┬───────┬───────┬──────┬──────┬───────────┤
│  ID  │Section │ Zone  │ Aisle │ Rack │ Bin  │   Type    │
├──────┼────────┼───────┼───────┼──────┼──────┼───────────┤
│  1   │  A     │  1    │  01   │  01  │  01  │ Pick Face │
│  2   │  A     │  1    │  01   │  01  │  02  │ Pick Face │
│  3   │  B     │  1    │  —    │  —   │  —   │ Receiving │
├──────┴────────┴───────┴───────┴──────┴──────┴───────────┤
│  Location code preview: A-1-01-01-01                     │
└──────────────────────────────────────────────────────────┘
```

**Create/Edit Modal:**

```
┌──────────────────────────────────┐
│ Add Location                     │
│                                  │
│ Section        [____]  optional  │
│ Zone           [____]  optional  │
│ Aisle          [____]  optional  │
│ Rack           [____]  optional  │
│ Bin            [____]  optional  │
│ Type           [Pick Face ▾]     │
│                                  │
│ Preview: A-1-01-01-01            │
│                [Cancel] [Save]   │
└──────────────────────────────────┘
```

**API:** `GET /warehouse/:id/locations`, `POST /warehouse/:id/locations` (new), `PATCH /warehouse/locations/:id` (new), `DELETE /warehouse/locations/:id` (new), `GET /warehouse/inventory-types` (new)

---

### 6.3 `/inventory/lots` — `StockLotListPage`

**Purpose:** Manage batch/serial/barcode tracking and monitor expiry dates.

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Lot Tracking                            [+ Create Lot]  │
├──────────────────────────────────────────────────────────┤
│  Search (batch/serial/barcode)...  [Expiry filter ▾]     │
├──────┬──────────┬──────────┬──────────┬─────────┬───────┤
│  ID  │ Item     │ Batch #  │ Serial # │ Barcode │Expiry │
├──────┼──────────┼──────────┼──────────┼─────────┼───────┤
│  1   │ Widget A │ B-2026-01│ —        │ 890123  │ ⚠ 15d │
│  2   │ Widget A │ B-2026-02│ SN-00042 │ 890124  │ ✓ 90d │
│  3   │ Serum X  │ —        │ SN-00099 │ —       │ ✗ Exp │
└──────┴──────────┴──────────┴──────────┴─────────┴───────┘
```

**ExpiryBadge colors:**
| Condition | Color | Label |
|---|---|---|
| Expired (past date) | Red | "Expired" |
| ≤ 30 days remaining | Yellow | "N days" |
| > 30 days remaining | Green | "N days" |
| No expiry set | Gray | "N/A" |

**API:** `GET /warehouse/stock-lots` (new), `POST /warehouse/stock-lots` (new), `PATCH /warehouse/stock-lots/:id` (new)

---

### 6.4 `/settings/warehouse` — `WarehouseSettingsPage`

**Purpose:** Manage InventoryType and MovementType lookup tables (same pattern as item attributes).

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Warehouse Settings                                      │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌────────────────────────────┐│
│  │ Inventory Types      │  │ Movement Types             ││
│  │ ┌──────────────────┐ │  │ ┌────────────────────────┐ ││
│  │ │ Bulk Storage  [✎]│ │  │ │ Receipt            [✎]│ ││
│  │ │ Pick Face     [✎]│ │  │ │ Shipment           [✎]│ ││
│  │ │ Receiving     [✎]│ │  │ │ Transfer           [✎]│ ││
│  │ │ Staging       [✎]│ │  │ │ Adjustment         [✎]│ ││
│  │ │ Shipping      [✎]│ │  │ │ Return             [✎]│ ││
│  │ │ Returns       [✎]│ │  │ │ Cycle Count        [✎]│ ││
│  │ │ [+ Add]          │ │  │ │ Write Off          [✎]│ ││
│  │ └──────────────────┘ │  │ │ [+ Add]               │ ││
│  └─────────────────────┘  │ └────────────────────────┘ ││
│                            └────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

Reuses the `AttributeCard` component pattern from SettingsPage.

**API:** CRUD for both `inventory-types` and `movement-types` (6 new endpoints).

---

### 6.5 `/settings/fulfillment` — `FulfillmentRoutingPage`

**Purpose:** Map sellers to warehouses with primary/priority configuration.

**Layout:**

```
┌──────────────────────────────────────────────────────────┐
│  Fulfillment Routing                   [+ Add Mapping]   │
├──────────────────────────────────────────────────────────┤
│  Seller filter ▾          Warehouse filter ▾             │
├──────┬─────────────┬──────────────┬─────────┬───────────┤
│  ID  │ Seller      │ Warehouse    │Priority │ Primary   │
├──────┼─────────────┼──────────────┼─────────┼───────────┤
│  1   │ Shopee MY   │ Warehouse A  │  0      │ ★ Yes     │
│  2   │ Shopee MY   │ Warehouse B  │  1      │   No      │
│  3   │ Lazada MY   │ Warehouse A  │  0      │ ★ Yes     │
└──────┴─────────────┴──────────────┴─────────┴───────────┘
```

**API:** CRUD for `seller-warehouses` (4 new endpoints).

---

## 7. Implementation Order

### Phase 1 — Backend: Location & Lot CRUD (v0.5.23)
1. Add `POST /warehouse/:id/locations` endpoint
2. Add `PATCH /warehouse/locations/:id` endpoint
3. Add `DELETE /warehouse/locations/:id` endpoint
4. Add `GET/POST/PATCH /warehouse/stock-lots` endpoints
5. Add `GET /items/:id/history` endpoint
6. Test all new endpoints via Swagger UI

### Phase 2 — Backend: Settings & Threshold Endpoints (v0.5.24)
1. Add CRUD endpoints for `inventory-types` (GET/POST/PATCH/DELETE)
2. Add CRUD endpoints for `movement-types` (POST/PATCH/DELETE — GET exists)
3. Add `PATCH /warehouse/:id/inventory/:levelId` for threshold editing
4. Add `GET /warehouse/:id/inventory/:levelId/replenishment-history`
5. Add CRUD endpoints for `seller-warehouses`

### Phase 3 — Frontend: Location & Lot Pages (v0.5.25 – v0.5.26)
1. Add new TS interfaces to `base_types/warehouse.ts` (StockLot, InventoryLocation CRUD, InventoryType, etc.)
2. Add new API functions to `base/warehouse.ts`
3. `pages/warehouse/LocationManagerPage.tsx` + `LocationsGrid.tsx` + `LocationBreadcrumb.tsx`
4. `pages/warehouse/StockLotListPage.tsx` + `StockLotFormPage.tsx` + `ExpiryBadge.tsx`
5. Add routes and sidebar item for Lot Tracking

### Phase 4 — Frontend: Item Detail & History (v0.5.27)
1. Add `GET /items/:id/history` API function to `base/items.ts`
2. Add `ItemsHistoryRead` to `base_types/items.ts`
3. `pages/items/ItemDetailPage.tsx` + `ItemHistoryTimeline.tsx`
4. Add `/catalog/items/:id` route (must be placed AFTER `/catalog/items/new` and `/catalog/items/upload` in App.tsx)

### Phase 5 — Frontend: Settings & Threshold Editing (v0.5.28)
1. `pages/settings/WarehouseSettingsPage.tsx` (reuse `AttributeCard`)
2. `pages/warehouse/ThresholdEditor.tsx` (inline/modal on InventoryLevelsPage)
3. `pages/settings/FulfillmentRoutingPage.tsx` + `SellerWarehouseMatrix.tsx`
4. Convert Settings sidebar to submenu with 3 children

### Phase 6 — Frontend: Dashboard Enhancement (v0.5.29 – v0.5.30)
1. `pages/dashboard/StockSummaryCard.tsx`
2. `pages/dashboard/ActiveAlertsWidget.tsx`
3. `pages/dashboard/RecentMovementsWidget.tsx`
4. `pages/dashboard/ExpiringLotsWidget.tsx`
5. Enhance `DashboardPage.tsx` with responsive grid layout

### Phase 7 — Refactors & Shared Components (ongoing)
1. Extract `ItemSearchSelect` to `components/common/` (used in 3+ pages)
2. Extract `BundleATPCard` from inline code in `InventoryLevelsPage`
3. Extract `AlertTypeBadge` from inline code in `InventoryAlertsPage`
4. Documentation updates: `version_update.md`, `frontend-development-progress.md`, `web-api.md`

---

## 8. Verification Checklist

### Backend Endpoints

| # | Test | Expected |
|---|------|----------|
| 1 | `POST /api/v1/warehouse/1/locations` with section/zone/aisle | 201 + location record |
| 2 | `PATCH /api/v1/warehouse/locations/1` | 200 + updated location |
| 3 | `DELETE /api/v1/warehouse/locations/1` | 204 |
| 4 | `GET /api/v1/warehouse/stock-lots?item_id=1` | 200 + lot list |
| 5 | `POST /api/v1/warehouse/stock-lots` with batch + expiry | 201 + lot record |
| 6 | `GET /api/v1/items/1/history` | 200 + history records with snapshot_data |
| 7 | `GET /api/v1/warehouse/inventory-types` | 200 + type list |
| 8 | `POST /api/v1/warehouse/inventory-types` | 201 + new type |
| 9 | `PATCH /api/v1/warehouse/1/inventory/1` with reorder_point=20 | 200 + updated level |
| 10 | `POST /api/v1/warehouse/seller-mappings` | 201 + mapping record |

### Frontend Pages

| # | Test | Expected |
|---|------|----------|
| 11 | Navigate to `/inventory/warehouses/1/locations` | Location grid renders with existing locations |
| 12 | Create location via modal | Row appears with preview code |
| 13 | `/inventory/lots` page loads | Lot list with expiry badges |
| 14 | Create lot with expiry date | Row appears with ExpiryBadge |
| 15 | `/catalog/items/1` | Item detail page with 4 tabs |
| 16 | History tab loads | Timeline of changes with diff display |
| 17 | `/settings/warehouse` | Two AttributeCards for InventoryType + MovementType |
| 18 | Edit reorder_point on stock levels page | ThresholdEditor saves, stock_status recalculates |
| 19 | `/settings/fulfillment` | Seller-warehouse routing table |
| 20 | Dashboard widgets populated | Stock summary, alerts, movements, expiring lots |
| 21 | Sidebar: Lot Tracking link | Navigates to `/inventory/lots` |
| 22 | Sidebar: Settings submenu | Expands with 3 children |

---

## 9. Changelog

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-03 | Initial plan created (v0.5.12–v0.5.16 scope) | Define warehouse frontend module + items completion review |
| 2026-03-04 | **Full revision** — updated to v0.5.22 baseline | Original plan fully delivered; new plan covers entity analysis, gap identification, 6 new pages, 19 table TS interfaces, and phased implementation for v0.5.23–v0.5.30 |
