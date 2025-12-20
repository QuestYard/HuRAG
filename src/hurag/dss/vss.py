import warnings
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="google.protobuf.runtime_version"
)

from contextlib import asynccontextmanager
from functools import wraps
from pymilvus import (
    AsyncMilvusClient,
    AnnSearchRequest,
    RRFRanker,
)
from typing import Callable, Any, Coroutine, TypeVar

from .. import conf

T = TypeVar("T", bound=Callable[..., Coroutine[Any, Any, Any]])

@asynccontextmanager
async def client():
    _cli = None
    try:
        _cli = AsyncMilvusClient(
            uri = conf.milvus.uri,
            token = conf.milvus.token,
            db_name = conf.milvus.db_name,
        )
        yield _cli
    finally:
        _cli and await _cli.close()

def with_vdb(
    func: T | None = None,
    *,
    client_name: str = "client",
) -> Callable[..., Any]:
    """Decorator to provide a VSS client to the decorated function."""
    # if func is None:
        # return lambda f: with_vdb(f, client_name=client_name)
    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _cli = AsyncMilvusClient(
                uri = conf.milvus.uri,
                token = conf.milvus.token,
                db_name = conf.milvus.db_name,
            )
            kwargs[client_name] = _cli
            ret = await func(*args, **kwargs)
            _cli and await _cli.close()
            return ret
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator

async def upsert(collection: str, data: list[dict]):
    async with client() as cli:
        res = await cli.upsert(collection_name=collection, data=data)
    return res

async def insert(collection: str, data: list[dict]):
    async with client() as cli:
        res = await cli.insert(collection_name=collection, data=data)
    return res

async def query(
    collection_name: str,
    filter: str = "",
    output_fields: list[str] | None = None,
    **kwargs,
):
    async with client() as cli:
        results = await cli.query(
            collection_name = collection_name,
            filter = filter,
            output_fields = output_fields,
            **kwargs,
        )
    return results

async def search(
    collection_name: str,
    vecs: dict,
    scope: list|None=None,
    top_k: int=50,
    rrf_k: float=100,
)-> dict[str, float]:
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
    expr = "id IN {ids}" if scope else None
    expr_params = {"ids": scope} if scope else None
    dense_request = AnnSearchRequest(
        data=vecs["dense"],
        anns_field="dense_vec",
        limit=top_k*2,
        expr=expr,
        expr_params=expr_params,
        param={"metric_type": "COSINE"}
    )
    sparse_request = AnnSearchRequest(
        data=vecs["sparse"],
        anns_field="sparse_vec",
        limit=top_k*2,
        expr=expr,
        expr_params=expr_params,
        param={"metric_type": "IP"}
    )
    ranker = RRFRanker(rrf_k)
    async with client() as cli:
        res = await cli.hybrid_search(
            collection_name=collection_name,
            reqs=[dense_request, sparse_request],
            ranker=ranker,
            limit = top_k,
            output_fields=["id"],
        )
    return {x["id"]: x["distance"] for x in res[0]}


