# Frontend Development Progress

All frontend updates, changes, and new feature implementations are documented here. Each entry must state **what** was changed and **why**.

Format: `[PRE-ALPHA vX.Y.Z | YYYY-MM-DD HH:MM] — Brief title`

---

## Frontend Ground Rules

1. Document all updates in this file (`frontend-development-progress.md`)
2. Document all APIs in `web-api.md`
3. Version naming aligned with backend `PRE-ALPHA vX.Y.Z`
4. Comprehensive API testing for all endpoints
5. UI color templates unchanged unless explicitly approved
6. All errors logged in `frontend-error.md` (mark as fixed when resolved)
7. **File Organisation**: Every new page and ALL its page-specific items (sub-components, helpers, types) must live inside a dedicated subfolder under `src/pages/` (e.g., `src/pages/settings/SettingsPage.tsx`, `src/pages/settings/AttributeCard.tsx`). Create the subfolder if it does not yet exist. `src/components/` is strictly reserved for universal/shared components used across multiple pages (e.g., DataTable, PageHeader, Sidebar)
8. **Styling Standards**: All CSS must be in separate files — no inline styles or in-component style blocks
9. **Routing Configuration**: Use `BrowserRouter` for application routing
10. **Tailwind CSS**: Use Tailwind CSS v4 as the base styling framework — all new styling must use Tailwind utility classes. MUI `sx` prop and `.styles.ts` files are deprecated and will be migrated to Tailwind

---

## [PRE-ALPHA v0.5.54 | 2026-03-11] — Bundle Mass Upload

**What changed:** Built a full bundle mass upload feature (backend endpoint + frontend page). Users can upload CSV/Excel files where each row is a bundle component. Rows with the same `bundle_sku` are grouped into a single bundle.

**Why:** Bundles tab in the Mass Upload page was a "coming soon" placeholder. Users need to bulk-create bundles from spreadsheets, especially when migrating existing bundle data or creating many bundles at once.

### New files
- `src/pages/items/BundlesMassUploadPage.tsx` — Full upload page: CSV template download, drag-drop file picker, SheetJS preview table, result display with success/error counts and per-row error table
- `backend/app/services/items_import/bundle_importer.py` — Backend service: parses CSV/Excel, groups by bundle_sku, resolves FKs, validates component SKUs, creates Item + PlatformSKU + ListingComponent records

### Modified files
- `backend/app/routers/items.py` — Added `POST /items/bundles/import` endpoint
- `src/api/base/items.ts` — Added `importBundles()` function
- `src/pages/items/CatalogUploadPage.tsx` — Bundles tab now renders `BundlesMassUploadPage` instead of placeholder

### API endpoint
- `POST /api/v1/items/bundles/import` — File upload (multipart/form-data), returns `ImportResult` (total_rows, success_rows, error_rows, errors[])

---

## [PRE-ALPHA v0.5.53 | 2026-03-11] — Tabbed Create & Upload Pages

**What changed:** "Create New Item" and "Mass Upload" pages now have Item/Bundle tabs instead of being item-only. Created `CatalogCreatePage` (Item/Bundle segmented tabs wrapping existing form pages) and `CatalogUploadPage` (Items/Bundles tabs, bundle upload shows "coming soon" placeholder). Added `hideHeader` prop to `ItemFormPage`, `BundleFormPage`, and `ItemsMassUploadPage`. Nav entry renamed to "Create New".

**Why:** Users needed a unified creation flow — switching between creating an item vs a bundle should be a tab click, not a different page. Same for mass upload, which will support bundles in a future release.

### New files
- `src/pages/items/CatalogCreatePage.tsx` — Wrapper with segmented tabs (Item/Bundle); reads `?type=bundle` query param for deep-linking
- `src/pages/items/CatalogUploadPage.tsx` — Wrapper with segmented tabs (Items/Bundles); bundles tab shows placeholder

### Modified files
- `src/pages/items/ItemFormPage.tsx` — Added `hideHeader` prop
- `src/pages/bundles/BundleFormPage.tsx` — Added `hideHeader` prop; back button points to `/catalog/items`
- `src/pages/items/ItemsMassUploadPage.tsx` — Added `hideHeader` prop
- `src/pages/items/ItemsListPage.tsx` — "Create Bundle" dropdown navigates to `/catalog/items/new?type=bundle`
- `src/App.tsx` — Routes updated: `/catalog/items/new` → CatalogCreatePage, `/catalog/items/upload` → CatalogUploadPage, `/catalog/bundles/new` redirects
- `src/components/layout/nav.config.tsx` — "Create New Item" → "Create New"; isActive covers bundle paths

---

## [PRE-ALPHA v0.5.52 | 2026-03-11] — Unified "My Items" Page (Items + Bundles Merged)

**What changed:** Merged the separate Items list (`ItemsListPage`) and Bundles list (`BundlesListPage`) into a single unified "My Items" page. Removed separate Bundles/Create Bundle nav entries; `/catalog/bundles` now redirects to the unified page.

**Why:** Users had to switch between two separate pages to manage items and bundles. Consolidating into one page reduces navigation friction, provides a unified view of all catalog items, and simplifies the Catalog sidebar section.

### Modified files
- `src/pages/items/ItemsListPage.tsx` — Complete rewrite: dual-tab system (primary: All/Items/Bundles; secondary: All/Live/Unpublished/Deleted), dropdown "Add New" button (Create Item / Create Bundle), visual Bundle badge (violet, LayersIcon), expandable rows for bundle components (fetched via `getBundle()`) and item variations, combined status counts across items and bundles, Item Type filter dropdown (hidden on Bundles tab)
- `src/components/layout/nav.config.tsx` — Removed "Bundles" and "Create Bundle" nav entries; renamed "Items" to "My Items"; extended `isActive` to cover bundle paths
- `src/App.tsx` — `/catalog/bundles` route redirects to `/catalog/items`; removed `BundlesListPage` import

### Key features
- **Primary tabs**: All (items+bundles combined), Items (excludes bundle type), Bundles (uses `listBundles` API)
- **Secondary tabs**: All, Live, Unpublished, Deleted — counts sum across items+bundles on "All" tab, filter per-type otherwise
- **Add New dropdown**: single button with Create Item / Create Bundle options
- **Bundle badge**: violet pill with LayersIcon in Item Type column
- **Expandable rows**: bundles show component table (item, SKU, qty); items show variation table
- **Smart dispatch**: delete/restore/toggle calls correct API (item vs bundle) based on `item_type`

---

## [PRE-ALPHA v0.5.46 | 2026-03-09] — My Bundles Dashboard

**What changed:** Built the "My Bundles" dashboard page (`BundlesListPage`) mirroring the existing "My Items" page structure, with a dedicated backend API for listing bundles with component counts.

**Why:** The `/catalog/bundles` route was a PlaceholderPage. Users need a dedicated dashboard to view, search, filter, toggle status, soft-delete, restore, and inspect bundles — matching the established UX pattern from the Items module.

### New files
- `src/pages/bundles/BundlesListPage.tsx` — Full bundles dashboard: card header ("My Bundles" + "+ Create New Bundle"), 4 tabs (All/Live/Unpublished/Deleted with counts), DataTable with columns (Bundle, Components, Category, Status, Brand, Actions), expandable rows showing component breakdown
- `src/pages/bundles/BundleFilters.tsx` — Filter bar: search (name/SKU) + Category dropdown + Brand dropdown

### Modified files
- `src/App.tsx` — `/catalog/bundles` route now renders `BundlesListPage` (was PlaceholderPage)
- `src/api/base_types/items.ts` — Added `BundleListItem` interface (extends `ItemRead` with `component_count`, `total_quantity`)
- `src/api/base/items.ts` — Added `listBundles()`, `getBundleCounts()`, `getBundle()` functions; added `ListBundlesParams` interface
- `src/pages/bundles/BundleFormPage.tsx` — Edit mode now uses `getBundle(id)` instead of `updateBundle(id, {})` workaround

