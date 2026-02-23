# WOMS - Warehouse Order Management System

A production-ready FastAPI backend for managing warehouse operations, inventory, orders, and deliveries.

## Features

- **Items Management** - Products, variations, categories, brands with version control
- **Inventory Control** - Stock levels, locations, movements, batch/lot tracking
- **Order Processing** - Multi-platform e-commerce integration, order fulfillment
- **Delivery Management** - Drivers, vehicles, trips, real-time tracking
- **User Administration** - Role-based access, comprehensive audit logging
- **Version Control Snapshots** - JSONB-based change tracking for compliance

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL with JSONB support
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose)
- **Async Support**: asyncpg

## Project Structure

```
woms-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection & schema
│   └── models/
│       ├── __init__.py      # Model exports
│       ├── items.py         # Items, Status, Brand, Category, etc.
│       ├── warehouse.py     # Warehouse, Locations, Inventory
│       ├── orders.py        # Orders, Platforms, Sellers
│       ├── delivery.py      # Drivers, Trips, Tracking
│       └── users.py         # Users, Roles, Audit
├── alembic/
│   ├── env.py               # Alembic environment
│   ├── script.py.mako       # Migration template
│   └── versions/            # Migration files
├── requirements.txt
├── .env.template
├── setup.py                 # One-click setup script
├── alembic.ini
└── README.md
```

## Database Schema

> **Full Documentation:** See [docs/DATABASE.md](docs/DATABASE.md) for complete schema documentation including all tables, columns, relationships, indexes, triggers, and views.

### Module Overview

| Module | Tables | Purpose |
|--------|--------|---------|
| **Items** | 8 tables | Product catalog, variations, version history |
| **Warehouse** | 11 tables | Physical locations, inventory tracking, alerts |
| **Orders** | 8 tables | Order processing, platform integration, raw imports |
| **Delivery** | 9 tables | Fleet management, trip tracking |
| **Users** | 3 tables | Authentication, authorization, audit |

### Key Features

1. **Version Control Snapshots** - Items history with JSONB for field-level change tracking
2. **Multi-Platform Support** - Translator table bridges platform SKUs to internal items
3. **Flexible Storage** - JSONB fields for addresses, customer data, permissions
4. **Batch/Lot Tracking** - Support for FIFO, LIFO, FEFO inventory methods
5. **Inventory Alerts** - Automatic low stock alerts with PostgreSQL triggers
6. **Raw Data Preservation** - Store Excel/API imports for auditing

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd woms-backend
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

   Or manually:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Windows)
   .\venv\Scripts\activate
   
   # Activate (Linux/Mac)
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Copy template
   cp .env.template .env
   
   # Edit with your settings
   # - DATABASE_HOST, DATABASE_PORT, DATABASE_NAME
   # - DATABASE_USER, DATABASE_PASSWORD
   # - SECRET_KEY (generate with: openssl rand -hex 32)
   ```

4. **Create PostgreSQL database**
   ```sql
   CREATE DATABASE woms_db;
   ```

5. **Initialize the database**
   ```bash
   # Option 1: Full initialization - tables + triggers + indexes + views (recommended)
   python -c "import asyncio; from app.database import init_db_full; asyncio.run(init_db_full())"
   
   # Option 2: Tables only (then run migrations separately)
   python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"
   
   # Option 3: Using Alembic migrations (production)
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   python -c "import asyncio; from app.database import run_migrations; asyncio.run(run_migrations())"
   ```

6. **Start the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

7. **Access the API**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## API Endpoints (Planned)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/items` | GET, POST | List/Create items |
| `/api/v1/items/{id}` | GET, PUT, DELETE | Item CRUD |
| `/api/v1/warehouse` | GET, POST | Warehouse management |
| `/api/v1/inventory` | GET | Inventory levels |
| `/api/v1/orders` | GET, POST | Order processing |
| `/api/v1/delivery/trips` | GET, POST | Trip management |
| `/api/v1/users` | GET, POST | User administration |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_HOST` | PostgreSQL host | localhost |
| `DATABASE_PORT` | PostgreSQL port | 5432 |
| `DATABASE_NAME` | Database name | woms_db |
| `DATABASE_USER` | Database user | postgres |
| `DATABASE_PASSWORD` | Database password | - |
| `SECRET_KEY` | JWT signing key | - |
| `DEBUG` | Enable debug mode | false |
| `CORS_ORIGINS` | Allowed CORS origins | localhost |

## Development

### Running Tests
```bash
pytest
```

### Type Checking
```bash
mypy app/
```

### Code Formatting
```bash
black app/
isort app/
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
