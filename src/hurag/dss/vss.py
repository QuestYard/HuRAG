import warnings

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="google.protobuf.runtime_version",
)

import asyncio
from typing import Any
from collections.abc import Callable

from contextlib import asynccontextmanager
from functools import wraps
from pymilvus import AsyncMilvusClient

_clients: dict[str, AsyncMilvusClient] = {}
_clients_lock: asyncio.Lock = asyncio.Lock()


async def get_client(
    uri: str | None = None,
    token: str | None = None,
    db_name: str | None = None,
    client_name: str = "default",
) -> AsyncMilvusClient:
    """Get or create the Milvus client."""
    from .. import conf

    global _clients

    if client_name in _clients:
        return _clients[client_name]

    async with _clients_lock:
        if client_name in _clients:
            return _clients[client_name]
        _clients[client_name] = AsyncMilvusClient(
            uri=uri or conf.milvus.uri,
            token=token or conf.milvus.token,
            db_name=db_name or conf.milvus.db_name,
        )

    return _clients[client_name]


async def close_client(client_name: str | None = None) -> None:
    """Close the Milvus client."""
    global _clients
    if client_name:
        if client_name in _clients:
            client = _clients.pop(client_name)
            await client.close()
    else:
        for client in _clients.values():
            await client.close()
        _clients.clear()


@asynccontextmanager
async def lifespan():
    """Context manager to handle Milvus clients."""
    try:
        yield
    finally:
        await close_client()


def with_vdb(
    func=None,
    *,
    client_arg_name="client",
    client_name="default",
) -> Callable[..., Any]:
    """Decorator to provide a VSS client to the decorated function."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            kwargs[client_arg_name] = await get_client(client_name=client_name)
            return await func(*args, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


async def upsert(collection: str, data: list[dict], client_name: str = "default"):
    cli = await get_client(client_name=client_name)
    return await cli.upsert(collection_name=collection, data=data)


async def insert(collection: str, data: list[dict], client_name: str = "default"):
    cli = await get_client(client_name=client_name)
    return await cli.insert(collection_name=collection, data=data)


async def query(
    collection_name: str,
    filter: str = "",
    output_fields: list[str] | None = None,
    client_name: str = "default",
    **kwargs,
):
    cli = await get_client(client_name=client_name)
    return await cli.query(
        collection_name=collection_name,
        filter=filter,
        output_fields=output_fields,
        **kwargs,
    )


async def search(
    collection_name: str,
    vecs: dict,
    scope: list | None = None,
    top_k: int = 50,
    rrf_k: float = 100,
    client_name: str = "default",
) -> dict[str, float]:
    """
    Perform hybrid search on collection 'collection_name'.

    Arguments:
        collection_name: str -- the collection to search inside of. must have
                two fields named 'dense_vec' and 'sparse_vec'
        vecs: the dict of query embeddings, as
                { "dense": dense_vector, "sparse": sparse_vector }
        scope: the list of ids that restricting the search scope, None if to
                search in the whole collection.
        top_k: default to 50
        rrf_k: default to 100

    Return:
        {id1: score1, id2: score2, ..., id_top_k: score_top_k}
    """
    from pymilvus import AnnSearchRequest, RRFRanker

    expr = "id IN {ids}" if scope else None
    expr_params = {"ids": scope} if scope else None
    dense_request = AnnSearchRequest(
        data=vecs["dense"],
        anns_field="dense_vec",
        limit=top_k * 2,
        expr=expr,
        expr_params=expr_params,
        param={"metric_type": "COSINE"},
    )
    sparse_request = AnnSearchRequest(
        data=vecs["sparse"],
        anns_field="sparse_vec",
        limit=top_k * 2,
        expr=expr,
        expr_params=expr_params,
        param={"metric_type": "IP"},
    )
    # `rrf_k` should be a float number, but the type hint of the argument `k` of
    # `pymilvus.RRFRanker` is mistaken for an 'int'.
    ranker = RRFRanker(rrf_k)  # type: ignore
    cli = await get_client(client_name=client_name)
    res = await cli.hybrid_search(
        collection_name=collection_name,
        reqs=[dense_request, sparse_request],
        ranker=ranker,
        limit=top_k,
        output_fields=["id"],
    )
    return {x["id"]: x["distance"] for x in res[0]}