### Key features
- **Components column**: Badge showing "3 Items (7 qty)" per bundle — data from new `GET /items/bundles` endpoint with LEFT JOIN component counts
- **Expand-to-view**: Clicking a bundle row fetches and displays a component breakdown table (item name, SKU, quantity) via `GET /items/bundles/{id}`
- **Soft-delete/restore**: Uses `DELETE /items/bundles/{id}` and `POST /items/bundles/{id}/restore` — same endpoints from v0.5.45
- **Status toggle**: Inline switch that calls `PATCH /items/bundles/{id}` with `is_active` toggle
- **Tabs with counts**: Dedicated `GET /items/bundles/counts` endpoint scoped to Bundle type

---

## [PRE-ALPHA v0.5.44 | 2026-03-09] — Bundle Form Page (Create / Edit)

**What changed:** Built the complete bundle creation and editing UI: a dedicated form page with searchable item picker, dynamic component list with quantity steppers, and full integration with the `POST /items/bundles` and `PATCH /items/bundles/{id}` backend endpoints.

**Why:** The `/catalog/bundles` route was a PlaceholderPage. This implements the form for creating and modifying bundles — allowing users to search for items, add them as components with quantities, set bundle metadata (SKU, name, category, platform/seller), and submit in a single atomic transaction.

### New files
- `src/pages/bundles/BundleFormPage.tsx` — Main form page (create + edit modes); uses `react-hook-form`, loads dropdown options via `Promise.allSettled`, validates bundle composition client-side, handles image upload, platform/seller selection (create-only), component management
- `src/pages/bundles/ComponentSearch.tsx` — Searchable dropdown that queries `GET /items` with debounce (350ms), excludes already-added items and Bundle-type items, shows thumbnail + name + SKU per result
- `src/pages/bundles/ComponentList.tsx` — Dynamic component table with +/- stepper buttons, direct quantity input, delete per row, summary bar (component count + total quantity)

### Modified files
- `src/api/base_types/items.ts` — Added `BundleComponentInput`, `BundleCreateRequest`, `BundleUpdateRequest`, `BundleComponentRead`, `BundleReadResponse` interfaces
- `src/api/base/items.ts` — Added `createBundle()` and `updateBundle()` API functions
- `src/App.tsx` — Added routes: `/catalog/bundles/new` and `/catalog/bundles/:id/edit` pointing to `BundleFormPage`
- `src/components/layout/nav.config.tsx` — Added "Create Bundle" nav leaf under Catalog; updated Bundles leaf with `isActive` override to exclude `/new` sub-path

### UI features
- **Searchable item picker**: type-ahead search (min 2 chars, 350ms debounce) queries active items, excludes Bundle-type items and already-selected items; dropdown shows thumbnail + name + SKU
- **Component table**: inline quantity stepper (+/- buttons + direct input), row delete, row numbers, summary bar with total count
- **Bundle metadata**: name, SKU, SKU display name, description, category/brand/UOM dropdowns, image upload, active toggle
- **Platform/Seller**: required in create mode only (filtered sellers by selected platform); hidden in edit mode
- **Client-side validation**: required fields, SKU no-spaces rule, bundle composition rules (>1 items or qty > 1), platform/seller required in create mode
- **Error handling**: server error messages displayed in alert box; loading spinner during submit

---

## [PRE-ALPHA v0.5.40 | 2026-03-07] — Warehouse Overview & Location Management in Settings

**What changed:** Replaced the Settings Warehouse tab placeholder with a full warehouse management experience: embedded warehouse table + inline location management panel.

**Why:** The Warehouse tab was a stub. This implements the complete feature set: warehouse CRUD, hierarchical location tree, bulk pattern generator, and CSV/Excel import.

### New files
| File | Purpose |
|---|---|
| `pages/settings/WarehouseSettingsTab.tsx` | Warehouse table (all CRUD), expandable location panel per row |
| `pages/settings/warehouse_locations/BulkCreationWizard.tsx` | Pattern-based location generator with Cartesian product preview |
| `pages/settings/warehouse_locations/CsvLocationImport.tsx` | SheetJS-powered file import with validation + progress bar |
| `pages/settings/warehouse_locations/LocationTree.tsx` | Nested tree (Section→Zone→Aisle→Rack→Bin) with edit/delete per node |
| `pages/settings/warehouse_locations/PreviewTable.tsx` | Preview table for generated locations |
| `pages/settings/warehouse_locations/EditNodeModal.tsx` | Modal to rename a single tree node |
| `pages/settings/warehouse_locations/LocationManagementPage.css` | Panel layout CSS |

### Modified files
| File | Change |
|---|---|
| `pages/settings/LocationManagementSection.tsx` | Added `overrideWarehouseId`/`overrideWarehouseName` props; added Generator/Import tab switcher |
| `pages/settings/SettingsPage.tsx` | Warehouse tab renders `<WarehouseSettingsTab />` |
| `api/base_types/warehouse.ts` | Added `is_active`, `sort_order` to `InventoryLocationCreate/Update` |

### Feature breakdown
- **Warehouse table** — compact table with search, status filter, Add/Edit modal, status toggle, duplicate, soft delete; clicking "Manage" on any row expands an inline location panel
- **Location Tree** — hierarchical expand/collapse tree with type badges, location counts, hover edit/delete actions
- **Pattern Generator** — enable each hierarchy level independently; set prefix + numeric range (with zero-padding) or explicit comma-separated values; preview Cartesian product before committing
- **CSV/Excel Import** — download template → upload file → parse + validate → preview with error highlighting → import row-by-row with live progress bar → result summary

---

## [PRE-ALPHA v0.5.39 | 2026-03-07] — Warehouse Settings Grid Refactor

**What changed:** Refactored `WarehouseCard.tsx` (Settings > Warehouse > Management tab) into a fully responsive CSS Grid with a permanently-visible primary action card.

**Why:** The previous implementation violated several UI contracts: the `+ Create` CTA card disappeared while the form was open (breaking the "always first" slot requirement), used non-standard breakpoints (`sm/xl`), and had no empty state for zero warehouses.

### Changes in detail

| Change | Before | After |
|---|---|---|
| Grid breakpoints | `cols-1 sm:cols-2 lg:cols-3 xl:cols-4` | `cols-1 md:cols-2 lg:cols-4` |
| CTA card visibility | Hidden when form open | Always visible in slot 0 |
| Create form placement | Inside grid as `col-span-full` replacing CTA | Above the grid; CTA card stays in position |
| CTA toggle behaviour | n/a | Click again to close form (icon rotates 45°) |
| Name font weight | `font-semibold` | `font-bold` |
| Status badge | Inline JSX | Extracted `<StatusBadge />` component |
| CTA card | Inline JSX | Extracted `<CreateWarehouseCard />` component |
| Empty state | None | `<EmptyState />` with inbox icon + copy |

### Files modified
- `frontend/src/pages/settings/WarehouseCard.tsx` — full refactor (no new files created; all sub-components stay in the same file per single-file convention)

---

## [PRE-ALPHA v0.5.35 | 2026-03-06] — Move Location Management into Settings > Warehouse > Locations & Sections

**What changed:** Relocated the Location Management UI (Location Tree, Bulk Creation Wizard, Preview Table) from its standalone page (`/inventory/locations`) into the Settings page's **Warehouse > Locations & Sections** sub-tab. Created `LocationManagementSection.tsx` in `pages/settings/` as the section wrapper. Removed the standalone route, nav item, and `LocationManagementPage.tsx`. The underlying components (`LocationTree`, `BulkCreationWizard`, `PreviewTable`) remain in `pages/warehouse/locations/` and are imported by the settings section.

