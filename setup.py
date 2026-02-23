#!/usr/bin/env python3
"""
WOMS - Warehouse Order Management System
One-Click Setup Script

This script automates the complete setup process:
1. Creates virtual environment
2. Installs dependencies
3. Copies environment template
4. Initializes the database schema
5. Runs initial migrations

Usage:
    python setup.py              # Full setup
    python setup.py --db-only    # Only initialize database
    python setup.py --deps-only  # Only install dependencies
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path


# Configuration
PROJECT_ROOT = Path(__file__).parent
VENV_DIR = PROJECT_ROOT / "venv"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_TEMPLATE = PROJECT_ROOT / ".env.template"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"


def print_banner():
    """Print setup banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   WOMS - Warehouse Order Management System                   ║
    ║   One-Click Setup Script                                     ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_step(step: int, message: str):
    """Print a step message."""
    print(f"\n{'='*60}")
    print(f"  Step {step}: {message}")
    print(f"{'='*60}\n")


def print_success(message: str):
    """Print success message."""
    print(f"  ✓ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"  ✗ ERROR: {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"  ! WARNING: {message}")


def run_command(command: list, cwd: Path = None, env: dict = None) -> bool:
    """Run a command and return success status."""
    try:
        process = subprocess.run(
            command,
            cwd=cwd or PROJECT_ROOT,
            env=env or os.environ.copy(),
            check=True,
            capture_output=True,
            text=True
        )
        if process.stdout:
            print(process.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(command)}")
        if e.stderr:
            print(e.stderr)
        return False


def get_python_executable() -> str:
    """Get the Python executable path."""
    if sys.platform == "win32":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def get_pip_executable() -> str:
    """Get the pip executable path."""
    if sys.platform == "win32":
        return str(VENV_DIR / "Scripts" / "pip.exe")
    return str(VENV_DIR / "bin" / "pip")


def create_virtual_environment() -> bool:
    """Create Python virtual environment."""
    print_step(1, "Creating Virtual Environment")
    
    if VENV_DIR.exists():
        print_warning(f"Virtual environment already exists at {VENV_DIR}")
        response = input("  Do you want to recreate it? (y/N): ").strip().lower()
        if response == 'y':
            shutil.rmtree(VENV_DIR)
        else:
            print_success("Using existing virtual environment")
            return True
    
    if run_command([sys.executable, "-m", "venv", str(VENV_DIR)]):
        print_success(f"Virtual environment created at {VENV_DIR}")
        return True
    return False


def install_dependencies() -> bool:
    """Install Python dependencies."""
    print_step(2, "Installing Dependencies")
    
    pip = get_pip_executable()
    
    # Upgrade pip first
    print("  Upgrading pip...")
    if not run_command([pip, "install", "--upgrade", "pip"]):
        print_warning("Failed to upgrade pip, continuing anyway...")
    
    # Install requirements
    print("  Installing requirements...")
    if run_command([pip, "install", "-r", str(REQUIREMENTS)]):
        print_success("All dependencies installed successfully")
        return True
    return False


def setup_environment_file() -> bool:
    """Setup environment configuration file."""
    print_step(3, "Setting Up Environment Configuration")
    
    if ENV_FILE.exists():
        print_warning(f".env file already exists")
        print_success("Skipping environment file creation")
        return True
    
    if not ENV_TEMPLATE.exists():
        print_error(f".env.template not found at {ENV_TEMPLATE}")
        return False
    
    shutil.copy(ENV_TEMPLATE, ENV_FILE)
    print_success(f"Created .env file from template")
    print_warning("Please edit .env file with your database credentials!")
    return True


def initialize_database() -> bool:
    """Initialize the database schema."""
    print_step(4, "Initializing Database Schema")
    
    python = get_python_executable()
    
    # Create a temporary script to initialize the database
    init_script = PROJECT_ROOT / "_init_db.py"
    init_code = '''
import asyncio
import sys
sys.path.insert(0, str({project_root!r}))

from app.database import init_db, engine
from app.models import *  # Import all models to register them

async def main():
    print("  Creating database tables...")
    await init_db()
    print("  Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(main())
'''.format(project_root=str(PROJECT_ROOT))
    
    try:
        init_script.write_text(init_code)
        
        if run_command([python, str(init_script)]):
            print_success("Database schema created successfully")
            return True
        else:
            print_warning("Database initialization failed. Make sure:")
            print("    1. PostgreSQL is running")
            print("    2. .env file has correct database credentials")
            print("    3. Database exists (create with: CREATE DATABASE woms_db;)")
            return False
    finally:
        if init_script.exists():
            init_script.unlink()


def setup_alembic() -> bool:
    """Initialize Alembic for migrations."""
    print_step(5, "Setting Up Database Migrations (Alembic)")
    
    alembic_dir = PROJECT_ROOT / "alembic"
    
    if alembic_dir.exists():
        print_success("Alembic already configured")
        return True
    
    python = get_python_executable()
    
    if run_command([python, "-m", "alembic", "init", "alembic"]):
        print_success("Alembic initialized")
        
        # Update alembic.ini with proper configuration
        alembic_ini = PROJECT_ROOT / "alembic.ini"
        if alembic_ini.exists():
            content = alembic_ini.read_text()
            # The sqlalchemy.url will be set from env in env.py
            print_success("Alembic configuration complete")
        return True
    return False


def print_next_steps():
    """Print next steps for the user."""
    print("\n" + "="*60)
    print("  SETUP COMPLETE!")
    print("="*60)
    print("""
  Next Steps:
  
  1. Edit the .env file with your database credentials:
     - DATABASE_HOST, DATABASE_PORT, DATABASE_NAME
     - DATABASE_USER, DATABASE_PASSWORD
     - SECRET_KEY (generate with: openssl rand -hex 32)
  
  2. Create the PostgreSQL database:
     CREATE DATABASE woms_db;
  
  3. Activate the virtual environment:
     Windows:  .\\venv\\Scripts\\activate
     Linux:    source venv/bin/activate
  
  4. Initialize the database:
     python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"
  
  5. Start the development server:
     uvicorn app.main:app --reload
  
  6. Open API documentation:
     http://localhost:8000/docs
  
  Happy coding! 🚀
    """)


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="WOMS Setup Script")
    parser.add_argument("--db-only", action="store_true", help="Only initialize database")
    parser.add_argument("--deps-only", action="store_true", help="Only install dependencies")
    args = parser.parse_args()
    
    print_banner()
    
    if args.db_only:
        setup_environment_file()
        initialize_database()
        return
    
    if args.deps_only:
        if create_virtual_environment():
            install_dependencies()
        return
    
    # Full setup
    steps = [
        create_virtual_environment,
        install_dependencies,
        setup_environment_file,
    ]
    
    for step_func in steps:
        if not step_func():
            print_error("Setup failed. Please fix the errors and try again.")
            sys.exit(1)
    
    print_next_steps()


if __name__ == "__main__":
    main()
