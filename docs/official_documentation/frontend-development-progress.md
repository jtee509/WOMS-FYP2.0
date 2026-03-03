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
