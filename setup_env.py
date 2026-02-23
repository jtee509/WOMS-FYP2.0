#!/usr/bin/env python3
"""
WOMS Environment & Database Auto-Setup

Generates a complete .env file with cryptographically secure keys and
auto-provisions the PostgreSQL user + both databases (woms_db, ml_woms_db).

Usage:
    python setup_env.py                  # Interactive: generate .env + create DB user/databases
    python setup_env.py --generate-only  # Only write .env (skip DB provisioning)
    python setup_env.py --force          # Overwrite existing .env without prompting
    python setup_env.py --db-host HOST   # Custom PostgreSQL host (default: localhost)
    python setup_env.py --db-port PORT   # Custom PostgreSQL port (default: 5432)

What this script does:
    1. Generates a 256-bit SECRET_KEY (token_hex)
    2. Generates a URL-safe random password for the DB application user
    3. Connects to PostgreSQL as the admin user (postgres) to:
       - CREATE USER woms_user WITH PASSWORD '...'
       - CREATE DATABASE woms_db   OWNER woms_user
       - CREATE DATABASE ml_woms_db OWNER woms_user
       - GRANT ALL PRIVILEGES ON both databases
    4. Writes a fully-populated .env to the project root (no placeholder values)

Admin credentials (postgres password) are only used during setup and are
NEVER written to the .env file.
"""

import argparse
import getpass
import secrets
import sys
from datetime import datetime
from pathlib import Path


# =============================================================================
# Constants — change here if project is renamed
# =============================================================================
PROJECT_ROOT = Path(__file__).parent
ENV_FILE     = PROJECT_ROOT / ".env"

DB_APP_USER  = "woms_user"       # dedicated application DB user (not postgres superuser)
DB_NAME      = "woms_db"         # production database
ML_DB_NAME   = "ml_woms_db"      # ML staging database


# =============================================================================
# Helpers
# =============================================================================

def _ok(msg: str)   -> None: print(f"  [OK]   {msg}")
def _warn(msg: str) -> None: print(f"  [WARN] {msg}")
def _err(msg: str)  -> None: print(f"  [ERR]  {msg}")


def generate_password(byte_length: int = 32) -> str:
    """
    Generate a URL-safe random password (base64url alphabet: A-Z a-z 0-9 - _).
    Safe to embed directly in connection URLs without percent-encoding.
    """
    return secrets.token_urlsafe(byte_length)


def generate_secret_key() -> str:
    """Generate a 256-bit hex secret key for JWT signing."""
    return secrets.token_hex(32)


# =============================================================================
# .env writer
# =============================================================================

def write_env_file(
    db_user:     str,
    db_password: str,
    secret_key:  str,
    host:        str = "localhost",
    port:        int = 5432,
) -> None:
    """Write a fully-populated .env to the project root."""

    db_url      = f"postgresql+asyncpg://{db_user}:{db_password}@{host}:{port}/{DB_NAME}"
    db_url_sync = f"postgresql+psycopg://{db_user}:{db_password}@{host}:{port}/{DB_NAME}"
    ml_db_url   = f"postgresql+asyncpg://{db_user}:{db_password}@{host}:{port}/{ML_DB_NAME}"
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""\
# =============================================================================
# WOMS - Warehouse Order Management System
# Auto-generated environment configuration
# Generated : {timestamp}
# NEVER commit this file to version control (.gitignore enforces this)
# =============================================================================

# -----------------------------------------------------------------------------
# Database — woms_db  (production)
# -----------------------------------------------------------------------------
DATABASE_HOST={host}
DATABASE_PORT={port}
DATABASE_NAME={DB_NAME}
DATABASE_USER={db_user}
DATABASE_PASSWORD={db_password}

# Fully-assembled connection URLs (used by SQLAlchemy / Alembic)
DATABASE_URL={db_url}
DATABASE_URL_SYNC={db_url_sync}

# -----------------------------------------------------------------------------
# Database — ml_woms_db  (ML staging, same user/password)
# -----------------------------------------------------------------------------
ML_DATABASE_HOST={host}
ML_DATABASE_PORT={port}
ML_DATABASE_NAME={ML_DB_NAME}
ML_DATABASE_USER={db_user}
ML_DATABASE_PASSWORD={db_password}
ML_DATABASE_URL={ml_db_url}

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------
APP_NAME=WOMS API
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=development

