"""
Auto-Initialize Database
Automatically creates database and tables on application startup using schema.sql.
"""
import sys
import os
import asyncio
import aiomysql
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load appropriate .env file based on environment
env_type = os.getenv("ENV", "production")
if env_type == "local":
    logger.info("🔧 Loading local environment configuration (.env.local)")
    load_dotenv(".env.local")
else:
    logger.info("☁️  Loading production/default configuration")
    load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "voice_user")
DB_PASS = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "voice_meta")


async def init_database():
    """
    Initialize database: create if missing, then apply schema.sql.
    """
    logger.info("=" * 60)
    logger.info("DATABASE INITIALIZATION")
    logger.info("=" * 60)
    
    conn = None
    try:
        # Step 1: Connect as root to create database if needed
        root_password = os.getenv("MYSQL_ROOT_PASSWORD", os.getenv("DB_PASSWORD", "db@1234"))
        logger.info(f"1. Connecting to MySQL server at {DB_HOST}:{DB_PORT} as root...")
        
        try:
            conn = await aiomysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user="root",
                password=root_password,
                autocommit=True
            )
            logger.info("✅ Connected to MySQL server as root")
        except Exception as e:
            # If root fails, try with the app user (maybe they already have permissions)
            logger.warning(f"⚠️  Root connection failed, trying with {DB_USER}...")
            try:
                conn = await aiomysql.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASS,
                    autocommit=True
                )
                logger.info(f"✅ Connected as {DB_USER}")
            except Exception as e2:
                logger.error(f"❌ Failed to connect as {DB_USER} as well: {e2}")
                raise e

        # Step 2: Create database if it doesn't exist
        cursor = await conn.cursor()
        logger.info(f"2. Ensuring database '{DB_NAME}' exists...")
        await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        logger.info(f"✅ Database '{DB_NAME}' is ready")
        
        # Create app user if it doesn't exist (only if we're connected as root)
        try:
            await cursor.execute(f"CREATE USER IF NOT EXISTS '{DB_USER}'@'%' IDENTIFIED BY '{DB_PASS}'")
            await cursor.execute(f"GRANT ALL PRIVILEGES ON {DB_NAME}.* TO '{DB_USER}'@'%'")
            await cursor.execute("FLUSH PRIVILEGES")
            logger.info(f"✅ User '{DB_USER}' configured with privileges")
        except Exception:
            # User might already exist or we're not root
            pass
        
        await cursor.close()
        conn.close()
        
        # Step 3: Apply Schema (Tables)
        logger.info(f"3. Applying Schema from data/db/schema.sql...")
        
        # Reconnect to the specific database
        conn = await aiomysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            autocommit=True
        )
        cursor = await conn.cursor()
        
        # Read schema file
        try:
            with open("data/db/schema.sql", "r", encoding="utf-8") as f:
                schema_sql = f.read()
        except FileNotFoundError:
            logger.error("❌ Error: data/db/schema.sql not found!")
            return False

        # Execute statements
        statements = schema_sql.split(";")
        for stmt in statements:
            if stmt.strip():
                try:
                    await cursor.execute(stmt)
                except Exception as e:
                    logger.warning(f"⚠️  Warning executing statement: {stmt[:50]}... -> {e}")
        
        logger.info(f"✅ Schema applied successfully (Tables ensured)")
        
        # Verify tables
        await cursor.execute("SHOW TABLES")
        tables = await cursor.fetchall()
        logger.info(f"📊 Current Tables: {[t[0] for t in tables]}")

        await cursor.close()
        conn.close()
        
        logger.info("=" * 60)
        logger.info("DATABASE READY!")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {type(e).__name__}")
        logger.error(f"Error: {str(e)}")
        if conn:
            try:
                conn.close()
            except:
                pass
        return False



if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)
