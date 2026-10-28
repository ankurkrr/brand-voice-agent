
import asyncio
from data.db.session import get_pool

async def migrate():
    print("Checking 'voice_profiles_machine' for 'brand_id' column...")
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            # Check if column exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'voice_profiles_machine' 
                    AND column_name = 'brand_id'
                )
            """)
            
            if not exists:
                print("Column 'brand_id' missing. Adding it now...")
                await conn.execute("""
                    ALTER TABLE voice_profiles_machine 
                    ADD COLUMN brand_id CHAR(36) NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
                """)
                # Note: We set a default to existing rows won't fail NOT NULL constraint. 
                # Ideally we would backfill it from voice_profiles_human, but for now this enables the schema.
                print("✓ Column 'brand_id' added successfully.")
                
                # Create index
                await conn.execute("CREATE INDEX IF NOT EXISTS idx_vp_machine_brand ON voice_profiles_machine(brand_id)")
                print("✓ Index added.")
            else:
                print("✓ Column 'brand_id' already exists.")
                
        except Exception as e:
            print(f"Migration Error: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(migrate())
