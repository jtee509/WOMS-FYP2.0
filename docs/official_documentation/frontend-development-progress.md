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
7. **Component Architecture**: Dedicated component section (`src/components/`) for reusable functions (e.g., printing utilities, shared UI widgets)
8. **Styling Standards**: All CSS must be in separate files — no inline styles or in-component style blocks
9. **Routing Configuration**: Use `BrowserRouter` for application routing
10. **Tailwind CSS**: Use Tailwind CSS v4 as the base styling framework — all new styling must use Tailwind utility classes. MUI `sx` prop and `.styles.ts` files are deprecated and will be migrated to Tailwind

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
