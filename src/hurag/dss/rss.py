import aiomysql
import asyncio
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar
from contextlib import asynccontextmanager

from .. import conf

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

_pool: aiomysql.Pool | None = None
_pool_lock: asyncio.Lock | None = None

async def _get_lock() -> asyncio.Lock:
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock

async def get_pool() -> aiomysql.Pool:
    """Get or create the database connection pool."""
    global _pool

    if _pool is not None:
        return _pool

    lock = await _get_lock()
    async with lock:
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
    """Close the database connection pool. Only used with API lifespan."""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

@asynccontextmanager
async def lifespan(app=None):
    """Context manager to handle database pool lifecycle."""
    try:
        yield
    finally:
        await close_pool()

def with_rdb(
    func: Callable | None = None,
    *,
    connection_name: str = "connection",
    cursor_name: str = "cursor",
    dict_cursor: bool = False,
    ss_cursor: bool = False,
) -> Callable:
    """
    Decorator for injection of rss connection and cursor.

    Args:
        func:
            The function to be decorated.
        connection_name: optional, default "connection"
            The name of the connection argument to be injected.
        cursor_name: optional, default "cursor"
            The name of the cursor argument to be injected.
        dict_cursor: optional, default False
            Whether to use a dictionary cursor.
        ss_cursor: optional, default False
            Whether to use a server-side cursor.

    **Usage**:

    The most common usage is to inject connection and ordinary cursor with
    default names, ordinary cursor.

    There should be two arguments named "connection" and "cursor" in
    the decorated function.

    ```python
    @with_rdb
    async def my_function(connection, cursor, other_arg):
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Connection and cursor can also be injected into the decorated function
    as keyword arguments. 

    ```python
    @with_rdb
    async def my_function(other_arg, **kwargs):
        connection = kwargs['connection']
        cursor = kwargs['cursor']
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Or you can customize the names of the injected arguments.

    ```python
    @with_rdb(connection_name="conn", cursor_name="cur", dict_cursor=True)
    async def my_function(other_arg, **kwargs):
        connection = kwargs['conn']
        cursor = kwargs['cur']
        await cursor.execute("SELECT * FROM my_table")
        results = await cursor.fetchall()
        return results
    ```

    Type of cursor can also be specified. There are four types of cursor:

    - Ordinary cursor (default): `dict_cursor=False`, `ss_cursor=False`
    - Dictionary cursor: `dict_cursor=True`, `ss_cursor=False`
    - Server-side ordinary cursor: `dict_cursor=False`, `ss_cursor=True`
    - Server-side dictionary cursor: `dict_cursor=True`, `ss_cursor=True`

    **Caution**:

    - The decorated function *MUST* be asynchronous.
    - *DO NOT* close the connection or cursor in the decorated function.

    Returns:
        The decorated function.
    """
    def decorator(func: T)-> T:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            pool = await get_pool()
            connection = await pool.acquire()
            if dict_cursor:
                if ss_cursor:
                    cursor = await connection.cursor(aiomysql.SSDictCursor)
                else:
                    cursor = await connection.cursor(aiomysql.DictCursor)
            else:
                if ss_cursor:
                    cursor = await connection.cursor(aiomysql.SSCursor)
                else:
                    cursor = await connection.cursor()
            kwargs[connection_name] = connection
            kwargs[cursor_name] = cursor
            ret = await func(*args, **kwargs)
            await cursor.close()
            pool.release(connection)
            return ret
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator

async def query(statement: str, data: tuple = ()) -> list[tuple]:
    """
    Execute a SQL query statement (SELECT) and return all results.

    Args:
        statement:
            The SQL query statement to be executed.
        data:
            The data to be used in the query statement.

    Returns:
        A list of tuples representing the query results.
    """
    pool = await get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute(statement, data)
        ret = await cur.fetchall()
        return list(ret)

async def query_iter(statement: str, data: tuple = (), batch_size: int = 1000):
    """
    Execute a SQL query statement (SELECT) and yield results iteratively.
    Uses a server-side cursor to avoid loading all results into memory.

    Args:
        statement:
            The SQL query statement to be executed.
        data:
            The data to be used in the query statement.
        batch_size:
            The number of rows to fetch at a time. Default is 1000.

    Yields:
        A tuple representing a row in the query results.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.SSCursor) as cur:
            await cur.execute(statement, data)
            while True:
                rows = await cur.fetchmany(batch_size)
                if not rows:
                    break
                for row in rows:
                    yield row

async def dml(statement: str, data: tuple | list[tuple] | None = ()) -> int:
    """
    Execute a DML statement (INSERT, UPDATE, DELETE).
    
    Args:
        statement:
            The DML statement to be executed.
        data:
            The data to be used in the DML statement. If a list of tuples is
            provided, executemany() will be used.

    Returns:
        The number of affected rows.
    """
    pool = await get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        try:
            if data is not None and isinstance(data, list):
                await cur.executemany(statement, data)
            else:
                await cur.execute(statement, data or ())
            await conn.commit()

            return cur.rowcount
        except Exception as e:
            await conn.rollback()
            raise e

async def transact(
    statements: list[str],
    data: list[tuple | list[tuple] | None] | None = None,
) -> int:
    """
    Execute multiple DML statements in a transaction.
    Args:
        statements:
            A list of DML statements to be executed.
        data:
            A list of data tuples or list of tuples corresponding to each
            statement. If None, empty tuples will be used. If the length of
            data is less than statements, the remaining statements will use
            empty tuples.

    Returns:
        The total number of affected rows.
    """
    pool = await get_pool()
    async with pool.acquire() as conn, conn.cursor() as cur:
        if data is None:
            data = [()] * len(statements)
        ns = len(statements)
        nd = len(data)
        if ns > nd:
            data = data.extend([()] * (ns - nd))
        try:
            rowcount = 0
            for st, dt in zip(statements[:ns], data[:ns]):
                if dt is not None and isinstance(dt, list):
                    await cur.executemany(st, dt)
                else:
                    await cur.execute(st, dt or ())
                rowcount += cur.rowcount
            await conn.commit()

            return rowcount
        except Exception as e:
            await conn.rollback()
            raise e

