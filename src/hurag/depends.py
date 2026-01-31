from __future__ import annotations
from typing import Annotated, TYPE_CHECKING

if TYPE_CHECKING:
    import aiomysql
    import pymilvus
    import openai

from fastapi import Depends

# --- MySQL/MariaDB CONNECTION POOL DEPENDENCY ---
#
# Usage 1:
# Get the default pool named "default" which connects to the default HuRAG rss
# database configured in `hurag.yaml`, `mariadb` section.
#
# Sample 1:
# ```python
# from hurag.depends import HuragRdbPoolDep
#
# @app.get("/db1")
# async def _db1(pool: HuragRdbPoolDep):
#     async with pool.acquire() as conn, conn.cursor() as cur:
#         await cur.execute("SELECT COUNT(*) FROM documents")
#         ret = await cur.fetchall()
#         return { "number_of_documents": ret[0][0] }
# ```
#
# Usage 2:
# Get a pool connects to some customed database other than the configured HuRAG rss
# database.
# The pool name must be provided and cannot be "default".
#
# Sample 2:
# ```python
# from hurag.depends import rdb_pool
# from fastapi import Depends
# from typing import Annotated
# 
# db2_params = {
#     "host": "localhost",
#     "port": 3306,
#     "user": "username",
#     "password": "password",
#     "db": "another_db",
#     "pool_name": "another_pool",
# }
#
# @app.get("/db2")
# async def _db2(pool: Annotated["aiomysql.Pool", Depends(rdb_pool(**db2_params))]):
#     async with pool.acquire() as conn, conn.cursor() as cur:
#         await cur.execute("SELECT COUNT(*) FROM documents")
#         ret = await cur.fetchall()
#         return { "number_of_documents": ret[0][0] }
# ```

def rdb_pool(
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    db: str | None = None,
    pool_name: str = "default",
):
    async def _get_pool() -> aiomysql.Pool:
        from .dss import rss
        return await rss.get_pool(host, port, user, password, db, pool_name)
    return _get_pool

HuragRdbPoolDep = Annotated["aiomysql.Pool", Depends(rdb_pool())]

# --- MySQL/MariaDB CONNECTION DEPENDENCY ---
#
# This is a more recommended dependancy item than the connection pool denpendcy.
# You should always choose to depend a connection rather to a pool unless there is
# complex or parallel transaction.
#
# Usage 1:
# Get a connection from the default pool named "default" which connects to the default
# HuRAG rss database configured in `hurag.yaml`, `mariadb` section.
#
# Sample 1:
# ```python
# from hurag.depends import HuragRdbConnectionDep
#
# @app.get("/db1")
# async def _db1(conn: HuragRdbConnectionDep):
#     async with conn.cursor() as cur:
#         await cur.execute("SELECT COUNT(*) FROM documents")
#         ret = await cur.fetchall()
#         return { "number_of_documents": ret[0][0] }
# ```
#
# Usage 2:
# Get a connection from the the customed pool connects to some customed database.
# The pool name must be provided and cannot be "default".
#
# Sample 2:
# ```python
# from hurag.depends import rdb_connection
# from fastapi import Depends
# from typing import Annotated
# 
# db2_params = {
#     "host": "localhost",
#     "port": 3306,
#     "user": "username",
#     "password": "password",
#     "db": "another_db",
#     "pool_name": "another_pool",
# }
#
# @app.get("/db2")
# async def _db2(
#     conn: Annotated["aiomysql.Connection", Depends(rdb_connection(**db2_params))]
# ):
#     async with conn.cursor() as cur:
#         await cur.execute("SELECT COUNT(*) FROM documents")
#         ret = await cur.fetchall()
#         return { "number_of_documents": ret[0][0] }
# ```

def rdb_connection(
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    db: str | None = None,
    pool_name: str = "default",
):
    async def _acquire() -> aiomysql.Connection:
        from .dss import rss
        pool = await rss.get_pool(host, port, user, password, db, pool_name)
        async with pool.acquire() as conn:
            yield conn
    return _acquire

HuragRdbConnectionDep = Annotated["aiomysql.Connection", Depends(rdb_connection())]

# --- Milvus ASYNC CLIENT DEPENDENCY ---
#
# Usage 1:
# Get a client named "default" which connects to the default HuRAG vss database
# configured in `hurag.yaml`, `milvus` section.
#
# Sample 1:
# ```python
# from hurag.depends import HuragVdbClientDep
#
# @app.get("/vdb1")
# async def _vdb1(cli: HuragVdbClientDep):
#     resp = await cli.list_collections()
#     return { "collections": resp }
# ```
#
# Usage 2:
# Get a client with customed name and connects to some customed milvus database.
# The client name must be provided and cannot be "default".
#
# Sample 2:
# ```python
# from hurag.depends import vdb_client
# from fastapi import Depends
# from typing import Annotated
# 
# vdb2_params = {
#     "uri": "http://localhost:19530",
#     "token": "user:password",
#     "db_name": "another_db",
#     "client_name": "another_client",
# }
#
# @app.get("/db2")
# async def _db2(
#     cli: Annotated["pymilvus.AsyncMilvusClient", Depends(vdb_client(**vdb2_params))]
# ):
#     resp = await cli.list_collections()
#     return { "collections": resp }
# ```

def vdb_client(
    uri: str | None = None,
    token: str | None = None,
    db_name: str | None = None,
    client_name: str = "default",
):
    async def _get_client() -> pymilvus.AsyncMilvusClient:
        from .dss import vss
        client = await vss.get_client(uri, token, db_name, client_name)
        return client
    return _get_client

HuragVdbClientDep = Annotated["pymilvus.AsyncMilvusClient", Depends(vdb_client())]

# --- OpenAI ASYNC CLIENT DEPENDENCY ---

def openai_client(
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 180.0,
    max_retries: int = 3,
    client_name: str = "generation",
):
    async def _get_openai() -> openai.AsyncOpenAI:
        from .llm import get_oa_client
        client = await get_oa_client(
            base_url, api_key, timeout, max_retries, client_name
        )
        return client
    return _get_openai

HuragGenerationClient = Annotated["openai.AsyncOpenAI", Depends(openai_client())]
HuragExtractionClient = Annotated[
    "openai.AsyncOpenAI", Depends(openai_client(client_name="extraction"))
]


async def generation_model_name() -> str:
    import os
    from . import conf
    return os.getenv(f"{conf.llm.generation}_MODEL")

async def extraction_model_name() -> str:
    import os
    from . import conf
    return os.getenv(f"{conf.llm.extraction}_MODEL")

HuragGenerationModel = Annotated[str, Depends(generation_model_name)]
HuragExtractionModel = Annotated[str, Depends(extraction_model_name)]

# --- Exposed Items ---

__all__ = [
    "HuragRdbPoolDep",
    "HuragRdbConnectionDep",
    "HuragVdbClientDep",
    "HuragGenerationClient",
    "HuragExtractionClient",
    "HuragGenerationModel",
    "HuragExtractionModel",
]
