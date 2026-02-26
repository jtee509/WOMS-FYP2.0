# WOMS — Warehouse Order Management System

A full-stack warehouse operations platform: multi-platform order ingestion (Shopee, Lazada, TikTok), inventory management, delivery tracking, and an ML staging pipeline.

**Status:** PRE-ALPHA v0.5.1 · Python 3.13 · Node 22+ · PostgreSQL 13+

---

## Features

| Area | What it does |
|------|-------------|
| **Order Import ETL** | Parse and stage CSV/XLSX orders from Shopee, Lazada, and TikTok into `order_import_staging` |
| **Reference Data** | Load platforms, sellers, and item master (SKU catalogue) via admin endpoints |
| **ML Staging DB** | Separate `ml_woms_db` database; sync staged orders for ML training |
| **Inventory** | Stock levels, locations, movements, batch/lot tracking |
| **Delivery** | Drivers, vehicles, trips, real-time tracking |
| **Users** | Role-based access, audit logging |
| **Frontend** | React + MUI dashboard with sidebar navigation, API integration |

---

## Tech Stack

### Backend

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.111 |
| ORM | SQLModel 0.0.31 (SQLAlchemy 2 + Pydantic 2) |
| Database | PostgreSQL 13+ with JSONB, triggers, views |
| Async driver | asyncpg 0.31 |
| Sync driver | psycopg 3 (Alembic migrations) |
| Migrations | Alembic 1.13 |
| Auth | JWT via python-jose |

### Frontend

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + TypeScript (Strict) |
| Build tool | Vite 6 |
| UI Library | Material UI (MUI) 6 |
| Routing | react-router-dom 7 (HashRouter) |
| Sidebar | react-pro-sidebar |
| HTTP client | axios |
| Charts | D3.js (useRef pattern) |
| Font | Montserrat (Google Fonts) |

---

## Project Layout

```
WOMS-FYP-NEW/                       ← repository root
├── .env                            ← secrets (git-ignored, auto-generated)
├── .env.template                   ← safe template committed to git
├── setup_env.py                    ← auto-generates .env + provisions PostgreSQL
├── setup.py                        ← one-click venv + deps setup
│
├── backend/                        ← FastAPI application
│   ├── alembic/                    ← migration scripts
│   │   └── versions/               ← 8 migration files (head: e6f7a8b9c0d1)
│   ├── alembic.ini
│   ├── requirements.txt
│   │
│   ├── app/
│   │   ├── main.py                 ← FastAPI app, lifespan hooks
│   │   ├── config.py               ← pydantic-settings, reads .env from root
│   │   ├── database.py             ← async engine, init_db(), run_migrations()
│   │   ├── ml_database.py          ← separate engine for ml_woms_db
│   │   │
│   │   ├── models/                 ← 49 SQLModel table classes
│   │   │   ├── items.py            ← product catalogue, SKUs, version history
│   │   │   ├── warehouse.py        ← locations, inventory, alerts
│   │   │   ├── orders.py           ← orders, platforms, sellers
│   │   │   ├── order_operations.py ← returns, cancellations
│   │   │   ├── delivery.py         ← drivers, trips, tracking
│   │   │   ├── users.py            ← auth, roles, audit
│   │   │   ├── order_import.py     ← raw + staging import tables
│   │   │   ├── triggers.py         ← PostgreSQL triggers (Python-managed)
│   │   │   ├── views.py            ← PostgreSQL views (Python-managed)
│   │   │   └── seed.py             ← lookup-table seed data
│   │   │
│   │   ├── routers/
│   │   │   ├── order_import.py     ← POST /api/v1/orders/import
│   │   │   ├── reference.py        ← POST /api/v1/reference/load-*
│   │   │   └── ml_sync.py          ← POST /api/v1/ml/sync
│   │   │
│   │   ├── services/
│   │   │   ├── order_import/       ← parser → cleaner → mapper → importer
│   │   │   ├── reference_loader/   ← platform / seller / item-master loaders
│   │   │   └── ml_sync/            ← staging → ml_woms_db sync
│   │   │
│   │   └── migrations/             ← deprecated SQL reference files (not executed)
│
├── frontend/                       ← React + Vite + TypeScript app
│   ├── index.html                  ← Montserrat font, app title
│   ├── vite.config.ts              ← dev proxy to backend, Electron-compatible base
│   ├── package.json
│   │
│   └── src/
│       ├── main.tsx                ← ThemeProvider + HashRouter entry
│       ├── App.tsx                 ← Route definitions
│       ├── theme/theme.ts          ← MUI theme (Montserrat, custom palette)
│       ├── layouts/MainLayout.tsx  ← Sidebar + AppBar + Outlet
│       ├── pages/                  ← Dashboard, OrderImport, Reference, MLSync, 404
│       ├── api/                    ← Axios client + endpoint modules
│       ├── types/                  ← TypeScript interfaces (API + JSONB)
│       ├── services/               ← Data service layer (multi-DB toggle)
│       ├── hooks/                  ← useD3 (D3 + React integration)
│       └── components/common/      ← Reusable UI components
│
└── docs/                           ← all documentation (project root)
    ├── official_documentation/
    │   ├── database_structure.md           ← full schema reference
    │   ├── version_update.md               ← changelog (PRE-ALPHA vX.Y.Z)
    │   ├── web-api.md                      ← API endpoint documentation
    │   ├── frontend-development-progress.md ← frontend change log
    │   └── frontend-error.md               ← frontend error tracker
    └── planning_phase/                     ← design notes (5 files)
```

