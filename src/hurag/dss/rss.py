import aiomysql
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .. import conf, logger

_pool: aiomysql.Pool | None = None
_pool_lock = None

async def _get_lock():
    global _pool_lock
    if _pool_lock is None:
        import asyncio
        _pool_lock = asyncio.Lock()
    return _pool_lock

async def get_pool():
    global _pool
    lock = await _get_lock()

    async with lock:
        if _pool is None:
            _pool = await aiomysql.create_pool(
                host=conf.mariadb.host,
                port=conf.mariadb.port,
                user=conf.mariadb.user,
                password=conf.mariadb.password,
                db=conf.mariadb.database,
                autocommit=False,
            )
    return _pool

async def close_pool():
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