**Why:** The user requested the location management UI live inside the Settings > Warehouse configuration area rather than as a standalone page, keeping all warehouse configuration tools in one administrative surface.

### Files created

| File | Purpose |
|------|---------|
| `pages/settings/LocationManagementSection.tsx` | Settings-embedded version of the location management UI: uses `useWarehouse()` context, TanStack Query for hierarchy + bulk-generate, two-column layout (tree + wizard/preview) with `border` styling (no nested cards inside the settings card) |

### Files modified

| File | Change |
|------|--------|
| `pages/settings/SettingsPage.tsx` | Replaced `WarehouseLocationCard` import/usage with `LocationManagementSection` in the "configuration" sub-tab |
| `App.tsx` | Removed `/inventory/locations` route and `LocationManagementPage` import |
| `components/layout/nav.config.tsx` | Removed "Locations" leaf from Inventory section |

### Files deleted

| File | Why |
|------|-----|
| `pages/warehouse/locations/LocationManagementPage.tsx` | Dead code — functionality moved to `LocationManagementSection` |

### Build

- TypeScript: zero errors
- Production: 949.39 kB JS (-5 kB), 37.11 kB CSS

---

## [PRE-ALPHA v0.5.34 | 2026-03-06] — Warehouse Location Management Components

**What changed:** Built location management components with three parts: a Location Tree sidebar (accordion-style hierarchy navigation), a Bulk Creation Wizard (range inputs for each hierarchy level), and a Preview Table (Cartesian product preview before saving). Integrated TanStack Query for API state management and Lucide React for icons. Added TypeScript types and API functions for hierarchy and bulk-generate endpoints.

**Why:** Warehouse managers need a visual tool to explore the location hierarchy and scaffold hundreds of locations at once. These components bridge the backend bulk-generate and hierarchy endpoints (v0.5.32-v0.5.33) with a purpose-built frontend interface.

### Dependencies added

| Package | Version | Purpose |
|---------|---------|---------|
| `@tanstack/react-query` | ^5.x | Server-state management — `useQuery` for hierarchy fetch, `useMutation` for bulk-generate with automatic cache invalidation |
| `lucide-react` | ^0.x | Icon library for tree nodes and wizard UI (ChevronRight, Warehouse, MapPin, Save, etc.) |

### Files created (all in `src/pages/warehouse/locations/`)

| File | Purpose |
|------|---------|
| `LocationTree.tsx` | Recursive accordion component — renders `LocationTreeNode[]` with expand/collapse, level-specific icons, count badges, display_code for leaves |
| `BulkCreationWizard.tsx` | 5 segment cards (section/zone/aisle/rack/bin) with enable toggle, range/values mode selector, prefix/start/end/pad inputs, client-side Cartesian product preview, live validation, total combinations counter with 10K limit |
| `PreviewTable.tsx` | Paginated preview table (50 rows/page) showing generated location codes before API call, active-column detection, large-batch warning |
| `LocationManagementPage.css` | Fixed-width tree panel (340px), scrollbar styling, responsive stacking below 1024px |

### Files modified

| File | Change |
|------|--------|
| `App.tsx` | Wrapped Routes in `QueryClientProvider` |
| `api/base_types/warehouse.ts` | Added `LocationTreeNode`, `SegmentRangeInput`, `BulkGenerateRequest`, `BulkGenerateError`, `BulkGenerateResponse` types |
| `api/base/warehouse.ts` | Added `getLocationHierarchy()`, `bulkGenerateLocations()` API functions |

### UX decisions

- **Two-column layout** — Tree sidebar (340px fixed) on the left for exploration, wizard + preview on the right for bulk operations. Stacks vertically on mobile (<1024px).
- **Client-side preview** — Cartesian product computed in TypeScript (`expandSegment` + `cartesianProduct`) before any API call, giving instant feedback. The same computation runs on the backend for the actual insert.
- **Range vs Values mode** — Each hierarchy level can use numeric ranges (prefix + start/end/pad) or an explicit comma-separated values list (e.g. "COLD, DRY, AMBIENT"). This matches the backend `SegmentRange` two-mode design.
- **10,000 combination limit** — Validated client-side and displayed as an error banner; matches backend `MAX_COMBINATIONS` guard.
- **TanStack Query cache invalidation** — On successful bulk-generate, the `location-hierarchy` query is automatically invalidated, causing the tree sidebar to refresh with the newly created locations.
- **Lucide icons for tree** — Different icon per hierarchy level (Warehouse, LayoutGrid, MapPin, ArrowRightLeft, Server, Box) for visual distinction at a glance.

---

## [PRE-ALPHA v0.5.29 | 2026-03-06] — Layout Restructure: Full-Width Header + Global Warehouse Context

**What changed:** Restructured `MainLayout.tsx` to match the new wireframe layout. The header now spans the full viewport width (fixed positioning, z-1300) with Logo, Hamburger, Search, Account dropdown, and a Notification bell placeholder. The sidebar starts below the header with a global `WarehouseSelector` at the top. Created `WarehouseContext` for app-wide warehouse state and migrated all three inventory pages to consume it.

**Why:** The previous layout had the logo/brand inside the sidebar and the top bar nested inside the main content area (offset by sidebar margin). The wireframe calls for a full-width top header above both sidebar and content, consistent with modern dashboard patterns. The global warehouse selector replaces per-page selectors so operators set the warehouse once and it persists across pages.

### Files created

| File | Purpose |
|------|---------|
| `api/contexts/WarehouseContext.tsx` | React context providing `warehouses`, `selectedWarehouseId`, `selectedWarehouse`, `setSelectedWarehouseId`, `loading`. Fetches active warehouses on mount, persists selection to `localStorage` (`selected_warehouse_id`), auto-selects first warehouse if nothing persisted. |
| `components/layout/WarehouseSelector.tsx` | Sidebar pill-shaped dropdown that reads from `useWarehouse()` context. Shows warehouse name + chevron when expanded, icon-only when collapsed, dropdown with checkmark for selected item. |

### Files modified

| File | Change |
|------|--------|
| `components/layout/MainLayout.tsx` | Extracted header to fixed full-width top bar (`z-[1300]`, `h-16`); moved logo from sidebar to header; added `NotificationsNoneIcon` placeholder; replaced sidebar brand area with `LayoutWarehouseSelector`; sidebar `top: 64px`, `height: calc(100vh - 64px)`; added `HEADER_HEIGHT` constant |
| `App.tsx` | Wrapped `<MainLayout />` in `<WarehouseProvider>` inside the `ProtectedRoute` route element |
| `pages/warehouse/InventoryLevelsPage.tsx` | Replaced local `warehouseId` state + `WarehouseSelector` import with `useWarehouse()` context; removed per-page warehouse dropdown from header |
| `pages/warehouse/InventoryMovementsPage.tsx` | Same migration to global warehouse context |
| `pages/warehouse/InventoryAlertsPage.tsx` | Same migration to global warehouse context |

### UX decisions
- Logo text ("WOMS") is hidden on very small screens (`hidden sm:inline`) to save header space
- Notification bell is a static placeholder — no badge or dropdown until backend notification system exists
- Warehouse selector adapts to sidebar collapsed state: shows icon-only when collapsed, with a flyout dropdown positioned to the right
- Inventory pages no longer show "Select a warehouse" empty states when using global context (auto-selects first warehouse)
- Existing `pages/warehouse/WarehouseSelector.tsx` kept intact for backward compatibility

---

## [PRE-ALPHA v0.5.23 | 2026-03-04] — Settings Module Expansion

**What changed:** Settings page reorganised into three named sections. Added `PlatformCard` for marketplace CRUD and `WarehouseLocationCard` for per-warehouse storage location management. Backed by new backend endpoints and API layer.