API_V1_PREFIX=/api/v1
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# -----------------------------------------------------------------------------
# Security — auto-generated 256-bit key (do not share or regenerate carelessly)
# -----------------------------------------------------------------------------
SECRET_KEY={secret_key}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# -----------------------------------------------------------------------------
# Server
# -----------------------------------------------------------------------------
HOST=0.0.0.0
PORT=8000
WORKERS=1
RELOAD=true

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
"""

    ENV_FILE.write_text(content, encoding="utf-8")


# =============================================================================
# PostgreSQL provisioning
# =============================================================================

def provision_postgres(
    admin_user:     str,
    admin_password: str,
    host:           str,
    port:           int,
    app_user:       str,
    app_password:   str,
) -> bool:
    """
    Connect as the Postgres admin user and:
      - CREATE (or update) the application user
      - CREATE woms_db and ml_woms_db owned by that user
      - GRANT full privileges

    Returns True on success, False on failure.
    Uses parameterised queries for passwords to prevent injection.
    """
    try:
        import psycopg
        import psycopg.errors as pgerr
    except ImportError:
        _err("psycopg3 not found — run:  pip install psycopg-binary")
        return False

    admin_dsn = f"host={host} port={port} user={admin_user} password={admin_password} dbname=postgres"

    try:
        with psycopg.connect(admin_dsn, autocommit=True) as conn:

            # ── Create / update application user ──────────────────────────
            try:
                conn.execute(
                    "CREATE USER %s WITH PASSWORD %%s" % app_user,
                    (app_password,),
                )
                _ok(f"Created PostgreSQL user: {app_user}")
            except pgerr.DuplicateObject:
                conn.execute(
                    "ALTER USER %s WITH PASSWORD %%s" % app_user,
                    (app_password,),
                )
                _ok(f"User '{app_user}' already exists — password updated")

            # ── Create databases ───────────────────────────────────────────
            for db in (DB_NAME, ML_DB_NAME):
                try:
                    conn.execute(f'CREATE DATABASE "{db}" OWNER {app_user}')
                    _ok(f"Created database: {db}")
                except pgerr.DuplicateDatabase:
                    conn.execute(f'ALTER DATABASE "{db}" OWNER TO {app_user}')
                    _ok(f"Database '{db}' already exists — owner updated to {app_user}")

            # ── Grant privileges ───────────────────────────────────────────
            for db in (DB_NAME, ML_DB_NAME):
                conn.execute(
                    f'GRANT ALL PRIVILEGES ON DATABASE "{db}" TO {app_user}'
                )
            _ok(f"Granted ALL PRIVILEGES on {DB_NAME} and {ML_DB_NAME} to {app_user}")

        return True

    except psycopg.OperationalError as exc:
        _err(f"Cannot connect to PostgreSQL: {exc}")
        return False
    except Exception as exc:
        _err(f"Unexpected error during DB provisioning: {exc}")
        return False


def print_manual_sql(app_user: str, app_password: str) -> None:
    """Print the equivalent SQL for the user to run manually."""
    print("\n  Run these SQL statements as the postgres superuser:")
    print("  " + "-" * 56)
    print(f"  CREATE USER {app_user} WITH PASSWORD '{app_password}';")
    print(f"  CREATE DATABASE {DB_NAME} OWNER {app_user};")
    print(f"  CREATE DATABASE {ML_DB_NAME} OWNER {app_user};")
    print(f"  GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {app_user};")
    print(f"  GRANT ALL PRIVILEGES ON DATABASE {ML_DB_NAME} TO {app_user};")
    print("  " + "-" * 56)


# =============================================================================
# Entry point
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="WOMS: auto-generate .env and provision PostgreSQL"
    )
    parser.add_argument(
        "--generate-only", action="store_true",
        help="Only write .env — skip database provisioning",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing .env without asking",
    )
    parser.add_argument("--db-host", default="localhost", metavar="HOST",
                        help="PostgreSQL host (default: localhost)")
    parser.add_argument("--db-port", type=int, default=5432, metavar="PORT",
                        help="PostgreSQL port (default: 5432)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  WOMS  —  Environment & Database Auto-Setup")
    print("=" * 60)

    # ── Guard: existing .env ───────────────────────────────────────────────
    if ENV_FILE.exists() and not args.force:
        print(f"\n  .env already exists at {ENV_FILE}")
        answer = input("  Overwrite? (y/N): ").strip().lower()
        if answer != "y":
            print("  Aborted — existing .env unchanged.")
            sys.exit(0)

    # ── Generate secrets ───────────────────────────────────────────────────
    print()
    db_password = generate_password(32)
    secret_key  = generate_secret_key()
    _ok("Generated SECRET_KEY            (256-bit, HS256-ready)")
    _ok(f"Generated DB password for user  '{DB_APP_USER}'")

    db_ok = False  # will be set to True if provisioning succeeds

    # ── PostgreSQL provisioning ────────────────────────────────────────────
    if not args.generate_only:
        print(f"\n  PostgreSQL admin credentials (used once — not stored):")
        admin_user = input(f"  Admin username (default: postgres): ").strip() or "postgres"
        admin_pass = getpass.getpass(f"  Password for '{admin_user}': ")

        print(f"\n  Provisioning PostgreSQL on {args.db_host}:{args.db_port} ...")
        db_ok = provision_postgres(
            admin_user=admin_user,
            admin_password=admin_pass,
            host=args.db_host,
            port=args.db_port,
            app_user=DB_APP_USER,
            app_password=db_password,
        )

        if not db_ok:
            print_manual_sql(DB_APP_USER, db_password)
            answer = input("\n  Write .env anyway? (Y/n): ").strip().lower()
            if answer == "n":
                sys.exit(1)
    else:
        print("\n  --generate-only: skipping database provisioning")

    # ── Write .env ─────────────────────────────────────────────────────────
    write_env_file(
        db_user=DB_APP_USER,
        db_password=db_password,
        secret_key=secret_key,
        host=args.db_host,
        port=args.db_port,
    )
    _ok(f"Written: {ENV_FILE}")

    # ── Next steps ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SETUP COMPLETE" + ("  (DB provisioned)" if db_ok else "  (manual DB setup needed)"))
    print("=" * 60)
    print("""
  Next steps:

    1.  cd backend

    2.  Run Alembic migrations:
        ../.venv/Scripts/alembic upgrade head

    3.  Start the server:
        ../.venv/Scripts/uvicorn app.main:app --reload

    4.  Open API docs:
        http://localhost:8000/docs
""")


if __name__ == "__main__":
    main()
