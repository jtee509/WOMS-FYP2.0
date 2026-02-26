# WOMS Version Update Log

Version scheme: `PRE-ALPHA vX.Y.Z`
- X — major milestone (0 = pre-alpha)
- Y — feature increment
- Z — fix / patch / minor addition

---

## [PRE-ALPHA v0.5.1.6 | 2026-02-26 ~23:30] — Convert layouts/ + components/ to Tailwind CSS, remove MUI theme

**What changed:** Migrated MainLayout, ProtectedRoute, and PageHeader from MUI components to native HTML + Tailwind CSS. Created custom `useIsMobile` hook to replace MUI `useMediaQuery`. Removed MUI `ThemeProvider` and `theme.ts` — all design tokens now live in `index.css` `@theme`. Uninstalled `lucide-react`. MUI icons are retained as the only MUI dependency in use.

### New Files

| File | Purpose |
|------|---------|
| `src/hooks/useIsMobile.ts` | Custom hook using `window.matchMedia` — replaces MUI `useMediaQuery(theme.breakpoints.down('md'))` |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/layouts/MainLayout.tsx` | Replaced MUI Box, AppBar, Toolbar, Typography, IconButton, useMediaQuery, useTheme with native HTML + Tailwind. react-pro-sidebar styles inlined as plain objects using CSS variables. MUI icons (Menu, Dashboard, UploadFile, Storage, Sync) retained. | Tailwind migration — ground rule #10 |
| `src/components/auth/ProtectedRoute.tsx` | Replaced MUI Box + CircularProgress with div + CSS spinner (`animate-spin`) | Tailwind migration |
| `src/components/common/PageHeader.tsx` | Replaced MUI Box + Typography with div/h1/p + Tailwind | Tailwind migration |
| `src/main.tsx` | Removed `ThemeProvider` wrapper and `theme` import. Only `BrowserRouter` + `AuthProvider` + `App` remain. | No MUI components depend on theme anymore |

### Files Deleted

| File | Why |
|------|-----|
| `src/layouts/MainLayout.styles.ts` | Replaced by Tailwind classes + inlined react-pro-sidebar styles |
| `src/components/auth/ProtectedRoute.styles.ts` | Replaced by Tailwind classes |
| `src/components/common/PageHeader.styles.ts` | Replaced by Tailwind classes |
| `src/styles/common.styles.ts` | Shared MUI styles no longer needed (Tailwind utilities used instead) |
| `src/theme/theme.ts` | All design tokens migrated to `index.css` `@theme` block |

### Packages Changed

| Package | Action | Why |
|---------|--------|-----|
| `lucide-react` | Uninstalled | User chose to keep MUI icons instead |

### Remaining MUI Dependencies

`@mui/icons-material`, `@mui/material`, `@emotion/react`, `@emotion/styled` are still installed — `@mui/icons-material` is used in MainLayout.tsx (5 icons) and LoginPage.tsx (3 icons). `@mui/material` + Emotion are peer dependencies of `@mui/icons-material`.

### Build Impact

| Metric | Before (v0.5.1.5) | After | Change |
|--------|--------|-------|--------|
| JS bundle | 466.01 kB | 417.26 kB | **-48.75 kB** (removed MUI layout components + ThemeProvider) |
| CSS output | 14.71 kB | 15.61 kB | +0.90 kB (Tailwind utilities for layouts) |
| Modules | 397 | 379 | -18 modules |

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful (417.26 kB JS, 15.61 kB CSS)
- `npm run dev` — server starts cleanly, no console errors

---

## [PRE-ALPHA v0.5.1.5 | 2026-02-26 ~23:00] — Convert pages/ to Tailwind CSS

**What changed:** Migrated all 6 page components from MUI `sx` / MUI components to native HTML + Tailwind CSS utility classes. Removed MUI component imports (Box, Card, Typography, Button, Alert, Grid) from all pages. Deleted deprecated `.styles.ts` files. Extended `index.css` with login-specific CSS (blob decorations, form input styles).

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/pages/LoginPage.tsx` | Replaced all MUI components (Box, Card, TextField, Button, Typography, Alert, IconButton, InputAdornment, CircularProgress) with native HTML + Tailwind classes. Only MUI icons retained. | Tailwind migration — ground rule #10 |
| `src/pages/NotFoundPage.tsx` | Replaced Box, Typography, Button with div/h1/p/button + Tailwind | Tailwind migration |
| `src/pages/DashboardPage.tsx` | Replaced Box, Card, CardContent, Grid, Typography with div/p + Tailwind grid | Tailwind migration |
| `src/pages/OrderImportPage.tsx` | Replaced Box, Alert with div + Tailwind info alert styling | Tailwind migration |
| `src/pages/ReferencePage.tsx` | Replaced Box, Alert with div + Tailwind info alert styling | Tailwind migration |
| `src/pages/MLSyncPage.tsx` | Replaced Box, Alert with div + Tailwind info alert styling | Tailwind migration |
| `src/index.css` | Added login page tokens (`--color-login-bg`, `--color-login-panel`, `--shadow-login`), blob CSS classes (`.login-blob--*`), form input CSS (`.form-input`, `.form-label`, `.form-helper`) | Custom CSS for complex login UI that doesn't fit pure utility classes |

### Files Deleted

| File | Why |
|------|-----|
| `src/pages/LoginPage.styles.ts` | Replaced by Tailwind classes + index.css custom CSS |
| `src/pages/NotFoundPage.styles.ts` | Replaced by Tailwind classes |

### Build Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| JS bundle | 561.80 kB | 466.01 kB | **-95.79 kB** (removed MUI component imports) |
| CSS output | 6.51 kB | 14.71 kB | +8.20 kB (Tailwind utilities + custom CSS) |
| Chunk warning | Yes (>500 kB) | **No** | Under threshold |

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful, no chunk size warnings

---

## [PRE-ALPHA v0.5.1.4 | 2026-02-26 ~22:00] — Add Tailwind CSS v4 as base styling framework

**What changed:** Installed Tailwind CSS v4 with the Vite plugin, created a base CSS template (`src/index.css`) with project design tokens mapped to Tailwind's `@theme`, and added ground rule #10 establishing Tailwind as the styling standard going forward.

### New Files

| File | Purpose |
|------|---------|
| `frontend/src/index.css` | Tailwind v4 base template — imports Tailwind, defines `@theme` with all project colors (primary, secondary, semantic), typography (Montserrat), border radii, and shadows matching `theme.ts` |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `frontend/vite.config.ts` | Added `@tailwindcss/vite` plugin | Tailwind v4 uses a Vite plugin (no PostCSS config needed) |
| `frontend/src/main.tsx` | Added `import './index.css'`; removed `CssBaseline` import | Tailwind's preflight replaces MUI's CssBaseline for CSS resets |
| `frontend/package.json` | Added `tailwindcss`, `@tailwindcss/vite` | Tailwind CSS v4 dependencies |

### New Ground Rule

| # | Rule |
|---|------|
| 10 | **Tailwind CSS**: Use Tailwind CSS v4 as base styling framework — all new styling uses Tailwind utility classes; MUI `sx`/`.styles.ts` are deprecated (migration pending) |

### Design Decisions

- **Tailwind CSS v4** (not v3) — CSS-first config via `@theme`, no `tailwind.config.js` needed, native Vite plugin
- **Removed CssBaseline** — Tailwind's preflight handles browser CSS reset
- **Kept ThemeProvider + theme.ts** temporarily — existing MUI components still depend on them; will be removed when components are fully migrated to Tailwind
- **`@theme` tokens match `theme.ts`** — `bg-primary` = `#1565C0`, `text-secondary` = `#555770`, `font-sans` = Montserrat, etc.

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful (6.51 kB CSS output, 561.80 kB JS — slightly smaller than before CssBaseline removal)

---

## [PRE-ALPHA v0.5.1.3 | 2026-02-26 ~21:00] — Extract inline styles to separate files

**What changed:** Extracted all inline MUI `sx` styles from React components into co-located `*.styles.ts` files using typed `SxProps<Theme>` exports. This enforces frontend ground rule #8 (all CSS in separate files).

### New Files Created