**Why:** Operators need to configure warehouse topology (locations) and marketplace connections (platforms) from the same administrative surface as item attribute tables.

### Files added

| File | Purpose |
|------|---------|
| `pages/settings/PlatformCard.tsx` | Inline Add/Edit card for platform CRUD — name, address, postcode, API endpoint, active toggle |
| `pages/settings/WarehouseLocationCard.tsx` | Per-warehouse location card — dropdown to select warehouse, grid form for section/zone/aisle/rack/bin, formatted code display (`A-Z1-01`) |
| `api/base_types/platform.ts` | `PlatformRead/Create/Update`, `SellerRead/Create/Update` types |
| `api/base/platform.ts` | `listPlatforms`, `createPlatform`, `updatePlatform`, `listSellers`, `createSeller`, `updateSeller` functions |

### Files modified

| File | Change |
|------|--------|
| `pages/settings/SettingsPage.tsx` | Reorganised into 3 sections: **Items Data** (Item Types, Categories, Brands, UOMs, Statuses), **Warehouse** (WarehouseLocationCard), **Platforms** (PlatformCard); section headings + descriptions added |
| `api/base_types/warehouse.ts` | Added `InventoryLocationCreate` and `InventoryLocationUpdate` types |
| `api/base/warehouse.ts` | Added `createLocation`, `updateLocation`, `deleteLocation` API functions |

### UX decisions
- Location code displayed as `section-zone-aisle-rack-bin` with blank parts omitted; falls back to `LOC-{id}`
- Platform delete omitted intentionally — platforms are reference data linked to order history; deactivation via toggle is the safe operation
- Both cards share the same inline form expansion pattern as `AttributeCard` for consistency

---

## [PRE-ALPHA v0.5.22 | 2026-03-04 16:00] — Bundle Image Upload + Delete

**What changed:** Image upload capability added to `BundleFormPage`; delete action added to `CatalogBundlesPage`; bundle list now shows a thumbnail column.

**Why:** Operators need to visually identify bundles the same way they do regular items. Delete allows removing stale bundles without DB access.

### Files modified

| File | Change |
|------|--------|
| `pages/catalog/BundleFormPage.tsx` | +`imageUrl`/`imageUploading` state + `fileInputRef`; image upload UI block (click-to-upload square, preview, remove button, hidden file input); `image_url` in create + update payloads; edit-mode sets `imageUrl` from `item.image_url` |
| `pages/catalog/CatalogBundlesPage.tsx` | +`deleteItem`, `DeleteOutlineIcon`, `ImageIcon` imports; +`deleting` state; +`handleDelete()` with confirm dialog; Bundle Name column shows thumbnail; Actions column is now edit + delete pair |

### UX decisions
- Upload pattern identical to `ItemFormPage` — consistency is intentional so operators learn one pattern
- Thumbnail placeholder matches `ItemsListPage` style exactly

---

## [PRE-ALPHA v0.5.21 | 2026-03-04 14:00] — Bundles Sub-Module (Catalog)

**What changed:** New Bundles sub-module under Catalog — dedicated list page and create/edit form for Bundle-type items.

**Why:** Bundle creation has a distinct workflow (component picker, qty validation, SKU generation) that does not belong in the general Item form. A dedicated sub-module gives operators a purpose-built interface while reusing the existing `ItemBundleComponent` BOM backend (v0.5.17) and `BundleComponentsTab` (v0.5.20).

### Files created/modified

| File | Change |
|------|--------|
| `pages/catalog/CatalogBundlesPage.tsx` | NEW — Bundle list: type ID resolved via `listItemTypes()`, filters items by `item_type_id`, DataTable with toggle/search/pagination |
| `pages/catalog/BundleFormPage.tsx` | NEW — Create mode: local `PendingComponent[]` + batch submit; Edit mode: embeds `BundleComponentsTab`; auto-SKU toggle; live ≥2 qty validation |
| `components/layout/MainLayout.tsx` | +`RedeemIcon`; Bundles MenuItem under Catalog SubMenu |
| `App.tsx` | +3 routes: `/catalog/bundles`, `/catalog/bundles/new`, `/catalog/bundles/:id/edit` |

### UX decisions
- **Auto-generate SKU** is a toggle — reactive, read-only while enabled; clears back to editable on disable
- **Qty indicator** has three states (green/amber/neutral) so operator always knows how far they are from the minimum
- **Batch create submission** — item is created first, then components are added in a loop; on any component failure the bundle item still exists and operator is redirected to edit mode to add remaining components
- **Bundle type ID lookup** — resolved once on mount, cached in state; if "Bundle" type not found in seed, a configuration error state is shown with remediation instructions

---

## [PRE-ALPHA v0.5.20 | 2026-03-04 10:00] — Bundle SKU Frontend UI

**What changed:** Frontend Phase 4 of the Bundle SKU module — BOM management on the Item Form, Bundle ATP Lookup on the Inventory Levels page, and bundle fulfillment support in the Record Movement modal.

**Why:** Closes the bundle SKU feature loop started in v0.5.17–v0.5.19. Warehouse operators need a UI to manage Bill-of-Materials for bundle products, look up live bundle ATP without raw API calls, and record a bundle sale that deducts all component stocks atomically in a single operation.

### Files created/modified

| File | Change |
|------|--------|
| `api/base_types/items.ts` | +5 bundle types (BundleComponentRead/Create/Update, BundleATPRead, BundleMembershipRead) |
| `api/base/items.ts` | +6 bundle API functions |
| `api/base_types/warehouse.ts` | +`reserved_quantity` on enriched level; +4 fulfillment types |
| `api/base/warehouse.ts` | +3 fulfillment API functions (reserveStock, releaseStock, fulfillBundle) |
| `pages/items/BundleComponentsTab.tsx` | NEW — BOM editor: search items, add/toggle/remove components |
| `pages/items/ItemFormPage.tsx` | Tab strip (Details / Bundle Components) when item_type = "Bundle" in edit mode |
| `pages/warehouse/InventoryLevelsPage.tsx` | Collapsible Bundle ATP Lookup card; Qty column now shows reserved_quantity |
| `pages/warehouse/InventoryMovementsPage.tsx` | Bundle mode selector when Bundle item selected; fulfill path calls POST /warehouse/fulfill/bundle |

### UX decisions
- **Tab strip** in ItemFormPage only renders in edit mode (bundle must already exist before BOM can be managed)
- **BundleATPLookup** filters item search client-side for `item_type.name === "Bundle"` — avoids new backend endpoint
- **Auto-switch to fulfill mode** — when a Bundle item is selected in the movement modal, fulfill mode is pre-selected; operator can override to manual if needed
- **Inline confirm-remove** pattern on BundleComponentsTab rows — avoids modal overhead for a simple destructive action

---

## [PRE-ALPHA v0.5.17–v0.5.19 | 2026-03-04 01:00] — Bundle SKU Backend (Frontend Phase Pending)

**What changed:** Backend-only release. Bundle SKU schema, services, and API are complete. Frontend (v0.5.20) completed in the next entry.

---

## [PRE-ALPHA v0.5.12 | 2026-03-03 21:00] — Warehouse & Inventory Frontend Module

**What changed:** Built the complete warehouse/inventory frontend module — 4 new pages, shared components, TypeScript types, API functions, sidebar navigation, and routing.

**Why:** The warehouse backend was functional but had no frontend surface. This release gives operations staff a full UI for managing warehouses, monitoring stock levels with color-coded status, recording movements (inbound/outbound/transfer), and resolving inventory alerts.

### New Pages (all in `src/pages/warehouse/`)

