# Frontend Development Progress

All frontend updates, changes, and new feature implementations are documented here. Each entry must state **what** was changed and **why**.

Format: `[PRE-ALPHA vX.Y.Z | YYYY-MM-DD HH:MM] — Brief title`

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