| File | Exports | Why |
|------|---------|-----|
| `src/styles/common.styles.ts` | `centeredFullPage`, `centeredContentArea` | Shared layout primitives reused by multiple components |
| `src/pages/LoginPage.styles.ts` | 18 exports (static + factory functions + `blob()` helper) | Largest extraction — decorative blobs, form panels, branding, buttons |
| `src/layouts/MainLayout.styles.ts` | 5 static + 5 factory/function exports | Sidebar, AppBar, page content; includes non-sx react-pro-sidebar props |
| `src/pages/NotFoundPage.styles.ts` | `pageRoot` (re-export), `errorCode`, `errorMessage` | 404 page layout and typography |
| `src/components/auth/ProtectedRoute.styles.ts` | `loadingContainer` (re-export) | Loading spinner container |
| `src/components/common/PageHeader.styles.ts` | `headerContainer` | Page header margin |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/pages/LoginPage.tsx` | All 16+ inline `sx` → `import * as styles` | Ground rule #8 compliance |
| `src/layouts/MainLayout.tsx` | All 9+ inline `sx` + react-pro-sidebar props → styles imports | Ground rule #8 compliance |
| `src/pages/NotFoundPage.tsx` | 3 inline `sx` → styles imports | Ground rule #8 compliance |
| `src/components/auth/ProtectedRoute.tsx` | 1 inline `sx` → styles import | Ground rule #8 compliance |
| `src/components/common/PageHeader.tsx` | 1 inline `sx` → styles import | Ground rule #8 compliance |

### Design Decisions

- **SxProps<Theme> style files** (not CSS Modules) — project uses MUI responsive breakpoints, spacing multipliers, and palette references extensively; CSS Modules would require rewriting all of this as raw CSS
- **Factory functions** for dynamic styles (e.g., `mainContent(isMobile, sidebarWidth)`, `emailHelperText(isValid)`) — runtime values require function calls
- **`import type`** for Theme/SxProps — `verbatimModuleSyntax: true` in tsconfig requires it
- **Re-exports from common** — `centeredFullPage` and `centeredContentArea` are shared patterns, imported by ProtectedRoute and NotFoundPage respectively

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful production build (563 kB bundle, unchanged from before extraction)

---

## [PRE-ALPHA v0.5.1.2 | 2026-02-26 ~20:00] — Frontend ground rules + BrowserRouter

**What changed:** Added 3 new frontend ground rules (component architecture, separate CSS files, BrowserRouter) and switched routing from HashRouter to BrowserRouter.

### New Ground Rules Added

| # | Rule | Why |
|---|------|-----|
| 7 | Dedicated component section (`src/components/`) for reusable functions (e.g., printing) | Establishes convention for shared UI components |
| 8 | All CSS in separate files — no inline or in-component styles | Consistent styling approach, easier maintenance |
| 9 | Use BrowserRouter for routing | Standard SPA routing with clean URLs (no `#/` prefix) |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `frontend/src/main.tsx` | `HashRouter` → `BrowserRouter` | Ground rule #9: clean URL paths |
| `frontend/src/api/client.ts` | 401 redirect: `window.location.hash = '#/login'` → `window.location.href = '/login'` | BrowserRouter uses pathname, not hash |
| `docs/official_documentation/frontend-development-progress.md` | Added "Frontend Ground Rules" section with all 9 rules | Canonical location for frontend conventions |

---

## [PRE-ALPHA v0.5.1.1 | 2026-02-26 ~19:30] — Auth endpoint bugfixes + DB provisioning

**What changed:** Fixed two bugs that prevented the login endpoint from working during end-to-end testing. Also provisioned `woms_user` in PostgreSQL and granted table-level permissions.

### Bugs Fixed

| # | Error | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | `permission denied for table users` | `woms_user` was created as DB owner but had no table-level `GRANT` on tables created by `postgres` | Ran `GRANT ALL ON ALL TABLES/SEQUENCES IN SCHEMA public TO woms_user` + `ALTER DEFAULT PRIVILEGES` |
| 2 | `can't subtract offset-naive and offset-aware datetimes` | `last_login` column is `TIMESTAMP WITHOUT TIME ZONE`; `datetime.now(timezone.utc)` returns tz-aware datetime; asyncpg rejects the mismatch | Added `.replace(tzinfo=None)` in `routers/auth.py` line 49 |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `backend/app/routers/auth.py` | `datetime.now(timezone.utc).replace(tzinfo=None)` | Strip timezone for `TIMESTAMP WITHOUT TIME ZONE` column |
| `fix_db_password.py` (new, temp) | Helper script to sync `.env` password with PostgreSQL | One-time DB provisioning tool |

### Test Results

| Test | Result |
|------|--------|
| `GET /health` | `{"status":"healthy","database":"connected"}` |
| `POST /api/v1/auth/login` (admin@admin.com / Admin123) | 200 — JWT token + user info returned |
| `GET /api/v1/auth/me` (Bearer token) | 200 — user profile returned |
| Vite proxy `/api` -> backend | Working (login via port 5173 succeeds) |
| Frontend dev server (localhost:5173) | Running, serves login page |

---

## [PRE-ALPHA v0.5.2 | 2026-02-26 ~18:00] — Full CRUD API for all domains

**What changed:** Built the complete REST API layer covering all 6 domains with 50+ endpoints. Includes Pydantic schemas (Create/Read/Update per entity), paginated list endpoints with search/filter, JWT-protected write operations, and a standard response envelope (`PaginatedResponse`, `ErrorResponse`). Also simplified Alembic migration naming by dropping the revision hash and seconds from filenames.

### New Files Created

| File | Purpose |
|------|---------|
| `backend/app/schemas/common.py` | `PaginatedResponse[T]`, `ErrorResponse`, `MessageResponse` |
| `backend/app/schemas/items.py` | ItemCreate, ItemRead, ItemUpdate + lookup reads |
| `backend/app/schemas/orders.py` | OrderCreate, OrderRead, OrderUpdate, OrderDetailCreate/Read/Update, OrderListItem |
| `backend/app/schemas/platform.py` | PlatformCreate/Read/Update, SellerCreate/Read/Update |
| `backend/app/schemas/warehouse.py` | WarehouseCreate/Read/Update, InventoryLevelRead, InventoryAlertRead |
| `backend/app/schemas/delivery.py` | DeliveryTripCreate/Read/Update, DriverCreate/Read/Update |
| `backend/app/schemas/users.py` | UserCreate/Read/Update, RoleRead |
| `backend/app/routers/items.py` | Items CRUD + lookup endpoints (statuses, types, categories, brands, UOMs) |
| `backend/app/routers/orders.py` | Order CRUD + order detail updates |
| `backend/app/routers/platforms.py` | Platform + Seller CRUD |
| `backend/app/routers/warehouse.py` | Warehouse CRUD, locations, inventory levels, alerts |
| `backend/app/routers/delivery.py` | Delivery trips + drivers CRUD |
| `backend/app/routers/users.py` | User CRUD + roles listing |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `backend/app/main.py` | Mounted 6 new routers, removed future-routers comment block | Activate all CRUD endpoints |
| `backend/app/schemas/__init__.py` | Re-export all new schema classes | Centralized schema imports |
| `backend/alembic.ini` | Simplified `file_template` (dropped `%%(second)` and `%%(rev)s`) | Cleaner migration filenames |

### Endpoint Summary (50+ routes)

| Domain | Endpoints | Auth Required |
|--------|-----------|---------------|
| Auth | POST /login, GET /me | Login: no, Me: yes |
| Orders | GET list, GET/:id, POST, PATCH/:id, PATCH/:id/details/:id | Write: yes |
| Order Import | POST /import | No |
| Items | GET list, GET/:id, POST, PATCH/:id, DELETE/:id + 5 lookup GETs | Write: yes |
| Platforms | GET list, GET/:id, POST, PATCH/:id | Write: yes |
| Sellers | GET list, GET/:id, POST, PATCH/:id | Write: yes |
| Warehouse | GET list, GET/:id, POST, PATCH/:id, locations, inventory, alerts | Write: yes |
| Delivery | Drivers: GET/POST/PATCH, Trips: GET/POST/PATCH | Write: yes |
| Users | GET list, GET/:id, POST, PATCH/:id, GET /roles | All: yes |
| Reference | POST load-platforms/sellers/items | No |
| ML Staging | POST sync, POST init-schema | No |

---

## [PRE-ALPHA v0.5.1 | 2026-02-26 ~12:00] — Login Page + JWT Authentication

**What changed:** Added full authentication flow: backend JWT login endpoint with bcrypt password hashing, frontend login page with dark-themed UI matching project design system, auth context with token persistence, and protected routes. Seeded a test admin user (`admin@admin.com` / `Admin123`).

### Backend Changes