1. **WarehouseListPage** (`/inventory/warehouses`) — CRUD list with inline create/edit modal, active status toggle, search, click-through to stock levels
2. **InventoryLevelsPage** (`/inventory/levels`) — Real-time stock matrix with warehouse selector, summary chips (counts by status), status filter tabs (All/OK/Low/Critical/Out of Stock/Overstock), search by item name or SKU
3. **InventoryMovementsPage** (`/inventory/movements`) — Movement history table with Record Movement modal (movement type, item autocomplete, multi-location transactions for transfers, reference number, notes)
4. **InventoryAlertsPage** (`/inventory/alerts`) — Alert action center with resolve modal, unresolved/all/resolved filter, summary chips per alert type

### Shared Page Components (in `src/pages/warehouse/`)

- **StockStatusBadge** — Color-coded badge (green OK, yellow Low, orange/red Critical, red Out of Stock, blue Overstock)
- **WarehouseSelector** — Dropdown that loads active warehouses on mount, used across Levels/Movements/Alerts pages

### API Layer

| File | Contents |
|------|----------|
| `src/api/base_types/warehouse.ts` | 13 TypeScript interfaces: `WarehouseRead/Create/Update`, `InventoryLocationRead`, `LocationSummary`, `InventoryLevelEnrichedRead`, `StockStatus`, `InventoryAlertRead`, `AlertType`, `MovementTypeRead`, `InventoryMovementRead`, `InventoryTransactionCreate`, `InventoryMovementCreate` |
| `src/api/base/warehouse.ts` | 11 API functions: `listWarehouses`, `getWarehouse`, `createWarehouse`, `updateWarehouse`, `listLocations`, `listInventoryLevels`, `listAlerts`, `resolveAlert`, `listMovementTypes`, `listMovements`, `createMovement` |

### Navigation

- Added **Inventory** submenu to `MainLayout.tsx` sidebar with 4 items: Warehouses, Stock Levels, Movements, Alerts
- Added 4 routes to `App.tsx`

### Files Modified / Created

| File | Action |
|------|--------|
| `frontend/src/api/base_types/warehouse.ts` | Created |
| `frontend/src/api/base/warehouse.ts` | Created |
| `frontend/src/pages/warehouse/StockStatusBadge.tsx` | Created |
| `frontend/src/pages/warehouse/WarehouseSelector.tsx` | Created |
| `frontend/src/pages/warehouse/WarehouseListPage.tsx` | Created |
| `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` | Created |
| `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` | Created |
| `frontend/src/pages/warehouse/InventoryAlertsPage.tsx` | Created |
| `frontend/src/App.tsx` | Modified — added 4 inventory routes |
| `frontend/src/components/layout/MainLayout.tsx` | Modified — added Inventory submenu + 4 icon imports |

---

## [PRE-ALPHA v0.5.11 | 2026-03-03 16:00] — Items Mass Upload

**What changed:** Implemented an end-to-end mass upload feature for the Items catalog. Users can upload a CSV or Excel file containing multiple items, preview the first 5 rows client-side (via SheetJS), confirm, and have the backend validate and insert all valid rows in one request. Per-row errors are reported back without aborting the entire batch.

**Why:** Manually creating hundreds of items one-by-one is impractical. A mass upload tool with client-side preview and clear per-row error feedback improves the data-entry experience significantly for operations staff.

### Key Features

1. **Client-side parse & preview** — SheetJS (`xlsx`) reads the uploaded file in the browser, extracts the first sheet, and renders the first 5 rows in a preview table before any network call is made. This lets users catch gross formatting errors instantly.
2. **Drag-and-drop dropzone** — Drop zone accepts `.csv`, `.xlsx`, `.xls` via `ondragover`/`ondrop`. Hidden `<input type="file">` handles click-to-select.
3. **Template download** — "Download CSV Template" generates a Blob in-browser (no server call) with the correct column headers and triggers a programmatic download.
4. **Client-side validation** — Extension whitelist, non-empty file, max 10 MB — all checked before the request is sent.
5. **Confirm & Upload flow** — "Upload Items" button appears below the preview. Reverts to dropzone via "Cancel".
6. **Per-row error table** — After upload, shows success count + a table (Row | Master SKU | Error) for every failed row. "Upload Another File" resets the UI.
7. **Backend column normalisation** — `parser.py` maps common header aliases (e.g. `"Product Name"` → `item_name`, `"Internal CODE"` → `master_sku`, `"BaseUOM"` → `uom`) so files from external sources work without manual header renaming.
8. **FK resolution & duplicate detection** — `validator.py` builds in-memory caches (one SELECT per lookup table) and checks for duplicate `master_sku` both within the file and against existing DB rows.
9. **Batch insert** — `importer.py` inserts all valid rows in a single flush; errors do not prevent valid rows from being saved.

### Files Modified / Created

| File | Action |
|------|--------|
| `backend/app/schemas/items.py` | Added `ImportRowError`, `ImportResult` schemas |
| `backend/app/services/items_import/__init__.py` | Created (empty package marker) |
| `backend/app/services/items_import/parser.py` | Created — CSV/Excel parser with alias normalisation |
| `backend/app/services/items_import/validator.py` | Created — FK cache, duplicate check, `is_active` parse |
| `backend/app/services/items_import/importer.py` | Created — orchestrates parse → validate → bulk insert |
| `backend/app/routers/items.py` | Added `POST /import` endpoint |
| `frontend/src/api/base_types/items.ts` | Added `ImportRowError`, `ItemsImportResult` types |
| `frontend/src/api/base/items.ts` | Added `importItems(file)` API function |
| `frontend/src/pages/items/ItemsMassUploadPage.tsx` | Created — full upload page with drag-drop, preview, result |
| `frontend/src/App.tsx` | Added `/catalog/items/upload` route |
| `frontend/src/pages/items/ItemsListPage.tsx` | Wired "Mass Upload" button to navigate to upload page; fixed icon import |

### npm Dependency Added

| Package | Version | Purpose |
|---------|---------|---------|
| `xlsx` | ^0.18.5 | SheetJS — client-side CSV/Excel parsing for preview |

---

## [PRE-ALPHA v0.5.10 | 2026-03-03 14:00] — Create Item: Toggle Switch, Validation & Backend Integrity

**What changed:** Replaced the Status `<select>` with a CSS toggle switch, tightened client-side validation on `master_sku` (no-spaces rule) and `sku_name` (max 500), standardized all select placeholders to "Select", removed the string-to-bool coercion hack from `onSubmit`, and added `disabled:cursor-not-allowed` to the submit button.

**Why:** A boolean field should use a boolean control. The previous select required a runtime type coercion and lacked uniqueness feedback for `master_sku`. The `sku_name` max-length was inconsistent with the backend schema.

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/pages/items/ItemFormPage.tsx` | Status toggle switch (watch+setValue), master_sku no-spaces validation, sku_name maxLength 500, select placeholder "Select", Row 4 → 2-col + toggle row, remove is_active string coercion, disabled:cursor-not-allowed on submit |

### Validation Rules (as-built)

| Field | Rule | Error Message |
|-------|------|---------------|
| item_name | Required, max 500 chars | "Item name is required" / "Max 500 characters" |
| master_sku | Required, max 100 chars, no whitespace | "Master SKU is required" / "Max 100 characters" / "Master SKU must not contain spaces" |
| sku_name | Optional, max 500 chars | "Max 500 characters" |

---

## [PRE-ALPHA v0.5.9 | 2026-03-03 12:00] — VariationBuilder Redesign

**What changed:** Completely redesigned the `VariationBuilder` component to match the specified e-commerce seller-centre style UI, and removed `price`/`stock` from variation combinations.

**Why:** The previous chip-based UI differed from the target design. The new layout uses a 2-column option grid with character counters, drag handles, and per-option delete icons — more ergonomic for product managers entering variation data. Price and stock are removed from variations as they belong in the pricing/order module, not the item catalogue.

### Key Changes

1. **Option grid** — 2-column layout; each option shows an inline `N/20` character counter, a `DragIndicatorIcon` handle (visual), and a delete button
2. **Name counter** — Variation name input now shows `N/14` inline counter on the right
3. **Max 5 options** — Draft "Input" slot appears after committed options up to the 5-option cap
4. **Section header** — Added `• Variations` label above the builder panels
5. **Combination table** — Price and Stock columns removed; only Image + variation values + SKU remain
6. **Type cleanup** — Removed `price` and `stock` fields from `VariationCombination` interface and all utility functions

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/pages/items/VariationBuilder.types.ts` | Removed `price`, `stock` from `VariationCombination` |
| `frontend/src/pages/items/VariationBuilder.utils.ts` | Updated default combo shape; strip price/stock in `migrateOldFormat` |
| `frontend/src/pages/items/VariationBuilder.tsx` | Full redesign — 2-column option grid, char counters, drag handles, simplified combination table |

