"""
Initialization script for the FastAPI blog application.
This script creates the database tables and sets up initial data.
"""

import asyncio
import sys
from pathlib import Path

# Add the fastapi_src directory to the path
sys.path.append(str(Path(__file__).parent))

from database.connection import create_tables, init_db_pool, close_db_pool
from core.config import settings

async def init_application():
    """Initialize the application database and tables"""
    print("Initializing FastAPI Blog Application...")
    
    try:
        # Initialize database connection pool
        await init_db_pool()
        print("✓ Database connection pool initialized")
        
        # Create tables
        await create_tables()
        print("✓ Database tables created/verified")
        
        print("✓ Application initialization completed successfully!")
        
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        sys.exit(1)
    finally:
        await close_db_pool()

if __name__ == "__main__":
    asyncio.run(init_application())
