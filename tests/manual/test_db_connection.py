"""
Database Connection Test Script
Tests if the backend can successfully connect to MySQL database
"""
import asyncio
import os
from dotenv import load_dotenv
from data.db.session import get_pool

load_dotenv()

async def test_connection():
    """Test database connection and basic query"""
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    
    # Print configuration
    print(f"\n📋 Configuration:")
    print(f"   Host: {os.getenv('DB_HOST', '127.0.0.1')}")
    print(f"   Port: {os.getenv('DB_PORT', '3306')}")
    print(f"   Database: {os.getenv('DB_NAME', 'NOT SET')}")
    print(f"   User: {os.getenv('DB_USER', 'NOT SET')}")
    
    try:
        print("\n🔌 Attempting to create connection pool...")
        pool = await get_pool()
        print("✅ Connection pool created successfully!")
        
        print("\n🔍 Testing database query...")
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Test 1: Check database version
                await cursor.execute("SELECT VERSION()")
                version = await cursor.fetchone()
                print(f"✅ MySQL Version: {version[0]}")
                
                # Test 2: Check if tables exist
                await cursor.execute("SHOW TABLES")
                tables = await cursor.fetchall()
                print(f"\n✅ Found {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table[0]}")
                
                # Test 3: Check if split tables exist
                split_tables = ['voice_profiles_human', 'voice_profiles_machine', 
                               'content_briefs_human', 'content_briefs_machine']
                await cursor.execute("SHOW TABLES")
                existing_tables = [t[0] for t in await cursor.fetchall()]
                
                print(f"\n🔧 Split Table Status:")
                for table in split_tables:
                    status = "✅ EXISTS" if table in existing_tables else "❌ MISSING"
                    print(f"   {table}: {status}")
                
                # Test 4: Check autocommit status
                await cursor.execute("SELECT @@autocommit")
                autocommit = await cursor.fetchone()
                print(f"\n⚙️  Autocommit Status: {autocommit[0]} (1 = enabled)")
                
                # Test 5: Count records in each table
                print(f"\n📊 Record Counts:")
                for table in ['brands', 'voice_profiles_human', 'content_briefs_human']:
                    if table in existing_tables:
                        await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = await cursor.fetchone()
                        print(f"   {table}: {count[0]} records")
        
        print("\n" + "=" * 60)
        print("✅ DATABASE CONNECTION TEST PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ DATABASE CONNECTION TEST FAILED!")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'pool' in locals():
            pool.close()
            await pool.wait_closed()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
