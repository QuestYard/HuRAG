import warnings

from aiomysql import connect
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
    MilvusClient,
    RRFRanker,
    DataType,
)
from typing import Callable

from .. import conf

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
    func: Callable | None = None,
    *,
    client_name: str = "client",
) -> Callable:
    """Decorator to provide a VSS client to the decorated function."""
    if func is None:
        return lambda f: with_vdb(f, client_name=client_name)

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
# 
# def init_vss():
#     with connect() as cli:
#         if cli.has_collection("chunks"):
#             cli.drop_collection("chunks")
#         # create chunks collection
#         schema = MilvusClient.create_schema(
#             enable_dynamic_field = False,
#             description = "dense and sparse vectors of chunks"
#         )
#         schema.add_field(
#             field_name="id",
#             datatype=DataType.VARCHAR,
#             max_length=36,
#             is_primary=True,
#         )
#         schema.add_field(
#             field_name="dense_vec",
#             datatype=DataType.FLOAT_VECTOR,
#             dim=1024,
#         )
#         schema.add_field(
#             field_name="sparse_vec",
#             datatype=DataType.SPARSE_FLOAT_VECTOR,
#         )
#         schema.add_field(
#             field_name="doc_id",
#             datatype=DataType.VARCHAR,
#             max_length=36,
#         )
#         index_params = cli.prepare_index_params()
#         index_params.add_index(
#             field_name="dense_vec",
#             index_name="dense_idx",
#             index_type="AUTOINDEX",
#             metric_type="COSINE"
#         )
#         index_params.add_index(
#             field_name="sparse_vec",
#             index_name="sparse_idx",
#             index_type="AUTOINDEX",
#             metric_type="IP"
#         )
#         index_params.add_index(
#             field_name="doc_id",
#             index_name="doc_idx"
#         )
#         cli.create_collection(
#             collection_name="chunks",
#             schema=schema,
#             index_params=index_params
#         )
#         # create kg collections
#         if cli.has_collection("nodes"):
#             cli.drop_collection("nodes")
#         if cli.has_collection("edges"):
#             cli.drop_collection("edges")
#         schema = MilvusClient.create_schema(
#             enable_dynamic_field = False,
#             description = "dense and sparse vectors of entities"
#         )
#         schema.add_field(
#             field_name="id",
#             datatype=DataType.VARCHAR,
#             max_length=36,
#             is_primary=True,
#         )
#         schema.add_field(
#             field_name="dense_vec",
#             datatype=DataType.FLOAT_VECTOR,
#             dim=1024,
#         )
#         schema.add_field(
#             field_name="sparse_vec",
#             datatype=DataType.SPARSE_FLOAT_VECTOR,
#         )
#         index_params = cli.prepare_index_params()
#         index_params.add_index(
#             field_name="dense_vec",
#             index_name="dense_idx",
#             index_type="AUTOINDEX",
#             metric_type="COSINE"
#         )
#         index_params.add_index(
#             field_name="sparse_vec",
#             index_name="sparse_idx",
#             index_type="AUTOINDEX",
#             metric_type="IP"
#         )
#         cli.create_collection(
#             collection_name="nodes",
#             schema=schema,
#             index_params=index_params
#         )
#         schema = MilvusClient.create_schema(
#             enable_dynamic_field = False,
#             description = "dense and sparse vectors of relation"
#         )
#         schema.add_field(
#             field_name="id",
#             datatype=DataType.VARCHAR,
#             max_length=36,
#             is_primary=True,
#         )
#         schema.add_field(
#             field_name="dense_vec",
#             datatype=DataType.FLOAT_VECTOR,
#             dim=1024,
#         )
#         schema.add_field(
#             field_name="sparse_vec",
#             datatype=DataType.SPARSE_FLOAT_VECTOR,
#         )
#         index_params = cli.prepare_index_params()
#         index_params.add_index(
#             field_name="dense_vec",
#             index_name="dense_idx",
#             index_type="AUTOINDEX",
#             metric_type="COSINE"
#         )
#         index_params.add_index(
#             field_name="sparse_vec",
#             index_name="sparse_idx",
#             index_type="AUTOINDEX",
#             metric_type="IP"
#         )
#         cli.create_collection(
#             collection_name="edges",
#             schema=schema,
#             index_params=index_params
#         )
# 
# def search(
#     collection_name: str,
#     vecs: dict,
#     scope: list|None=None,
#     top_k: int=50,
#     rrf_k: float=100,
# )-> dict[str, float]:
#     """
#     Perform hybrid search on collection 'collection_name'.
# 
#     Arguments:
#         collection_name: str -- the collection to search inside of. must have
#                 two fields named 'dense_vec' and 'sparse_vec'
#         vecs: the dict of query embeddings, as
#                 { "dense": dense_vector, "sparse": sparse_vector }
#         scope: the list of ids that restricting the search scope, None if to
#                 search in the whole collection.
#         top_k: default to 50
#         rrf_k: default to 100
# 
#     Return:
#         {id1: score1, id2: score2, ..., id_top_k: score_top_k}
#     """
#     expr = "id IN {ids}" if scope else None
#     expr_params = {"ids": scope} if scope else None
#     dense_request = AnnSearchRequest(
#         data=vecs["dense"],
#         anns_field="dense_vec",
#         limit=top_k*2,
#         expr=expr,
#         expr_params=expr_params,
#         param={"metric_type": "COSINE"}
#     )
#     sparse_request = AnnSearchRequest(
#         data=vecs["sparse"],
#         anns_field="sparse_vec",
#         limit=top_k*2,
#         expr=expr,
#         expr_params=expr_params,
#         param={"metric_type": "IP"}
#     )
#     ranker = RRFRanker(rrf_k)
#     with connect() as client:
#         res = client.hybrid_search(
#             collection_name=collection_name,
#             reqs=[dense_request, sparse_request],
#             ranker=ranker,
#             limit = top_k,
#             output_fields=["id"],
#         )
#     return {x["id"]: x["distance"] for x in res[0]}
# 
# 