---

## [PRE-ALPHA v0.5.8 | 2026-03-02 21:00] — Item Main Image Upload

**What changed:** Added a product image upload section to the Item Create/Edit form. Users can click to upload an image (JPG/PNG/WebP/GIF, max 5 MB), see a live preview, and remove the image. The upload goes to a new `POST /items/upload-image` endpoint which stores files locally and returns a URL path. The URL is sent as part of the normal item JSON payload.

**Why:** Items had no visual representation. Product images are essential for e-commerce catalog management and visual identification in the item list.

### Key Features

1. **Click-to-upload area** — 128x128 dashed-border placeholder with ImageIcon; shows preview after upload
2. **Upload-first pattern** — Image uploaded via separate endpoint, URL stored in `image_url` column
3. **Validation** — Content type (4 image formats) + size limit (5 MB) enforced on backend
4. **Remove image** — Click "Remove image" to clear, sets `image_url` to null on save
5. **Edit mode** — Existing image loads and displays on edit

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/api/base_types/items.ts` | Added `image_url` to TypeScript types |
| `frontend/src/api/base/items.ts` | Added `uploadItemImage()` API function |
| `frontend/src/pages/ItemFormPage.tsx` | Added image upload UI section at top of form |
| `frontend/vite.config.ts` | Added `/uploads` proxy rule for dev server |

### Build

- Production: 493.07 kB JS, 25.86 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.7 | 2026-03-02 17:30] — VariationBuilder Component

**What changed:** Replaced the basic variation section in ItemFormPage with a full e-commerce-style VariationBuilder. Users can now define up to 2 variation dimensions with auto-growing option inputs, and a dynamic combination table generates rows for every cartesian product with per-variant SKU, Price, Stock, and image placeholder fields. Includes batch-apply for mass updates.

**Why:** The old variation section was just text rows (attribute name + comma-separated values) with no per-variant data. Sellers need a matrix view to manage individual variation SKUs, prices, and stock levels — matching the UX of Shopee/Lazada seller centers.

### Key Features

1. **Variation Builder** — Define variation name + options with auto-grow inputs (type + Enter to add)
2. **Max 2 Levels** — Primary (e.g. Colour) + optional secondary (e.g. Size)
3. **Combination Table** — Auto-generated rows for every cartesian product
4. **Per-Variant Fields** — SKU, Price, Stock, and image placeholder per combination row
5. **Batch Apply** — Mass-update Price/Stock/SKU across all rows at once
6. **Backwards Compatibility** — `migrateOldFormat()` auto-generates combinations from old attribute-only data

### New Files (all in `src/pages/items/`)

| File | Purpose |
|------|---------|
| `VariationBuilder.types.ts` | Shared interfaces: `VariationsData`, `VariationAttribute`, `VariationCombination` |
| `VariationBuilder.utils.ts` | Pure functions: `cartesianProduct()`, `syncCombinations()`, `migrateOldFormat()` |
| `VariationBuilder.tsx` | Main component + `VariationLevel` and `CombinationTable` sub-components |

### Files Modified

| File | Change |
|------|--------|
| `ItemFormPage.tsx` | Removed `VariationRow`, `useFieldArray`, old helpers; added `useState<VariationsData>` + `<VariationBuilder>` integration |

### Build

- Production: 491.28 kB JS, 25.68 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.6.1 | 2026-03-02 16:00] — Move Item Type to Tabs Row

**What changed:** Relocated the "Item Type" dropdown from the lower filter row to the tabs row, right-aligned via `justify-between`. Removed Item Type props/state/fetch from `ItemFilters.tsx`; added them to `ItemsListPage.tsx`.

**Why:** Item Type (Outgoing Product, Raw Material, Office Supply) is a workspace-level toggle, not a search filter. Elevating it to the tabs row makes it visually distinct and frees space in the filter bar for the remaining Search + Category + Brand controls.

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/pages/items/ItemFilters.tsx` | Removed `itemTypeId`, `onItemTypeChange`, `itemTypes` state, `listItemTypes` import, and `<select>` |
| `frontend/src/pages/ItemsListPage.tsx` | Added `itemTypes` state + fetch; Item Type `<select>` in tabs row with `flex-wrap justify-between`; cleaned up `<ItemFilters>` props |

---

## [PRE-ALPHA v0.5.6 | 2026-03-02] — Items Page Redesign (List + Form)

**What changed:** Redesigned the Items list page and Create/Edit form to match a reference admin dashboard design. Added tab-based status filtering with live counts, checkbox row selection, page-number pagination, combined item column, and flattened the multi-tab form into a single-card layout.

**Why:** The previous v0.5.4 implementation was functional but didn't match the target UX. This redesign improves: (1) status visibility via tab counts, (2) filtering with inline search + Item Type dropdown, (3) data density with combined columns, and (4) form usability by showing all fields at once.

### Key Changes

1. **Tab-based Status Filtering** — All / Live / Unpublished / Deleted tabs with real-time counts from new `GET /items/counts` endpoint
2. **Combined Items Column** — Image placeholder + item name + SKU in a single column
3. **Checkbox Selection** — DataTable now supports `selectable` prop with select-all/individual checkboxes
4. **Page-Number Pagination** — Replaced prev/next with clickable page numbers, ellipsis, first/last buttons
5. **Inline Filters** — Search + Category + Brand dropdowns in filter bar (removed Active/Inactive — tabs handle it; Item Type moved to tabs row in v0.5.6.1)
6. **Single-Card Form** — Removed tab layout; all fields visible in one card (Name+SKU → Description → Category+Brand → UOM+Type+Status → Variations)
7. **Status Badges** — Active (green), Inactive (gray), Deleted (red) inline badges in list

### File Organization

