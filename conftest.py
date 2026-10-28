import pytest
import asyncio


@pytest.fixture(scope="session", autouse=True)
def cleanup_db_pools():
    yield
    # cleanup
    from data.db import session
    if session._pool:
        try:
            asyncio.run(session._pool.close())
        except:
            pass
