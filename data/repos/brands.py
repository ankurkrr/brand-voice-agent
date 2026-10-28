# data/repos/brands.py

from data.db.session import get_pool
import uuid

class BrandsRepo:
    """
    Repository for Brand operations - MySQL/aiomysql version.
    """

    @staticmethod
    async def create_brand(name: str):
        print(f"[BrandsRepo] Creating brand: {name}")
        pool = await get_pool()
        brand_id = str(uuid.uuid4())
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO brands (id, brand_id, name)
                    VALUES (%s, %s, %s)
                    """,
                    (brand_id, brand_id, name)
                )
                # No explicit commit - pool has autocommit=True
                
                # Fetch the inserted row
                await cursor.execute(
                    "SELECT * FROM brands WHERE brand_id = %s",
                    (brand_id,)
                )
                row = await cursor.fetchone()
                columns = [desc[0] for desc in cursor.description]
                result = dict(zip(columns, row))
                print(f"[BrandsRepo] Brand created: {result}")
                return result

    @staticmethod
    async def create_brand_with_id(brand_id: str, name: str):
        """Create brand with specific ID (for parallel execution)"""
        print(f"[BrandsRepo] Creating brand with ID {brand_id}: {name}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO brands (id, brand_id, name)
                    VALUES (%s, %s, %s)
                    """,
                    (brand_id, brand_id, name)
                )
                # No explicit commit - pool has autocommit=True
                
                # Fetch the inserted row
                await cursor.execute(
                    "SELECT * FROM brands WHERE brand_id = %s",
                    (brand_id,)
                )
                row = await cursor.fetchone()
                columns = [desc[0] for desc in cursor.description]
                result = dict(zip(columns, row))
                print(f"[BrandsRepo] Brand created with custom ID: {result}")
                return result

    @staticmethod
    async def get_brand_by_name(name: str):
        print(f"[BrandsRepo] Fetching brand by name: {name}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM brands WHERE name = %s LIMIT 1",
                    (name,)
                )
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    print(f"[BrandsRepo] Brand found: {result}")
                    return result
                print("[BrandsRepo] Brand not found")
                return None

    @staticmethod
    async def get_brand_by_id(brand_id: str):
        print(f"[BrandsRepo] Fetching brand by ID: {brand_id}")
        pool = await get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM brands WHERE brand_id = %s LIMIT 1",
                    (brand_id,)
                )
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    print(f"[BrandsRepo] Brand found: {result}")
                    return result
                print("[BrandsRepo] Brand not found")
                return None