- Moved `ItemFilters.tsx` from `components/items/` → `pages/items/` (page-specific component rule: `components/` is for universal/shared components only)

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/api/base/items.ts` | Added `getItemCounts()`, `item_type_id` + `include_deleted` params |
| `frontend/src/api/base_types/items.ts` | Added `deleted_at` to `ItemRead` |
| `frontend/src/components/common/DataTable.tsx` | Added `selectable`, `noCard` props; page-number pagination |
| `frontend/src/pages/items/ItemFilters.tsx` | Relocated + added search input + Item Type dropdown |
| `frontend/src/pages/ItemsListPage.tsx` | Full redesign with tabs, card wrapper, new columns |
| `frontend/src/pages/ItemFormPage.tsx` | Flattened tabs → single card, reordered fields |

### Build

- Production: 489.60 kB JS, 24.55 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.4 | 2026-03-02] — Items Module (Master Catalog)

**What changed:** Built the complete Items module frontend with a paginated catalog list, advanced filtering, variation row expansion, and a multi-tab create/edit form.

**Why:** The Items module is the core data management interface — users need to browse, search, create, and edit their product catalog with variation support (size, color, etc.).

### Key Features

1. **Item Catalog List** (`/catalog/items`)
   - Server-side paginated DataTable (reusable component)
   - Global search by item name or master SKU (debounced)
   - Column filters: Status, Category, Brand (loaded from backend)
   - Row expansion: click parent items to view child variations inline
   - Edit and Delete actions per row (soft-delete with confirmation)

2. **Item Create/Edit Form** (`/catalog/items/new`, `/catalog/items/:id/edit`)
   - Powered by `react-hook-form` with `useFieldArray` for dynamic variations
   - **Tab 1 — Basic Info**: 9 form fields (name, SKU, description, 5 dropdown selects for lookups, UOM)
   - **Tab 2 — Variations**: Toggle `has_variation`, add attribute rows (name + comma-separated values), auto-generated SKU combination preview grid
   - Edit mode: loads existing item data, master_sku is readonly
   - Validation: required fields, max length enforcement

3. **Reusable DataTable** (`src/components/common/DataTable.tsx`)
   - Generic `<T>` component with typed columns
   - Pagination controls (prev/next, page size selector, "Showing X-Y of Z")
   - Optional search bar, row expansion, header actions slot
   - Consistent Tailwind styling matching project patterns

4. **Sidebar Navigation**
   - New "Catalog" collapsible group with `SubMenu` (react-pro-sidebar)
   - "Items" link with active state detection for `/catalog/*` paths

### New Dependencies
- `react-hook-form` (multi-tab form with dynamic arrays)

### Files Created
- `frontend/src/components/common/DataTable.tsx`
- `frontend/src/components/items/ItemFilters.tsx`
- `frontend/src/pages/ItemsListPage.tsx`
- `frontend/src/pages/ItemFormPage.tsx`

### Files Modified
- `frontend/src/api/base_types/items.ts` — added `ItemRead`, `ItemCreate`, `ItemUpdate`, `PaginatedResponse<T>`
- `frontend/src/api/base/items.ts` — added 5 item CRUD functions
- `frontend/src/App.tsx` — added 3 catalog routes
- `frontend/src/components/layout/MainLayout.tsx` — added Catalog SubMenu nav group

### Build
- Production: 488.06 kB JS, 24.11 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.3 | 2026-02-27 ~00:30] — Settings Page with Item Attributes CRUD

**What changed:** Added a new Settings page (`/settings`) with full CRUD for 5 item-attribute lookup tables: Status, ItemType, Category, Brand, and BaseUOM. Built a reusable `AttributeCard` component that handles inline add/edit/delete for any ID+name pair. Added 20 API functions with normaliser helpers to map varying backend field names to a generic `{ id, name }` interface. Settings nav item added to sidebar.

### New Files

| File | Purpose |
|------|---------|
| `src/api/base_types/items.ts` | `AttributeItem` interface — generic `{ id: number; name: string }` |
| `src/api/base/items.ts` | 20 API functions (4 per table) + 5 normaliser helpers |
| `src/components/settings/AttributeCard.tsx` | Reusable CRUD card: inline add/edit/delete, Enter/Escape keys, error display, loading spinner |
| `src/pages/SettingsPage.tsx` | Settings page with responsive grid (`md:grid-cols-2 xl:grid-cols-3`) of 5 AttributeCards |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/App.tsx` | Added `/settings` route inside protected group | Route to SettingsPage |
| `src/components/layout/MainLayout.tsx` | Added Settings nav item with `SettingsIcon` | Sidebar navigation entry |

### Design Decisions

- **Generic `AttributeItem` type**: All 5 tables have identical structure after normalisation — one component, one interface
- **Normaliser pattern**: Backend uses `status_id`/`status_name`, `uom_id`/`uom_name`, etc. Normalisers at the API boundary convert to uniform `{ id, name }`
- **`Promise.allSettled`**: Loads all 5 tables independently — one table's failure doesn't block others
- **`makeHandlers` factory**: Generates `onCreate`/`onUpdate`/`onDelete` callbacks for each table without repetition
- **MUI icons only**: `AddIcon`, `EditIcon`, `DeleteIcon` from `@mui/icons-material` — consistent with existing icon approach

### Build Result

- TypeScript: zero errors
- Production build: 425.02 kB JS (+8 kB from 5 new API functions + SettingsPage), 16.62 kB CSS

---

## [PRE-ALPHA v0.5.1.6 | 2026-02-26 ~23:30] — Convert layouts/ + components/ to Tailwind, remove MUI theme

**What changed:** Migrated MainLayout, ProtectedRoute, and PageHeader from MUI to native HTML + Tailwind. Removed MUI `ThemeProvider` and `theme.ts` — all design tokens now in `index.css`. Created `useIsMobile` hook to replace MUI `useMediaQuery`. MUI icons retained. JS bundle dropped from 466 kB to 417 kB (-49 kB).

### Components Converted

| Component | MUI Components Removed |
|-----------|----------------------|
| `MainLayout.tsx` | Box, AppBar, Toolbar, Typography, IconButton, useMediaQuery, useTheme |
| `ProtectedRoute.tsx` | Box, CircularProgress |
| `PageHeader.tsx` | Box, Typography |

### New Files

| File | Purpose |
|------|---------|
| `src/hooks/useIsMobile.ts` | Replaces MUI `useMediaQuery` using native `window.matchMedia` |

### Files Deleted

- `MainLayout.styles.ts`, `ProtectedRoute.styles.ts`, `PageHeader.styles.ts`, `common.styles.ts`, `theme/theme.ts`

### MUI Status

- **Still used**: `@mui/icons-material` (8 icons across MainLayout + LoginPage)
- **Removed from app code**: ThemeProvider, CssBaseline, all MUI components (Box, AppBar, Typography, etc.)
- **Kept as peer deps**: `@mui/material`, `@emotion/react`, `@emotion/styled` (required by `@mui/icons-material`)

---

## [PRE-ALPHA v0.5.1.5 | 2026-02-26 ~23:00] — Convert pages/ to Tailwind CSS

**What changed:** Migrated all 6 page components from MUI to native HTML + Tailwind utility classes. JS bundle dropped from 561 kB to 466 kB (-96 kB) by removing MUI component imports from pages.

### Pages Converted

| Page | MUI Components Removed |
|------|----------------------|
| `LoginPage.tsx` | Box, Card, TextField, Button, Typography, Alert, IconButton, InputAdornment, CircularProgress |
| `NotFoundPage.tsx` | Box, Typography, Button |
| `DashboardPage.tsx` | Box, Card, CardContent, Grid, Typography |
| `OrderImportPage.tsx` | Box, Alert |
| `ReferencePage.tsx` | Box, Alert |
| `MLSyncPage.tsx` | Box, Alert |

### Custom CSS Added to `index.css`

| Class | Purpose |
|-------|---------|
| `.login-blob--*` (5 variants) | Decorative gradient circles for login panel |
| `.form-input` / `.form-input--error` | Styled text inputs with focus/error states |
| `.form-label` / `.form-helper` | Input labels and helper text |

### Files Deleted

- `LoginPage.styles.ts`, `NotFoundPage.styles.ts` — replaced by Tailwind classes

---

## [PRE-ALPHA v0.5.1.4 | 2026-02-26 ~22:00] — Add Tailwind CSS v4 as Base Styling Framework

**What changed:** Installed Tailwind CSS v4 with Vite plugin, created base CSS template with project theme tokens, and established ground rule #10 for Tailwind as the new styling standard.

### Setup

| Step | Detail |
|------|--------|
| Install | `tailwindcss` + `@tailwindcss/vite` |
| Vite plugin | Added `tailwindcss()` to `vite.config.ts` plugins |
| Base CSS | `src/index.css` — `@import "tailwindcss"` + `@theme` with all project design tokens |
| Entry point | `main.tsx` imports `index.css`; `CssBaseline` removed (Tailwind preflight replaces it) |

### Available Tailwind Theme Classes

| Class Pattern | Maps To |
|---------------|---------|
| `bg-primary`, `text-primary` | #1565C0 |
| `bg-secondary`, `text-secondary` | #FF8F00 |
| `bg-background` | #F5F7FA |
| `bg-surface` | #FFFFFF |
| `text-text-primary` | #1A1A2E |
| `text-text-secondary` | #555770 |
| `bg-error`, `bg-success`, `bg-warning`, `bg-info` | Semantic colors |
| `font-sans` | Montserrat |
| `rounded-default`, `rounded-card` | 8px, 12px |
| `shadow-card`, `shadow-appbar` | Project shadows |

---

## [PRE-ALPHA v0.5.1.3 | 2026-02-26 ~21:00] — Extract Inline Styles to Separate Files

**What changed:** Extracted all inline MUI `sx` styles from 5 React components into co-located `*.styles.ts` files using typed `SxProps<Theme>` exports. Enforces ground rule #8.

### New Style Files

| File | Exports |
|------|---------|
| `src/styles/common.styles.ts` | `centeredFullPage`, `centeredContentArea` — shared layout primitives |
| `src/pages/LoginPage.styles.ts` | 18 exports — blob helper, form panels, branding, buttons |
| `src/layouts/MainLayout.styles.ts` | 10 exports — sidebar, AppBar, page content, react-pro-sidebar props |
| `src/pages/NotFoundPage.styles.ts` | 3 exports — page root (re-export), error code, error message |
| `src/components/auth/ProtectedRoute.styles.ts` | 1 export — loading container (re-export) |
| `src/components/common/PageHeader.styles.ts` | 1 export — header container |

### Refactored Components

| Component | Inline `sx` removed | Pattern |
|-----------|---------------------|---------|
| `LoginPage.tsx` | 16+ | `import * as styles from './LoginPage.styles'` |
| `MainLayout.tsx` | 9+ | `import * as styles from './MainLayout.styles'` |
| `NotFoundPage.tsx` | 3 | `import * as styles from './NotFoundPage.styles'` |
| `ProtectedRoute.tsx` | 1 | `import * as styles from './ProtectedRoute.styles'` |
| `PageHeader.tsx` | 1 | `import * as styles from './PageHeader.styles'` |

---

## [PRE-ALPHA v0.5.1 | 2026-02-26 ~12:00] — Login Page + Authentication Flow

**What changed:** Added a full login page with dark-themed UI, authentication context with JWT token management, protected routes, and integration with the new backend `POST /api/v1/auth/login` endpoint.

### Changes Made

| File | Change | Why |
|---|---|---|
| `src/pages/LoginPage.tsx` (new) | Full-page login UI: dark background, decorative blobs panel, email/password form with validation, show/hide password toggle, error alerts | Matches reference design with WOMS branding and project color theme |
| `src/contexts/AuthContext.tsx` (new) | `AuthProvider` + `useAuth()` hook: token in localStorage, /me validation on mount, login/logout functions | Global auth state management; prevents flash of login on page reload |
| `src/components/auth/ProtectedRoute.tsx` (new) | Route guard: redirects to /login if not authenticated, shows spinner while loading | Protects all dashboard routes from unauthenticated access |
| `src/types/auth.ts` (new) | `LoginRequest`, `LoginResponse`, `AuthUser` TypeScript interfaces | Type safety for auth API interactions |
| `src/api/auth.ts` (new) | `login()` and `getMe()` API functions | Axios calls to backend auth endpoints |
| `src/api/client.ts` | Activated Bearer token injection; added 401 redirect handler | Token auto-injected; expired tokens trigger login redirect via `window.location.hash` |
| `src/main.tsx` | Wrapped App in `<AuthProvider>` inside HashRouter | Auth context needs router hooks; available to all components |
| `src/App.tsx` | `/login` route outside MainLayout; all others wrapped in `<ProtectedRoute>` | Login has no sidebar; dashboard requires auth |

### Design Decisions

- **Dark background (#1A1A2E)** for login page matches project text.primary color
- **Decorative blobs** use primary (#1565C0) and secondary (#FF8F00) from theme
- **HashRouter** — login redirect uses `window.location.hash` from Axios interceptor (outside React context)
- **localStorage** for token storage — simpler than cookies for SPA + Vite proxy setup
- **"Forgot Password" and "Request Account"** are placeholder buttons (not functional yet)

---

## [PRE-ALPHA v0.5.0 | 2026-02-25 ~15:00] — Frontend Project Scaffold

**What changed:** Created the `frontend/` directory with a complete React + Vite + TypeScript scaffold, including MUI theming, routing, sidebar layout, API client layer, type definitions, and placeholder pages.

### Changes Made

| File / Folder | Change | Why |
|---|---|---|
| `frontend/` | New Vite + React + TypeScript project scaffold | Monorepo structure prepared in v0.4.0; this is the frontend sibling to `backend/` |
| `frontend/vite.config.ts` | Proxy `/api` to `http://localhost:8000`, base `./` for Electron compat | Dev proxy avoids CORS issues; relative base enables Electron file:// loading |
| `frontend/index.html` | Montserrat font via Google Fonts CDN, updated title | User-specified font; descriptive page title |
| `frontend/src/theme/theme.ts` | MUI theme: Montserrat, custom palette, button/checkbox/alert overrides | Light-mode theme with scalable ThemeProvider for future dark mode |
| `frontend/src/main.tsx` | StrictMode + ThemeProvider + CssBaseline + HashRouter | HashRouter for Electron compat; ThemeProvider for consistent styling |
| `frontend/src/App.tsx` | Route definitions: /, /orders/import, /reference, /ml, 404 | Maps all backend features to frontend pages |
| `frontend/src/layouts/MainLayout.tsx` | react-pro-sidebar with collapsible nav, responsive AppBar | Sidebar navigation with Material Icons, mobile-responsive |
| `frontend/src/api/client.ts` | Axios instance with base URL, response/request interceptors | Centralised HTTP client with error handling |
| `frontend/src/api/orders.ts` | `importOrders()` — multipart/form-data matching backend contract | Matches `POST /api/v1/orders/import` form fields exactly |
| `frontend/src/api/reference.ts` | `loadPlatforms()`, `loadSellers()`, `loadItems()` | Matches backend reference router form field names |
| `frontend/src/api/mlSync.ts` | `syncStaging()`, `initSchema()` | Matches backend ML sync router JSON contract |
| `frontend/src/api/health.ts` | `checkHealth()` | Simple health check endpoint |
| `frontend/src/types/*.ts` | TypeScript interfaces for all API contracts + JSONB columns | Type safety for all backend interactions |
| `frontend/src/services/dataService.ts` | Multi-DB toggle service layer (woms_db / ml_woms_db) | Forward-looking abstraction for database context switching |
| `frontend/src/hooks/useD3.ts` | D3 + useRef integration hook | Prevents D3/React virtual DOM conflicts |
| `frontend/src/components/common/PageHeader.tsx` | Reusable page header component | Consistent heading style across all pages |
| `frontend/src/pages/*.tsx` | 5 placeholder pages (Dashboard, OrderImport, Reference, MLSync, 404) | Skeleton pages ready for feature implementation |

### Packages Installed

| Package | Version | Purpose |
|---|---|---|
| `@mui/material` | 6.x | UI component library |
| `@emotion/react` | 11.x | MUI styling engine |
| `@emotion/styled` | 11.x | MUI styled components |
| `@mui/icons-material` | 6.x | Material Design icons |
| `react-router-dom` | 7.x | Client-side routing (HashRouter) |
| `react-pro-sidebar` | 1.x | Collapsible sidebar navigation |
| `axios` | 1.x | HTTP client for API calls |
| `@faker-js/faker` | 9.x | Mock data generation |
| `d3` | 7.x | Data visualization |
| `@types/d3` | 7.x | TypeScript definitions for D3 |

---
