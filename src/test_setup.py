"""
Simple test script to validate FastAPI blog application
"""

import asyncio
import sys
from pathlib import Path

# Add the fastapi_src directory to the path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_database, init_db_pool, close_db_pool
from core.security import get_password_hash, verify_password

async def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    try:
        await init_db_pool()
        async for db in get_database():
            cursor = await db.cursor()
            await cursor.execute("SELECT 1")
            result = await cursor.fetchone()
            await cursor.close()
            assert result[0] == 1
            print("✓ Database connection successful")
            break
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    finally:
        await close_db_pool()
    return True

def test_password_hashing():
    """Test password hashing functionality"""
    print("Testing password hashing...")
    try:
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Verify correct password
        assert verify_password(password, hashed) == True
        
        # Verify incorrect password
        assert verify_password("wrong_password", hashed) == False
        
        print("✓ Password hashing works correctly")
        return True
    except Exception as e:
        print(f"✗ Password hashing failed: {e}")
        return False

async def test_table_creation():
    """Test that tables can be created"""
    print("Testing table creation...")
    try:
        from database.connection import create_tables
        await init_db_pool()
        await create_tables()
        print("✓ Tables created/verified successfully")
        return True
    except Exception as e:
        print(f"✗ Table creation failed: {e}")
        return False
    finally:
        await close_db_pool()

async def run_tests():
    """Run all tests"""
    print("FastAPI Blog Application Tests")
    print("=" * 40)
    
    tests = [
        test_password_hashing(),
        await test_database_connection(),
        await test_table_creation()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 40)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to run.")
        return True
    else:
        print("❌ Some tests failed. Please check your configuration.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