| File | Change | Why |
|---|---|---|
| `backend/app/schemas/auth.py` (new) | `LoginRequest`, `TokenResponse`, `TokenPayload` Pydantic schemas | Type-safe request/response validation for auth endpoints |
| `backend/app/services/auth.py` (new) | `hash_password()`, `verify_password()`, `create_access_token()`, `decode_access_token()`, `authenticate_user()`, `get_current_user()` | Auth business logic using passlib[bcrypt] + python-jose; separated from router |
| `backend/app/dependencies/__init__.py` (new) | Package init for FastAPI dependencies | Organise dependency injection functions |
| `backend/app/dependencies/auth.py` (new) | `OAuth2PasswordBearer` scheme + `require_current_user()` dependency | JWT extraction from Bearer header; reusable for all protected endpoints |
| `backend/app/routers/auth.py` (new) | `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | Login endpoint returns JWT; /me validates token and returns user profile |
| `backend/app/main.py` | Registered auth router at `/api/v1/auth` | Expose auth endpoints via FastAPI |
| `backend/app/models/seed.py` | Added test admin user insert (`ON CONFLICT DO NOTHING`) | Test user for development; uses subquery for role_id resolution |
| `backend/app/schemas/__init__.py` | Added auth schema imports | Package-level export |

### Frontend Changes

| File | Change | Why |
|---|---|---|
| `frontend/src/types/auth.ts` (new) | `LoginRequest`, `LoginResponse`, `AuthUser` interfaces | TypeScript types matching backend auth contract |
| `frontend/src/api/auth.ts` (new) | `login()`, `getMe()` API functions | Frontend-to-backend auth API calls |
| `frontend/src/contexts/AuthContext.tsx` (new) | `AuthProvider` + `useAuth()` hook | Global auth state: token in localStorage, /me validation on mount, login/logout |
| `frontend/src/components/auth/ProtectedRoute.tsx` (new) | Route guard component | Redirects to /login if unauthenticated; shows spinner while validating |
| `frontend/src/pages/LoginPage.tsx` (new) | Full login page UI | Dark background, decorative blobs panel, email/password form, error handling |
| `frontend/src/api/client.ts` | Activated Bearer token injection; added 401 redirect handler | Token auto-injected on every request; expired tokens trigger login redirect |
| `frontend/src/main.tsx` | Wrapped App in `<AuthProvider>` | Auth context available to all components |
| `frontend/src/App.tsx` | `/login` route outside MainLayout; all others wrapped in `<ProtectedRoute>` | Login page has no sidebar; dashboard requires authentication |

### New Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Public | Authenticate with email + password, receive JWT |
| GET | `/api/v1/auth/me` | Bearer JWT | Get current user profile (token validation) |

### Test User

| Field | Value |
|---|---|
| Email | `admin@admin.com` |
| Password | `Admin123` |
| Username | `admin` |
| Role | Admin |

---

## [PRE-ALPHA v0.4.5 | 2026-02-25 ~16:00] — API Development Proposal revised (10 review findings)

**What changed:** The API Development Proposal (`docs/planning_phase/Backend/06_api_development_proposal_106ea193.plan.md`) was reviewed against the actual codebase and rewritten with 10 improvements.

### Changes Made

| # | Finding | Change |
|---|---------|--------|
| 1 | Nested `/catalog/`, `/marketplace/` paths | Replaced with flat paths matching `main.py:207-211` stubs |
| 2 | Missing authentication | Added new Section 3 covering `app/auth/` package, JWT, login/register/refresh endpoints |
| 3 | Separate `seller.py` for one model | Merged Seller into `platform.py` with other marketplace models |
| 4 | Deeply nested `schemas/` directory | Flattened to mirror model files |
| 5 | `PlatformRawImport` incorrectly marked as "legacy/deprecate" | Corrected: both tables serve distinct roles; `Order.raw_import_id` FK depends on it |
| 6 | Migration naming lacked implementation detail | Added actual `alembic.ini` `file_template` change |
| 7 | `warehouse.py` not discussed | Acknowledged as future split candidate (483 lines, 11 models) |
| 8 | Circular import risk in model split | Added `TYPE_CHECKING` + string FK refs resolution pattern |
| 9 | Existing `ImportResult`/`SyncResult` dataclasses not mentioned | Documented with conversion plan to Pydantic |
| 10 | No error response standardization | Added `ErrorResponse`/`PaginatedResponse` in `common.py` |

Phases reordered from 4 to 6: docs → schemas → **auth** → order CRUD → supporting CRUDs → model split.

---

## [PRE-ALPHA v0.5.0 | 2026-02-25 ~15:00] — Frontend Project Scaffold (React + Vite + TypeScript + MUI)

**What changed:** Created the `frontend/` directory with a complete React + Vite + TypeScript project scaffold. Includes Material UI theming (Montserrat font, custom palette, button/checkbox/alert overrides), react-pro-sidebar navigation, HashRouter for Electron compatibility, Axios API client layer matching all backend endpoints, TypeScript interfaces for JSONB columns, D3 integration hook, and placeholder pages for all features. Also created three new documentation files for frontend development tracking.

### Changes Made

| File / Folder | Change | Why |
|---|---|---|
| `frontend/` (new) | Complete Vite + React + TS scaffold with 25+ source files | Monorepo frontend sibling to `backend/`; prepared since v0.4.0 |
| `frontend/vite.config.ts` | Dev proxy `/api` → `localhost:8000`; base `./` | Proxy avoids CORS issues; relative base enables Electron file:// |
| `frontend/index.html` | Montserrat font CDN link, updated title | User-specified font; descriptive page title |
| `frontend/src/theme/theme.ts` | MUI theme: Montserrat, primary (#1565C0), secondary (#FF8F00), component overrides | Light-mode theme with scalable ThemeProvider for future dark mode |
| `frontend/src/main.tsx` | StrictMode + ThemeProvider + CssBaseline + HashRouter | HashRouter for Electron compat; theme consistency |
| `frontend/src/App.tsx` | 5 routes: /, /orders/import, /reference, /ml, 404 | Maps all backend features to frontend pages |
| `frontend/src/layouts/MainLayout.tsx` | react-pro-sidebar, responsive AppBar, Outlet | Collapsible sidebar with Material Icons, mobile breakpoints |
| `frontend/src/api/*.ts` | Axios client + 4 API modules matching backend contracts | Type-safe API calls with centralised error handling |
| `frontend/src/types/*.ts` | TypeScript interfaces for orders, reference, mlSync, JSONB | Type safety for all backend interactions |
| `frontend/src/services/dataService.ts` | Multi-DB toggle service (woms_db / ml_woms_db) | Forward-looking abstraction for DB context switching |
| `frontend/src/hooks/useD3.ts` | D3 + useRef integration hook | Prevents D3/React virtual DOM conflicts |
| `frontend/src/components/common/PageHeader.tsx` | Reusable page header | Consistent heading style across pages |
| `frontend/src/pages/*.tsx` | 5 placeholder pages | Skeleton pages ready for feature implementation |
| `docs/official_documentation/frontend-development-progress.md` (new) | Frontend progress tracking document | User ground rule #1: document all updates |
| `docs/official_documentation/web-api.md` (new) | Full API documentation for all 9 endpoints | User ground rule #2: document all APIs |
| `docs/official_documentation/frontend-error.md` (new) | Error tracking log template | User ground rule #6: document all errors |
| `README.md` | Added Frontend section, updated project layout tree | Reflect new frontend directory |

### Tech Stack

| Layer | Choice | Version |
|---|---|---|
| Framework | React + TypeScript (Strict) | 19.x |
| Build tool | Vite | 6.x |
| UI Library | @mui/material + @emotion | 6.x |
| Routing | react-router-dom (HashRouter) | 7.x |
| Sidebar | react-pro-sidebar | 1.x |
| HTTP client | axios | 1.x |
| Charts | d3 (useRef pattern) | 7.x |
| Mock data | @faker-js/faker | 9.x |

---

## [PRE-ALPHA v0.4.4 | 2026-02-23 ~23:30] — Move docs/ to project root, commit planning_phase

**What changed:** The `docs/` folder was moved from `backend/docs/` to the project root so it is visible to anyone browsing the repository without navigating into `backend/`. The `planning_phase/` subfolder was removed from `.gitignore` and all 5 design-notes files are now committed alongside the official documentation.

### Changes Made

| File | Change | Why |
|---|---|---|
| `backend/docs/` → `docs/` | Entire docs folder moved to project root | Better discoverability — docs are now visible at repo root without entering backend/ |
| `.gitignore` | Removed `backend/docs/planning_phase/` and `docs/planning_phase/` exclusion lines | Planning docs should be versioned alongside official docs for full project history |
| `docs/planning_phase/` (5 files) | Added to git and committed for the first time | Design notes are part of the project record and useful for contributors |
| `README.md` | Updated 2 doc links from `backend/docs/...` → `docs/...`; updated project layout tree | Links were pointing to old path after folder move |

---

## [PRE-ALPHA v0.4.3 | 2026-02-23 ~23:00] — README overhaul + remove planning_phase from git

**What changed:** README.md was completely rewritten to reflect the current project state (backend/ layout, actual endpoints, setup_env.py workflow). The `planning_phase/` docs folder was removed from git tracking (files remain on disk but are gitignored).

### Changes Made

| File | Change | Why |
|---|---|---|
| `README.md` | Rewritten: accurate project layout, actual API endpoints, setup_env.py instructions, correct env vars table, links to official docs | Old README was from v0.1.0; referenced non-existent files and commands |
| `.gitignore` | Added `backend/docs/planning_phase/` and `docs/planning_phase/` patterns | Internal design notes should not be published to GitHub |
| `backend/docs/planning_phase/` (5 files) | Removed from git index (`git rm --cached`) — files stay on disk | Planning docs are internal; not relevant to users cloning the repo |

---

## [PRE-ALPHA v0.4.2 | 2026-02-23 ~22:30] — setup_env.py: Auto-generate .env + provision PostgreSQL

**What changed:** Added `setup_env.py` at the project root — a one-command tool that generates all secrets and DB credentials, creates the PostgreSQL user and both databases, then writes a complete `.env` with no placeholder values.

### Changes Made

| File | Change | Why |
|---|---|---|
| `setup_env.py` (new) | Auto-generates `SECRET_KEY` (256-bit hex), DB password (`token_urlsafe`), creates `woms_user` + `woms_db` + `ml_woms_db` in PostgreSQL, writes complete `.env` | Eliminates manual credential setup; every install gets unique secure keys |

### How it works
- `SECRET_KEY` — `secrets.token_hex(32)` → 64-char hex, 256 bits of entropy
- `DATABASE_PASSWORD` — `secrets.token_urlsafe(32)` → URL-safe (A-Z a-z 0-9 `-` `_`), safe in connection URLs without percent-encoding
- Connects to PostgreSQL as admin user (`postgres` by default) using `psycopg3`
- Uses parameterised queries for password to prevent injection
- Idempotent: if user/DB already exists, updates password/owner instead of failing
- Admin credentials are asked interactively (`getpass`) — **never stored**
- Falls back gracefully: prints SQL commands if `psycopg` unavailable or connection fails

### Usage
```bash
python setup_env.py                  # Interactive: generate + provision DB
python setup_env.py --generate-only  # Just write .env (no DB creation)
python setup_env.py --force          # Overwrite existing .env without prompt
```

---

## [PRE-ALPHA v0.4.1 | 2026-02-23 ~22:00] — requirements.txt Sync to Actual Installed Versions

**What changed:** `requirements.txt` was outdated — it listed package versions from the initial project setup, two missing packages (`pandas`, `python-dateutil`), and one wrong package name (`psycopg-binary` vs `psycopg[binary,pool]`). The file now reflects exact versions from the active Python 3.13 environment.

**Root cause discovered:** The project runs on Python 3.13 (system install at `AppData/Local/Programs/Python/Python313/`). The `venv/` directory is not a standard virtual environment (no `pyvenv.cfg`) — it only holds compiled `.pyd` extension stubs. All packages are installed in the system Python 3.13.

### Changes Made

| File | Change | Why |
|---|---|---|
| `backend/requirements.txt` | Updated all package versions to match Python 3.13 actual installs | Old versions were from initial setup; project has been running on newer versions |
| `backend/requirements.txt` | Added `pandas==3.0.1` | Was missing — used throughout order import pipeline for CSV/Excel parsing |
| `backend/requirements.txt` | Added `python-dateutil==2.9.0.post0` | Was missing — used in `cleaner.py` `parse_flexible_date()` for date normalization |
| Python 3.13 | Installed `pandas==3.0.1`, `python-dateutil==2.9.0.post0` | Both were absent from the active Python environment |

### Key Version Changes
| Package | Old | New |
|---|---|---|
| `fastapi` | 0.109.2 | 0.111.0 |
| `uvicorn` | 0.27.1 | 0.30.1 |
| `sqlmodel` | 0.0.14 | 0.0.31 |
| `sqlalchemy` | 2.0.25 | 2.0.34 |
| `pydantic-settings` | 2.1.0 | 2.11.0 |
| `asyncpg` | 0.29.0 | 0.31.0 |
| `bcrypt` | 4.1.2 | 5.0.0 |
| `pandas` | missing | 3.0.1 |
| `python-dateutil` | missing | 2.9.0.post0 |

---

## [PRE-ALPHA v0.4.0 | 2026-02-23 ~21:30] — Project Restructuring: `backend/` layout + `venv` → `.venv`

**What changed:** All application code was relocated from the project root into a `backend/` subfolder, adopting a monorepo-style layout that makes room for a future `frontend/` sibling. The deprecated SQL `migrations/` folder was co-located inside `app/`. The virtual environment was renamed from `venv/` to `.venv/` (convention standard, already in `.gitignore`).

### Changes Made

| File / Folder | Change | Why |
|---|---|---|
| `alembic/` | Moved to `backend/alembic/` | All backend code lives in `backend/` |
| `alembic.ini` | Moved to `backend/alembic.ini` | `script_location = alembic` stays relative — run alembic from `backend/` |
| `app/` | Moved to `backend/app/` | Monorepo layout for future frontend sibling |
| `docs/` | Moved to `backend/docs/` | Documentation co-located with application |
| `migrations/` (root) | Moved to `backend/app/migrations/` | Deprecated SQL reference files co-located with app |
| `requirements.txt` | Moved to `backend/requirements.txt` | Dependency manifest with the application code |
| `tests/` | Moved to `backend/tests/` | Test data/fixtures with the application code |
| `venv/` | Renamed to `.venv/` at project root | Convention standard; stays at root (not inside backend/) |
| `backend/app/config.py` | `env_file=".env"` → absolute path via `Path(__file__).parent.parent.parent / ".env"` | `.env` stays at project root; absolute path ensures it loads regardless of CWD |
| `backend/app/database.py` | `PROJECT_ROOT` path updated (`.parent.parent` → `.parent.parent.parent`); comment updated | Reflects new depth of file in `backend/app/` |
| `.claude/settings.local.json` | All `venv/` references → `.venv/` | Match new virtual environment folder name |

### Files NOT Moved (remain at project root)
`.env`, `.env.template`, `.gitignore`, `README.md`, `setup.py`

### How to Run After Restructuring
```bash
# Start server (from project root):
cd backend
../.venv/Scripts/uvicorn app.main:app --reload

# Run Alembic (from backend/):
cd backend
../.venv/Scripts/alembic upgrade head
```

### Verification
- Server started from `backend/` with `DEBUG=false venv/Scripts/uvicorn app.main:app`
- `GET /api/v1/health` → `{"status": "healthy"}` ✓
- Swagger UI at `http://localhost:8000/docs` ✓
- `.env` loaded correctly (DB settings resolved from project root) ✓

---

## [PRE-ALPHA v0.3.5 | 2026-02-23 ~19:00] — Documentation Restructuring

**What changed:** Project documentation files were renamed and consolidated into a single canonical directory. New ground rule established for where documentation lives.

### Changes Made

| File | Change | Why |
|---|---|---|
| `docs/database.md` | Renamed/moved to `docs/official_documentation/database_structure.md` | Descriptive filename better communicates purpose; consolidated into the official docs folder |
| `version_update.md` (project root) | Moved to `docs/official_documentation/version_update.md` (this file) | Single canonical location for all official project documentation |

### New Ground Rule
- **Canonical documentation directory:** `docs/official_documentation/`
- **Database schema docs:** always update `docs/official_documentation/database_structure.md` (previously `database.md`)
- **Version update log:** always update `docs/official_documentation/version_update.md` (this file)

---

## [PRE-ALPHA v0.3.4 | 2026-02-23 ~18:00] — Item Master Upload Correction + SKU Mapping Plan

**What changed:** The `load_item_master` endpoint was uploading platform SKU codes with a hard-coded `seller_id`, which is architecturally wrong. Different sellers across multiple platforms have different platform-specific SKU names for the same product. The mapping from platform SKU → Internal SKU is a manual per-seller decision.

### Changes Made

| File | Change | Why |
|---|---|---|
| `app/services/reference_loader/loader.py` | Removed all `platform_sku` and `listing_component` creation from `load_item_master()`. Now only inserts/updates `items` rows. Removed `seller_id` parameter. | Platform SKU codes in the Item Master file are generic product codes, not seller-specific. Forcing a single seller_id creates false associations. |
| `app/routers/reference.py` | Removed `seller_id: int = Form(...)` from `upload_items` endpoint. Removed `Form` import. | `load_item_master` no longer needs seller context. |

### Data Reset Applied
- Cleared `items`, `platform_sku`, `listing_component` in both `woms_db` and `woms_test_db`
- Re-uploaded items correctly (items table only, 0 platform_sku records)
- Order staging data (`order_import_staging`, `order_import_raw`) was preserved — it serves as the reference for manual SKU mapping

### Final State
```
woms_db:       items=499  platform_sku=0  staging=517 rows
woms_test_db:  items=499  platform_sku=0  staging=517 rows
```

### Platform SKU Mapping — Plan for Future Orders

The `platform_sku` table will be populated manually by the user, per seller, by referencing:
1. **Order staging data** — `platform_sku` column contains the platform's SKU string for each order line
2. **Item Master** — `Internal CODE` is the canonical ID to map to

Mapping workflow (future):
1. User reviews `order_import_staging` rows (e.g. Shopee platform_sku = `"(10 inch) 5'"`)
2. User identifies the matching `items.master_sku` (e.g. `ADM10001`)
3. User creates a `platform_sku` record: `{platform_id, seller_id, platform_sku="(10 inch) 5'", → item}`
4. A `listing_component` record links `platform_sku.listing_id → items.item_id`
5. Once mapped, future imports can auto-resolve platform SKU → internal item

A future admin endpoint `POST /api/v1/reference/map-sku` will be built to accept these mappings.

---

## [PRE-ALPHA v0.3.3 | 2026-02-23 ~17:30] — woms_test_db Clean-Install Test + 2 Bug Fixes

**What changed:** Full clean-install test on a fresh `woms_test_db` PostgreSQL database (separate from `woms_db`). Uncovered and fixed 2 new bugs.

### Bugs Fixed

| File | Bug | Fix |
|---|---|---|
| `app/database.py` → `init_db()` | `create_all()` fails on a fresh database with `InvalidSchemaNameError: schema "order_import" does not exist` — the `order_import` schema must be created before any tables that use it | Added `CREATE SCHEMA IF NOT EXISTS order_import` inside `init_db()` before `create_all()` (mirrors the fix already present in `init_ml_db()`) |
| `app/services/order_import/cleaner.py` → `_DATE_FORMATS` | Shopee dates (`23/12/2025 20:52`) and Lazada dates (`1/1/2025 15:35`) use `DD/MM/YYYY HH:MM` format (no seconds). The format list only had `%d/%m/%Y %H:%M:%S` (with seconds) and `%d/%m/%Y` (date only), so all Shopee/Lazada `order_date` fields were stored as `NULL` | Added `"%d/%m/%Y %H:%M"` to `_DATE_FORMATS` between the with-seconds and date-only variants |

### Why each fix was needed
- **init_db schema**: SQLModel `create_all()` iterates tables alphabetically; `order_import.*` tables come before the schema exists. The `init_ml_db()` function already had this fix — it was just missing from the production `init_db()`.
- **Date format HH:MM vs HH:MM:SS**: Shopee and Lazada export timestamps without seconds. Python's `strptime` does not allow partial pattern matches — `%H:%M:%S` won't match `20:52` because seconds are absent.

### Test Results on woms_test_db (2026-02-23)

```
DB: woms_test_db (fresh PostgreSQL database, clean install)
Server: port 8001, DATABASE_URL override via env var

POST /api/v1/reference/load-platforms  -> 4 platforms loaded
POST /api/v1/reference/load-sellers    -> 8 sellers loaded
POST /api/v1/reference/load-items      -> 499 items, 1497 platform SKUs

POST /api/v1/orders/import [shopee]    -> 116/116 success
POST /api/v1/orders/import [lazada]    -> 120/120 success
POST /api/v1/orders/import [tiktok]    -> 281/281 success

Staging coverage after fix:
  Platform    Rows  w/ Date  w/ Phone  w/ Tracking
  lazada       120      120       120          120   (100% all fields)
  shopee       116      115       115          115   (1 row has empty date/phone in source)
  tiktok       281      278       281          279   (3 rows missing date, 2 missing tracking in source)
  TOTAL        517
```

---

## [PRE-ALPHA v0.3.2 | 2026-02-23 ~17:00] — Alembic Stamp to Head

**What changed:** After the v0.3.1 end-to-end test, the Alembic version tracker in `woms_db` was at `c4d5e6f7a8b9` even though two newer migrations existed in `alembic/versions/`:
- `d5e6f7a8b9c0` — adds `phone_number` and `platform_order_status` to `order_import_staging`
- `e6f7a8b9c0d1` — adds all 47 performance indexes

Both migrations' effects were already present in the DB (columns added via `ALTER TABLE` in v0.3.1; indexes applied by SQLModel `__table_args__` via `create_all()`). Re-running the migrations would have failed with "column already exists" / "index already exists" errors.

**Fix:** Ran `alembic stamp e6f7a8b9c0d1` to advance the version pointer to head without re-executing the DDL. Confirmed with `alembic current` → `e6f7a8b9c0d1 (head)`.

**Why this approach:** `alembic stamp` is the correct tool when the DB state already matches the migration's DDL but the version table is behind — it records the migration as applied without running it.

---

## [PRE-ALPHA v0.3.1 | 2026-02-23 16:30] — End-to-End Test + Bug Fixes

**What changed:** First full end-to-end test run against the test database. Found and fixed 5 bugs uncovered during testing.

### Bugs Fixed

| File | Bug | Fix |
|---|---|---|
| `app/database.py`, `app/main.py`, `app/models/triggers.py`, `app/models/views.py`, `app/models/seed.py`, `app/ml_database.py` | Unicode characters (✓ ⚠) in print() caused `UnicodeEncodeError` on Windows cp1252 console | Replaced all emoji/special chars with ASCII `[OK]` / `[WARN]` |
| `app/services/order_import/parser.py` | CSV files encoded in cp1252 (not UTF-8), causing `UnicodeDecodeError` on Shopee/Lazada/TikTok CSVs | `_read_dataframe()` now tries encodings in order: `utf-8-sig` → `cp1252` → `latin-1` |
| `app/services/order_import/importer.py` | Raw and staging inserts used `:param::jsonb` SQLAlchemy named-param + Postgres cast syntax; asyncpg rejects this combo | Changed to `CAST(:param AS jsonb)` standard SQL syntax |
| `app/models/order_import.py` / DB migration | `phone_number` and `platform_order_status` columns exist in SQLModel but were missing from the live DB (old Alembic migration predated them) | Applied `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` to both `woms_db` and `ml_woms_db` |
| `app/services/order_import/parser.py` | Shopee CSV has an unnamed phone-number column inserted after "Receiver Name", shifting Province/City/Country/Zip Code labels right by 1 position | `parse_shopee_file()` now detects the unnamed column and renames all shifted columns by position index (no duplicate column names created) |

### Why each fix was needed
- **Unicode print**: Windows cmd/uvicorn terminal uses cp1252 by default; Python 3.12 raises on any unencodable char in print()
- **CSV encoding**: The test data CSVs were saved with Windows encoding (cp1252) — they contain characters like ° or Malaysian text that UTF-8 can't decode
- **CAST vs ::jsonb**: SQLAlchemy's text() binds named params (`:name`) then converts to `$N` positional; the `::` Postgres cast operator immediately after `:name` breaks the tokenizer
- **Missing columns**: The Alembic migration `e6f7a8b9c0d1` was created from an older version of the model that didn't yet have `phone_number`/`platform_order_status`; `init_db()` at startup only creates tables that don't exist yet, so columns added to the model after table creation are never added to the live DB automatically
- **Shopee column shift**: Shopee's CSV exporter inserts the phone number column without a header between "Receiver Name" and "Phone Number", pushing all subsequent column labels one position to the right. The delivery address data ends up under the "Phone Number" label, geo columns end up mismatched, etc.

### Test Results (2026-02-23)

```
POST /api/v1/reference/load-platforms  → 4 platforms (test data subset)
POST /api/v1/reference/load-sellers    → 8 sellers
POST /api/v1/reference/load-items      → 499 items, 1497 platform SKUs

POST /api/v1/orders/import [shopee]    → 116/116 success
POST /api/v1/orders/import [lazada]    → 120/120 success
POST /api/v1/orders/import [tiktok]    → 281/281 success

POST /api/v1/ml/sync                   → 505 synced, 12 skipped (duplicate keys in lazada data)

woms_db staging breakdown:
  shopee:  116 rows
  lazada:  120 rows
  tiktok:  281 rows
  total:   517 rows

ml_woms_db staging breakdown:
  shopee:  116 rows
  lazada:  108 rows  (12 duplicate keys skipped)
  tiktok:  281 rows
  total:   505 rows
```

### Remaining Known Issue
- ~~`phone_number` and `platform_order_status` missing-column fix was applied as a direct `ALTER TABLE` to the live DB.~~ **Resolved in v0.3.2**: Alembic stamped to `e6f7a8b9c0d1 (head)` — migration `d5e6f7a8b9c0` in `alembic/versions/` already covers these columns; fresh environments will pick them up via `alembic upgrade head`.

---

## [PRE-ALPHA v0.3.0 | 2026-02-21 ~12:00] — Multi-Platform ETL Pipeline + ML Staging DB

### Context
Extended the import pipeline to support three platforms (Shopee, Lazada, TikTok),
CSV file format in addition to Excel, a reference data loading service for platforms/
sellers/items, a separate ML staging database (`ml_woms_db`), and a sync endpoint
that promotes cleaned staging records from `woms_db` → `ml_woms_db`.

---

### Files Changed

#### `app/services/order_import/parser.py`
**What:** Full rewrite.
- Added `_read_dataframe(file_bytes, filename)` helper — dispatches on `.csv` vs `.xlsx/.xls`
  using `pd.read_csv(..., keep_default_na=False, encoding="utf-8-sig")` for CSV and
  `pd.read_excel()` for Excel.
- Updated `_df_to_records()` to handle both NaN (Excel empty cells) and `""` (CSV empty cells).
- Renamed `parse_shopee_excel` → `parse_shopee_file(file_bytes, filename)`.
- Renamed `parse_lazada_excel` → `parse_lazada_file(file_bytes, filename)`.
- Added `parse_tiktok_file(file_bytes, filename)` — fixes corrupted column header
  `"Tracking ID577729206730130897"` by renaming any column starting with `"Tracking ID"` → `"Tracking ID"`.

**Why:** All three test data files are CSV, not Excel. The original parsers used
`pd.read_excel()` only, so CSV files would have failed silently. The filename-based
dispatch avoids breaking existing Excel workflows.

---

#### `app/services/order_import/cleaner.py`
**What:**
- Added `"%d/%m/%Y %H:%M:%S"` to `_DATE_FORMATS` (TikTok uses DD/MM/YYYY HH:MM:SS).
- Added `clean_tiktok_row()` — cleans all TikTok-specific fields: string fields including
  "Phone #", all timestamp columns (Created Time, Paid Time, RTS Time, etc.),
  decimal fields (Order Amount, SKU Unit Original Price, etc.), Quantity as int.

**Why:** TikTok has a distinct timestamp format and a non-standard phone column name.
Without the new format, all TikTok dates would return None from `parse_flexible_date()`.

---

#### `app/services/order_import/mapper.py`
**What:**
- Added `TIKTOK_FIELD_MAP` (23 staging columns mapped to TikTok CSV column names).
- Registered `"tiktok": TIKTOK_FIELD_MAP` in `_PLATFORM_MAPS`.
- Updated error message in `map_to_staging()` to include tiktok.

**Why:** The mapper is the single source of truth for per-platform column name
translations. Adding TikTok here keeps all platform-specific logic in one place.

---

#### `app/services/order_import/importer.py`
**What:**
- Updated imports: `parse_shopee_file`, `parse_lazada_file`, `parse_tiktok_file`,
  `clean_tiktok_row`.
- Added `"tiktok"` to `_PARSERS` and `_CLEANERS`.
- Changed `parser(file_bytes)` → `parser(file_bytes, filename)` so parsers can
  dispatch on file extension.
- Updated docstring and error message.

**Why:** The orchestrator must pass the filename to parsers so they know whether
to use `pd.read_csv()` or `pd.read_excel()`.

---

#### `app/routers/order_import.py`
**What:**
- Added `"tiktok"` to `_SUPPORTED_PLATFORMS`.
- Extended file extension check to allow `.csv` in addition to `.xlsx/.xls`.
- Updated endpoint descriptions.

**Why:** The API must accept TikTok CSV files and validate platform names correctly.

---

#### `app/services/reference_loader/__init__.py` *(new)*
**What:** Package init — exports `load_platforms`, `load_sellers`, `load_item_master`.

**Why:** Clean public API so the router only imports from the package.

---

#### `app/services/reference_loader/loader.py` *(new)*
**What:** Three async loader functions for seeding reference tables from upload files.
- `load_platforms(session, file_bytes, filename)` — reads `test platform.xlsx` columns
  (Platform_ID, Platform_Name, Address, Postcode); upserts into `platform` table by
  `platform_name` (SELECT-then-update/insert pattern).
- `load_sellers(session, sellers_bytes, sellers_filename, platforms_bytes=None, platforms_filename=None)` —
  reads `test_sellers.xlsx`; resolves Platform_ID codes (MYONL1→Lazada) via an optional
  platform file cross-reference + DB lookup; upserts sellers by `platform_store_id`.
- `load_item_master(session, file_bytes, filename, seller_id)` — reads multi-sheet Excel
  with `header=3` (headers on row 4); filters blank rows by checking `Internal CODE (Main code)`;
  upserts `items` (by `master_sku`), `platform_sku` (by `platform_id/seller_id/platform_sku`),
  and `listing_component` (by `listing_id/item_id`). Creates `BaseUOM` records on demand.

**Why:** Reference data must be loaded once per environment before order imports so
`platform_id`, `seller_id`, and item lookups resolve correctly. The SELECT-then-upsert
pattern avoids needing DB-level unique constraints beyond those already on the models.

---

#### `app/routers/reference.py` *(new)*
**What:** Three `POST` endpoints:
- `POST /api/v1/reference/load-platforms` — accepts single upload file
- `POST /api/v1/reference/load-sellers` — accepts `sellers_file` + optional `platforms_file`
- `POST /api/v1/reference/load-items` — accepts upload file + `seller_id` form field

**Why:** Exposes the reference loaders as REST endpoints for admin upload tooling.
All three are idempotent (safe to re-run).

---

#### `app/config.py`
**What:** Added ML database config fields: `ml_database_host`, `ml_database_port`,
`ml_database_name`, `ml_database_user`, `ml_database_password`, `ml_database_url`
(optional override). Added `async_ml_database_url` property.

**Why:** The ML database URL must be configurable via env vars (`.env` or shell)
without hardcoding credentials.

---

#### `app/ml_database.py` *(new)*
**What:** Separate SQLAlchemy async engine (`ml_engine`) and session factory
(`ml_session_maker`) for `ml_woms_db`. Provides:
- `get_ml_session()` — FastAPI dependency (mirrors `get_session()` from database.py)
- `init_ml_db()` — creates `order_import` schema + all SQLModel tables in `ml_woms_db`
- `check_ml_db_connection()` — health check

**Why:** ML workloads must be completely isolated from the production `woms_db`.
A separate engine with the same SQLModel metadata means both DBs stay in schema sync
without duplicating model definitions.

---

#### `app/services/ml_sync/__init__.py` *(new)*
**What:** Package init — exports `sync_staging_to_ml`, `SyncResult`.

---

#### `app/services/ml_sync/sync.py` *(new)*
**What:** `sync_staging_to_ml(woms_session, ml_session, platform_source=None, seller_id=None)`.
- Reads `order_import_staging` rows from woms_db (with optional platform/seller filters).
- Builds an in-memory set of already-synced keys from ml_woms_db for dedup.
- For each new row: copies the referenced platform + seller to ml_woms_db (satisfies FK
  constraints), then inserts the staging row (with `raw_import_id=None` since raw imports
  are not synced).
- Upsert key: `(platform_source, platform_order_id, platform_sku, seller_id)`.
- Returns `SyncResult` with `staging_synced`, `staging_skipped`, `platforms_synced`,
  `sellers_synced`, and per-row errors.

**Why:** ML models need a clean, isolated copy of processed staging data. Copying
platforms/sellers automatically avoids FK constraint failures in ml_woms_db.

---

#### `app/routers/ml_sync.py` *(new)*
**What:** Two endpoints:
- `POST /api/v1/ml/sync` — JSON body `{platform_source, seller_id}` (both optional);
  runs sync; returns SyncResult as dict.
- `POST /api/v1/ml/init-schema` — calls `init_ml_db()` to create ml_woms_db tables.

**Why:** Exposes sync and init as REST calls so they can be triggered from admin
tooling without shell access.

---

#### `app/main.py`
**What:** Registered `reference_router` at `/api/v1/reference` and `ml_sync_router`
at `/api/v1/ml`.

**Why:** Routers must be attached to the FastAPI app to be served.

---

### New Endpoints Summary

| Method | URL | Purpose |
|---|---|---|
| POST | `/api/v1/orders/import` | Import Shopee/Lazada/TikTok CSV or Excel |
| POST | `/api/v1/reference/load-platforms` | Upsert platforms from file |
| POST | `/api/v1/reference/load-sellers` | Upsert sellers from file |
| POST | `/api/v1/reference/load-items` | Upsert items + platform_skus from file |
| POST | `/api/v1/ml/init-schema` | Initialize ml_woms_db schema |
| POST | `/api/v1/ml/sync` | Sync staging data to ml_woms_db |

---

### Data Quality Issues Documented (TikTok)

| Issue | Handling |
|---|---|
| Column header `"Tracking ID577729206730130897"` — tracking code appended to header | Renamed: any col starting with `"Tracking ID"` → `"Tracking ID"` in `parse_tiktok_file()` |
| Phone column named `"Phone #"` (non-standard) | Mapped directly in `TIKTOK_FIELD_MAP` + cleaned in `clean_tiktok_row()` |
| Timestamps in `DD/MM/YYYY HH:MM:SS` format | Added `"%d/%m/%Y %H:%M:%S"` to `_DATE_FORMATS` |
| All test data files are CSV not Excel | `_read_dataframe()` dispatches on file extension |

### Data Quality Issues Documented (Item Master)

| Issue | Handling |
|---|---|
| Headers in row 4 (not row 1) | `pd.read_excel(..., header=3)` |
| Example data rows between header and real data | Filtered: drop rows where `Internal CODE` is blank |
| Empty trailing columns (`Unnamed: N`) | Ignored — only mapped columns are accessed |
| BaseUOM values not pre-seeded for all items | `get_or_create_uom()` inserts on demand |

---

### Tests Pending
- [ ] `POST /api/v1/orders/import` — Shopee Test Data.csv (shopee, seller_id=1)
- [ ] `POST /api/v1/orders/import` — Lazada Test Data.csv (lazada, seller_id=1)
- [ ] `POST /api/v1/orders/import` — Tiktok Sample Data.csv (tiktok, seller_id=1)
- [ ] `POST /api/v1/reference/load-platforms` — test platform.xlsx → expect 10 platforms
- [ ] `POST /api/v1/reference/load-sellers` — test_sellers.xlsx + test platform.xlsx → expect 15 sellers
- [ ] `POST /api/v1/reference/load-items` — Item Master.xlsx, seller_id=1 → expect ~1900 items
- [ ] `POST /api/v1/ml/init-schema` — verify ml_woms_db tables created
- [ ] `POST /api/v1/ml/sync` — body: `{"platform_source":"tiktok"}` → verify rows copied
- [ ] `SELECT COUNT(*) FROM order_import.order_import_staging` in ml_woms_db — match woms_db count

---

## [PRE-ALPHA v0.1.0 | 2026-02-21 ~09:00] — Order Import Pipeline (Initial Build)

### Context
Analyzed two real e-commerce export files (Shopee 60-col/116-row, Lazada 79-col/120-row) and
implemented a full ingestion pipeline into the existing `order_import` schema in `woms_db`.

---

### Files Changed

#### `app/models/order_import.py`
**What:** Added two new fields to `OrderImportStaging`:
- `phone_number: Optional[str]` (max 50)
- `platform_order_status: Optional[str]` (max 50)

**Why:** The existing staging schema had no field for the shipping contact phone number
(critical for delivery operations) and no way to distinguish the platform's own order status
(e.g. Shopee "Completed", Lazada "packed") from the manually entered `manual_status` column.
These two fields exist in both datasets and are operationally meaningful.

---

#### `alembic/versions/20260221_0900_00_d5e6f7a8b9c0_add_phone_platform_status_to_staging.py`
**What:** New Alembic migration — `ALTER TABLE order_import.order_import_staging`
adds `phone_number VARCHAR(50)` and `platform_order_status VARCHAR(50)`.

**Why:** SQLModel model changes must be mirrored in a migration so the live DB schema
stays in sync. The migration chains from `c4d5e6f7a8b9` (the order_import schema creation).

---

#### `app/services/order_import/parser.py` *(new file)*
**What:** Excel-to-raw-dict parsers for Shopee and Lazada.
- `parse_shopee_excel()` — strips trailing `*` from column names (e.g. `"Tracking Number*"`)
- `parse_lazada_excel()` — renames duplicate `status` column: col 66 → `status_platform`,
  col 76 → `status_manual`

**Why:** Both platforms export columns with platform-specific quirks that must be resolved
before any cleaning or mapping. Doing this at the parse stage keeps downstream code clean
and platform-agnostic.

---

#### `app/services/order_import/cleaner.py` *(new file)*
**What:** Per-platform data cleaning functions.
- `normalize_address()` — replaces fullwidth commas U+FF0C → ASCII `,` (Lazada issue)
- `parse_flexible_date()` — handles ISO, DD.MM.YYYY, D.M.YYYY; returns `None` for
  non-date strings (e.g. driver names found in Shopee's misaligned "Date" column)
- `parse_phone()` — converts float phone numbers (e.g. `60123456789.0`) to clean string
- `clean_shopee_row()` / `clean_lazada_row()` — apply all cleaners per row

**Why:** The raw datasets contain encoding issues (Lazada fullwidth commas), column
misalignment (Shopee "Date" col containing driver names), and type inconsistencies
(phone as float, multiple date formats). Cleaning must happen before mapping to prevent
bad data reaching the staging table.

---

#### `app/services/order_import/mapper.py` *(new file)*
**What:** Field mapping configuration and staging dict builder.
- `SHOPEE_FIELD_MAP` — maps 23 staging columns to their Shopee source column names
- `LAZADA_FIELD_MAP` — maps 23 staging columns to their Lazada source column names
  (with `__LITERAL__1` for quantity since Lazada is 1 item/row, and `__CAST_STR__orderNumber`
  to handle integer order IDs)
- `map_to_staging()` — applies the map and casts values to correct types (Decimal, int, date)

**Why:** Centralising field mappings in one place makes it easy to update when platforms
change their export format, and keeps the importer logic free of per-platform conditionals.

---

#### `app/services/order_import/importer.py` *(new file)*
**What:** Main orchestration function `import_excel_file()`.
Pipeline: parse → generate batch UUID → for each row: insert raw (JSONB) → clean → map → insert staging.
Returns `ImportResult` dataclass with total/success/skipped/error counts and per-row error details.

**Why:** Separating orchestration from parsing/cleaning/mapping means each concern can be
tested and maintained independently. The two-table design (raw + staging) preserves the
original data immutably while giving a clean normalized view for order processing.

---

#### `app/services/order_import/__init__.py` *(new file)*
**What:** Package init — exports `import_excel_file` and `ImportResult`.

**Why:** Clean public API for the service package; consumers import from the package,
not from internal modules directly.

---

#### `app/routers/order_import.py` *(new file)*
**What:** FastAPI router with `POST /api/v1/orders/import`.
Accepts: `platform` (form field), `seller_id` (form field), `file` (UploadFile .xlsx).
Returns: JSON import summary (counts + error list).
Validates: platform name, file extension, file size (≤ 10 MB).

**Why:** Exposes the import pipeline as a REST endpoint so the frontend or admin tooling
can trigger imports without direct DB access. File size limit prevents memory exhaustion
from oversized uploads.

---

#### `app/main.py`
**What:** Registered the new order_import router under `{api_v1_prefix}/orders`.

**Why:** The router must be attached to the FastAPI app to be served. Placed under `/orders`
prefix to keep the import endpoint logically grouped with order-related operations.

---

### Data Quality Issues Documented (from test file analysis)

| Platform | Issue | Handling |
|---|---|---|
| Shopee | "Tracking Number*" column has trailing asterisk | Stripped in `parse_shopee_excel()` |
| Shopee | "Date" col (manual) contains driver names / tracking codes | `parse_flexible_date()` returns `None` for non-date strings |
| Shopee | Mixed date formats (ISO vs DD.MM.YYYY) | `parse_flexible_date()` tries multiple formats |
| Shopee | Phone stored as float (`60123456789.0`) | `parse_phone()` strips `.0` |
| Lazada | Duplicate `status` column (col 66 + col 76) | Renamed to `status_platform` / `status_manual` |
| Lazada | Fullwidth comma U+FF0C in addresses | `normalize_address()` replaces with ASCII `,` |
| Lazada | `orderNumber` stored as integer | `__CAST_STR__` sentinel in mapper |
| Lazada | 27 completely empty columns | Skipped in staging; preserved in raw JSONB |
| Both | Numeric prices as float/int in Excel | `parse_decimal()` → `Decimal` |

---

### Tests Pending
- [ ] `alembic upgrade head` — verify migration applies cleanly
- [ ] `POST /api/v1/orders/import` with Shopee Test Data.xlsx — expect 116 success rows
- [ ] `POST /api/v1/orders/import` with LAZADA Test Data.xlsx — expect 120 success rows
- [ ] Query `order_import.order_import_raw` — verify JSONB row count matches
- [ ] Query `order_import.order_import_staging` — spot-check mapped fields
- [ ] Verify Lazada `platform_order_status = 'packed'` (from col 66)
- [ ] Verify Lazada address has no fullwidth commas after import
- [ ] Verify Shopee non-date "Date" values produce `manual_date = NULL`

---

## [PRE-ALPHA v0.2.0 | 2026-02-21 10:00] — SQL Migration → Python Conversion

### Context
All content from `migrations/*.sql` (triggers, views, seed data, indexes) has been
converted to Python and embedded directly in `app/models/`. The SQL files are retained
as reference only — the application no longer reads them at runtime.

**Why:** Keeping DB logic in external SQL files created an implicit dependency on the
filesystem and made it easy for the schema to drift from the Python models. Embedding
everything in Python means a fresh `init_db_full()` call produces a fully operational
database without any manual SQL steps.

---

### New Files Created

#### `app/models/triggers.py`
**What:** All 8 PostgreSQL trigger functions as Python string constants in `_TRIGGER_SQL`.
Public API: `async def apply_triggers(conn: AsyncConnection) -> None`.

Triggers: `update_timestamp`, `check_inventory_threshold`, `update_inventory_on_transaction`,
`auto_resolve_inventory_alerts`, `update_updated_at_column`, `sync_order_detail_return_status`,
`calculate_exchange_value_difference`, `calculate_price_adjustment_final`.

**Why:** `CREATE OR REPLACE FUNCTION` and `DROP TRIGGER IF EXISTS` make every statement
idempotent. Called from `database.run_migrations()` so triggers are always applied after
`create_all()` without needing to run SQL files manually.

---

#### `app/models/views.py`
**What:** All 12 reporting views as Python string constants.
Public API: `async def apply_views(conn: AsyncConnection) -> None`.

Views: `v_inventory_status`, `v_order_fulfillment`, `v_seller_warehouse_routing`,
`v_platform_import_status`, `v_active_inventory_alerts`, `v_warehouse_summary`,
`v_order_line_items`, `v_order_returns`, `v_order_exchanges`, `v_order_modifications`,
`v_order_price_adjustments`, `v_order_operations_summary`.

**Why:** `CREATE OR REPLACE VIEW` is idempotent. Views provide denormalized read-only
projections used by reporting/dashboard queries.

---

#### `app/models/seed.py`
**What:** All lookup table seed data as Python data structures.
Public API: `async def seed_database(session: AsyncSession) -> None`.

Tables seeded: `action_type`, `status`, `item_type`, `base_uom`, `inventory_type`,
`movement_type`, `delivery_status`, `roles`, `platform`, `cancellation_reason`,
`return_reason`, `exchange_reason`.

**Why:** `INSERT … ON CONFLICT DO NOTHING` is idempotent. Seed data is required for
FK lookups and role-based access control and must be applied immediately after schema creation.

---

#### `alembic/versions/20260221_1000_00_e6f7a8b9c0d1_add_all_performance_indexes.py`
**What:** Alembic migration applying all 47 performance indexes (GIN + composite +
partial) to existing databases using `CREATE INDEX IF NOT EXISTS`.

**Why:** `__table_args__` indexes are created by `create_all()` for fresh databases
but existing databases need an explicit Alembic migration. All statements use
`IF NOT EXISTS` so re-running is safe.

---

### Files Modified

#### `app/models/items.py`
**What:** Added `__table_args__` to `Item` (GIN on `variations_data`; partial active items)
and `ItemsHistory` (GIN on `snapshot_data`).

**Why:** GIN enables `@>` JSONB containment queries. Partial index covers the
overwhelmingly common "active items only" query pattern.

---

#### `app/models/warehouse.py`
**What:** Added `__table_args__` to `Warehouse`, `InventoryLevel`, `InventoryAlert`,
`SellerWarehouse`, `InventoryTransaction` — composite and partial indexes for stock
lookups, FIFO/FEFO allocation, alert dashboards, and transaction history.

**Why:** Inventory queries are the highest-frequency operations in a WMS.

---

#### `app/models/users.py`
**What:** Added `__table_args__` to `Role` (GIN on `permissions`) and `AuditLog`
(GIN on `old_data` and `new_data`).

**Why:** Enables permission-level JSONB queries and before/after change queries on the
audit log without full table scans.

---

#### `app/models/orders.py`
**What:** Added `Index` + `text` imports. Added `__table_args__` to `Seller`, `PlatformRawImport`,
`PlatformSKU`, `CustomerPlatform`, `Order`, `OrderDetail` — GIN indexes on all JSONB
fields; composite indexes for fulfillment queue, reporting, SKU translation; partial
indexes for pending orders and active-only filtering.

**Why:** Order queries are the most common read pattern. Partial indexes on "pending"
orders avoid scanning completed/cancelled rows.

---

#### `app/models/order_operations.py`
**What:** Added `Index` + `text` imports. Added `__table_args__` to `ReturnReason`,
`OrderReturn`, `ExchangeReason`, `OrderExchange`, `OrderModification`, `OrderPriceAdjustment`.

Partial indexes on optional FK columns use `WHERE col IS NOT NULL` — avoids indexing NULL
entries which are never used in FK-specific joins.

**Why:** GIN on JSONB diffs enables audit trail queries by field value.

---

#### `app/database.py`
**What:** Replaced `run_migrations()` (read SQL files) with calls to `apply_triggers(conn)`,
`apply_views(conn)`, `seed_database(session)` from the new Python modules.

**Why:** Application no longer depends on `migrations/*.sql` at runtime. All DB init
logic is self-contained in Python and importable/testable.

---

#### `app/models/__init__.py`
**What:** Added imports and `__all__` entries for `apply_triggers`, `apply_views`,
`seed_database`.

**Why:** Callers that already import from `app.models` can access init utilities without
a separate import path.

---

### Tests Pending
- [ ] `alembic upgrade head` — confirm `e6f7a8b9c0d1` applies without error
- [ ] `python -c "import asyncio; from app.database import init_db_full; asyncio.run(init_db_full())"` — fresh DB: confirm triggers/views/seed applied
- [ ] `SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename` — verify 47 new indexes present
- [ ] `SELECT * FROM action_type` — confirm seed data populated
- [ ] GIN query test: `SELECT * FROM orders WHERE platform_raw_data @> '{"platform":"shopee"}'`

---

## [PRE-ALPHA v0.1.1 | 2026-02-21 ~09:30] — Ground Rules & Version Control Setup

### Files Changed

#### `version_update.md` *(this file — new)*
**What:** Created version update log with pre-alpha versioning scheme.
Backfilled all v0.1.0 work.

**Why:** User ground rule — all changes must be logged with version label, timestamp,
file changed, what was done, and why.

#### `C:\Users\James\.claude\projects\d--Documents-Project-WOMS-FYP-NEW\memory\MEMORY.md`
**What:** Added ground rule #5 (version_update.md logging) and created the file with
project overview, key file paths, recent work summary, and patterns.

**Why:** Persists project context and user preferences across Claude sessions so rules
and architecture decisions don't need to be re-explained each time.
