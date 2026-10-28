# services/db/test_db.py
import asyncpg
import os

TEST_DB_URL = os.getenv("TEST_DB_URL", "postgres://postgres:postgres@localhost:5556/testdb")

_pool = None

async def get_test_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(TEST_DB_URL)
    return _pool
