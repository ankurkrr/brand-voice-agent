import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
root_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(root_dir / ".env")

from data.db.session import get_pool


async def apply_005():
    pool = await get_pool()
    migration_file = root_dir / "data" / "db" / "migrations" / "005_create_token_usage_logs.sql"
    
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()
        
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    print(f"Executing: {stmt[:50]}...")
                    await cur.execute(stmt)
        await conn.commit()
    print("Migration 005 applied successfully.")


if __name__ == "__main__":
    asyncio.run(apply_005())
