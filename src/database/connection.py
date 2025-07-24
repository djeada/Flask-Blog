import aiomysql
from core.config import settings
from typing import AsyncGenerator

# Global connection pool
connection_pool = None

async def init_db_pool():
    """Initialize database connection pool"""
    global connection_pool
    connection_pool = await aiomysql.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_NAME,
        autocommit=False,
        cursorclass=aiomysql.DictCursor,
        minsize=1,
        maxsize=10
    )

async def close_db_pool():
    """Close database connection pool"""
    global connection_pool
    if connection_pool:
        connection_pool.close()
        await connection_pool.wait_closed()

async def get_database() -> AsyncGenerator[aiomysql.Connection, None]:
    """Get database connection from pool"""
    global connection_pool
    if not connection_pool:
        await init_db_pool()
    
    async with connection_pool.acquire() as conn:
        try:
            yield conn
        finally:
            pass  # Connection automatically returned to pool

async def create_tables():
    """Create database tables if they don't exist"""
    async for db in get_database():
        cursor = await db.cursor()
        
        # Users table
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                username VARCHAR(25) UNIQUE NOT NULL,
                email VARCHAR(50) NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Articles table
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                body TEXT NOT NULL,
                author VARCHAR(25) NOT NULL,
                image VARCHAR(255) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (author) REFERENCES users(username) ON DELETE CASCADE
            )
        """)
        
        await db.commit()
        await cursor.close()
        break  # Only need to create tables once