---

## Quick Start

### Prerequisites

- Python 3.13
- Node.js 22+
- PostgreSQL 13+

### 1 — Clone

```bash
git clone https://github.com/jtee509/WOMS-FYP2.0.git
cd WOMS-FYP2.0
```

### 2 — Install dependencies

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 3 — Generate `.env` and provision databases

```bash
python setup_env.py
```

This will:
- Generate a 256-bit `SECRET_KEY` and a random database password
- Create PostgreSQL user `woms_user` with the generated password
- Create `woms_db` (production) and `ml_woms_db` (ML staging), owned by `woms_user`
- Write a complete `.env` to the project root

You will be prompted once for your PostgreSQL admin password. It is never stored.

> **Skip DB provisioning?** Use `python setup_env.py --generate-only` to only write the `.env` and run the SQL manually (the script prints the statements).

### 4 — Run migrations

```bash
cd backend
../python -m alembic upgrade head
```

### 5 — Start the backend

```bash
cd backend
../python -m uvicorn app.main:app --reload
```

### 6 — Start the frontend

```bash
cd frontend
npm run dev
```

### 7 — Open the app

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Frontend (React dashboard) |
| http://localhost:8000/docs | Swagger UI (backend API) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check |

---

## API Endpoints

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/login` | Authenticate with email + password, receive JWT |
| `GET` | `/api/v1/auth/me` | Get current user profile (requires Bearer token) |

**Test account:** `admin@admin.com` / `Admin123`

### Order Import

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/orders/import` | Upload Shopee / Lazada / TikTok CSV or XLSX |

**Form fields:** `platform` (shopee / lazada / tiktok), `seller_id` (int), `file` (upload)

### Reference Data

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/reference/load-platforms` | Upload platform list XLSX |
| `POST` | `/api/v1/reference/load-sellers` | Upload seller list XLSX |
| `POST` | `/api/v1/reference/load-items` | Upload item master XLSX |

### ML Staging

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ml/sync` | Copy staged orders → `ml_woms_db` |
| `POST` | `/api/v1/ml/init-schema` | Initialise `ml_woms_db` schema |

> Full API documentation: [`docs/official_documentation/web-api.md`](docs/official_documentation/web-api.md)

---

## Database Migrations

```bash
cd backend

# Apply all pending migrations
../python -m alembic upgrade head

# Current migration head
../python -m alembic current

# Generate a new migration after model changes
../python -m alembic revision --autogenerate -m "describe change"

# Roll back one migration
../python -m alembic downgrade -1
```

Current migration head: `e6f7a8b9c0d1`

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_HOST` | PostgreSQL host | `localhost` |
| `DATABASE_PORT` | PostgreSQL port | `5432` |
| `DATABASE_NAME` | Production database | `woms_db` |
| `DATABASE_USER` | App DB user | `woms_user` |
| `DATABASE_PASSWORD` | App DB password | _(generated)_ |
| `DATABASE_URL` | Full async URL | _(assembled)_ |
| `DATABASE_URL_SYNC` | Full sync URL (Alembic) | _(assembled)_ |
| `ML_DATABASE_NAME` | ML staging database | `ml_woms_db` |
| `ML_DATABASE_URL` | Full ML async URL | _(assembled)_ |
| `SECRET_KEY` | JWT signing key (256-bit) | _(generated)_ |
| `DEBUG` | Enable debug / SQL logging | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `localhost:3000, 5173` |

All values are auto-populated by `setup_env.py`. See `.env.template` for the full list.

---

## Documentation

| File | Contents |
|------|----------|
| [`docs/official_documentation/database_structure.md`](docs/official_documentation/database_structure.md) | Full schema: all 49 tables, columns, indexes, triggers, views |
| [`docs/official_documentation/version_update.md`](docs/official_documentation/version_update.md) | Changelog — every change logged with version + timestamp |
| [`docs/official_documentation/web-api.md`](docs/official_documentation/web-api.md) | API endpoint documentation with request/response formats |
| [`docs/official_documentation/frontend-development-progress.md`](docs/official_documentation/frontend-development-progress.md) | Frontend development changelog |
| [`docs/official_documentation/frontend-error.md`](docs/official_documentation/frontend-error.md) | Frontend error tracking log |

---

## License

MIT License — see LICENSE file for details.
