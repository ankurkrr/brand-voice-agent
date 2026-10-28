import asyncio
from data.db.session import get_pool

async def apply_migration():
    print("Applying migration 004...")
    pool = await get_pool()
    
    sql = """
    CREATE TABLE IF NOT EXISTS persona_dimensional_cache (
        id CHAR(36) PRIMARY KEY,
        content_hash VARCHAR(64) NOT NULL,
        llm_model VARCHAR(50) NOT NULL,
        llm_temperature FLOAT DEFAULT 0.0,
        dimensions JSON NOT NULL,
        scores JSON NOT NULL,
        text_preview TEXT,
        token_count INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        UNIQUE KEY idx_hash_model (content_hash, llm_model),
        INDEX idx_created (created_at)
    );
    """
    
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(sql)
            await conn.commit()
    
    print("Migration 004 applied successfully.")

if __name__ == "__main__":
    asyncio.run(apply_migration())
