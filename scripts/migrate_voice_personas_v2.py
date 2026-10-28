
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from data.db.session import get_pool

async def migrate_db():
    print("Starting voice_personas schema migration...")
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Check if columns exist
            await cursor.execute("SHOW COLUMNS FROM voice_personas")
            columns = [row[0] for row in await cursor.fetchall()]
            
            alter_stmts = []
            
            if "persona_key" not in columns:
                alter_stmts.append("ADD COLUMN persona_key VARCHAR(50) DEFAULT NULL")
            
            if "persona_origin" not in columns:
                alter_stmts.append("ADD COLUMN persona_origin VARCHAR(20) DEFAULT 'SYSTEM'")
                
            if "persona_overlay_prompt" not in columns:
                alter_stmts.append("ADD COLUMN persona_overlay_prompt TEXT DEFAULT NULL")
                
            if "persona_scope" not in columns:
                alter_stmts.append("ADD COLUMN persona_scope VARCHAR(20) DEFAULT 'OVERLAY'")
                
            if "persona_version" not in columns:
                alter_stmts.append("ADD COLUMN persona_version INT DEFAULT 1")
            
            if alter_stmts:
                sql = f"ALTER TABLE voice_personas {', '.join(alter_stmts)}"
                print(f"Executing: {sql}")
                await cursor.execute(sql)
                await conn.commit()
                print("Migration successful.")
            else:
                print("All columns already exist. No changes needed.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate_db())
