"""
Database Connection Pool — Cloud Run + Cloud SQL (Private IP)

Single connection strategy: Private IP via VPC connector.
SSL enabled (CloudSQL ENCRYPTED_ONLY). No unix socket. No dual-mode branching.

Required environment variables:
    DB_HOST     — Cloud SQL Private IP (e.g. 10.x.x.x)
    DB_USER     — Database username
    DB_PASSWORD — Database password
    DB_NAME     — Database name
    DB_PORT     — (Optional) Database port, defaults to 3306
"""

import os
import ssl as _ssl
import asyncio
import logging
from typing import Optional

import aiomysql

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (read once at module load)
# ---------------------------------------------------------------------------
DB_HOST: Optional[str] = os.getenv("DB_HOST")
DB_USER: Optional[str] = os.getenv("DB_USER")
DB_PASS: Optional[str] = os.getenv("DB_PASSWORD")
DB_NAME: Optional[str] = os.getenv("DB_NAME")
DB_PORT: int = int(os.getenv("DB_PORT", "3306"))

# ---------------------------------------------------------------------------
# Pool singleton + lock for async-safe initialisation
# ---------------------------------------------------------------------------
_pool: Optional[aiomysql.Pool] = None
_pool_lock: asyncio.Lock = asyncio.Lock()


def _validate_db_config() -> None:
    """
    Validate all required database environment variables.
    Raises RuntimeError immediately if any are missing (fail-fast).
    """
    required = {
        "DB_HOST": DB_HOST,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASS,
        "DB_NAME": DB_NAME,
    }
    missing = [k for k, v in required.items() if not v]

    if missing:
        msg = f"Missing required database environment variables: {', '.join(missing)}"
        logger.error(f"[DB] {msg}")
        raise RuntimeError(msg)


async def get_pool() -> aiomysql.Pool:
    """
    Get or create the database connection pool (async-safe singleton).

    Uses an asyncio.Lock to prevent race conditions when multiple
    coroutines call get_pool() concurrently during startup.

    Returns:
        aiomysql.Pool — the active connection pool

    Raises:
        RuntimeError — if configuration is invalid or connection fails
    """
    global _pool

    if _pool is not None and not _pool._closed:
        return _pool

    async with _pool_lock:
        # Double-check after acquiring lock (another coroutine may have created it)
        if _pool is not None and not _pool._closed:
            return _pool

        # Fail fast on missing config
        _validate_db_config()

        try:
            logger.info(f"[DB] Connecting via Private IP: {DB_HOST}:{DB_PORT}")
            # SSL logic: detailed handling
            use_ssl = True
            ssl_ctx = None
            
            # Disable SSL for localhost (Cloud SQL Proxy or Local DB)
            if DB_HOST in ["127.0.0.1", "localhost", "host.docker.internal"]:
                 use_ssl = False
                 logger.info("[DB] Running on localhost proxy - SSL Disabled")
            else:
                 ssl_ctx = _ssl.create_default_context()
                 ssl_ctx.check_hostname = False
                 ssl_ctx.verify_mode = _ssl.CERT_NONE

            _pool = await aiomysql.create_pool(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                db=DB_NAME,
                minsize=1,
                maxsize=10,
                autocommit=True,
                connect_timeout=10,
                ssl=ssl_ctx if use_ssl else None,
            )
            logger.info("[DB] Connection pool created successfully")
        except Exception as e:
            error_msg = (
                f"Failed to create database connection pool: "
                f"{type(e).__name__}: {e}"
            )
            logger.error(f"[DB] {error_msg}")
            raise RuntimeError(error_msg) from e

    return _pool


async def test_connection() -> bool:
    """
    Run a lightweight connectivity test (SELECT 1).

    Returns True on success, False on failure. Never raises.
    Intended for startup probes and /ready endpoints.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
                if result and result[0] == 1:
                    logger.info("[DB] Connection test passed (SELECT 1)")
                    return True
        return False
    except Exception as e:
        logger.error(f"[DB] Connection test failed: {type(e).__name__}: {e}")
        return False


async def close_pool() -> None:
    """
    Gracefully close the connection pool.
    Safe to call multiple times (idempotent).
    """
    global _pool

    if _pool is not None and not _pool._closed:
        _pool.close()
        await _pool.wait_closed()
        logger.info("[DB] Connection pool closed")
        _pool = None
