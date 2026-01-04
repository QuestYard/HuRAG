from __future__ import annotations
from typing import TYPE_CHECKING, Any, AsyncGenerator, Literal

if TYPE_CHECKING:
    from embedding_service.async_embedding_client import AsyncEmbeddingClient
    from embedding_service.schemas import EmbeddingPayloadMeta
    from ..schemas import Document, Graph

from . import with_es_client
from .. import logger

@with_es_client
async def embed_query(
    query: str | list[str],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> tuple[dict[str, Any], EmbeddingPayloadMeta]:
    """
    Embed a query or a list of queries into vector representations.
    
    Args:
        query: A single query string or a list of query strings to be embedded.
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.
            
    Returns:
        A tuple containing:
            - A dictionary with keys "dense_vecs" and "sparse_vecs" containing the
              corresponding vector representations.
            - An EmbeddingPayloadMeta object with metadata about the embeddings.
    """
    try:
        results = await esclient.embed(query, return_sparse=return_sparse)
        return results
    except Exception as e:
        logger.error(f"Failed embedding query: {e}")
        raise

@with_es_client
async def embed_documents(
    docs: Document | list[Document],
    *,
    batch_type: int = 1,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> AsyncGenerator[tuple[dict[str, Any], EmbeddingPayloadMeta], None, None]:
    """
    Embed documents into vector representations in batches.
    
    Args:
        docs: A single Document object or a list of Document objects to be
            embedded.
        batch_type: The type of batching to use for embedding.
            - 0: all-in-one (embed all chunks from all documents in one batch)
            - 1: doc-by-doc (embed chunks from each document separately)
            - >1: chunk-by-chunk with chunk_size = batch_type
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.
            
    Yields:
        A tuple containing:
            - A dictionary with keys "dense_vecs" and "sparse_vecs" containing
                the corresponding vector representations for the batch.
            - An EmbeddingPayloadMeta object with metadata about the embeddings.
    """
    from itertools import islice

    if batch_type == 0: # all-in-one
        chunks = [
            chk.text
            for doc in docs
            for seg in doc.segments
            for chk in seg.chunks
        ]
        try:
            results = await esclient.embed(chunks, return_sparse=return_sparse)
            yield results
        except Exception as e:
            logger.error(f"Failed embedding documents: {e}")
            raise
    elif batch_type == 1: # doc-by-doc
        for doc in docs:
            chunks = [chk.text for seg in doc.segments for chk in seg.chunks]
            try:
                results = await esclient.embed(chunks, return_sparse=return_sparse)
                yield results
            except Exception as e:
                logger.error(f"Failed embedding documents: {e}")
                raise
    elif batch_type > 1: # chunk-by-chunk with chunk_size = batch_type
        all_chunks = (
            chk.text
            for doc in docs
            for seg in doc.segments
            for chk in seg.chunks
        )
        while batch := list(islice(all_chunks, batch_type)):
            try:
                results = await esclient.embed(batch, return_sparse=return_sparse)
                yield results
            except Exception as e:
                logger.error(f"Failed embedding documents: {e}")
                raise

@with_es_client
async def embed_keywords(
    keywords: dict[Literal["low_level_keywords", "high_level_keywords"], list[str]],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> tuple[dict[str, Any], EmbeddingPayloadMeta]:
    """
    Embed keywords into vector representations.
    
    Args:
        keywords: A dictionary with keys "low_level_keywords" and
            "high_level_keywords", each containing a list of keyword strings
            to be embedded.
        return_sparse: Whether to return sparse vectors along with dense vectors.
            Default is True.
        esclient: An instance of AsyncEmbeddingClient. This is provided
            automatically by the decorator.
            
    Returns:
        A tuple containing:
            - A dictionary with keys "dense_vecs" and "sparse_vecs" containing
              the corresponding vector representations.
            - An EmbeddingPayloadMeta object with metadata about the embeddings.
    """
    try:
        return await esclient.embed(
            keywords["low_level_keywords"] + keywords["high_level_keywords"],
            return_sparse=return_sparse,
        )
    except Exception as e:
        logger.error(f"Failed embedding keywords: {e}")
        raise

@with_es_client
async def embed_kg_elements(
    g: Graph,
    *,
    return_sparse: bool = True,
    batch_size: int=1024,
    esclient: AsyncEmbeddingClient | None = None,
) -> AsyncGenerator[tuple[dict[str, Any], EmbeddingPayloadMeta], None, None]:
    from itertools import chain, batched

    for batch in batched(chain(g.nodes, g.edges), batch_size):
        texts = [
            f"## {e.name}: \n\n- {e.description}"
            if hasattr(e, "name")
            else f"## {e.source} - {e.target}:\n\n- {e.description}"
            for e in batch
        ]
        try:
            results = await esclient.embed(texts, return_sparse=return_sparse)
            yield results
        except Exception as e:
            logger.error(f"Failed embedding graph elements: {e}")
            raise

# 
# async def embed_community_summaries(summaries: dict) -> list[dict]:
#     from .kernel import ef
# 
#     table = [
#         {
#             "c_no": k,
#             "summary": v[-1] if v else "null",
#             "dense_vec": None,
#             "sparse_vec": None,
#         }
#         for k, v in summaries.items()
#     ]
#     vecs = await ef([s["summary"] for s in table])
#     for i, e in enumerate(table):
#         e["dense_vec"] = vecs["dense"][i]
#         e["sparse_vec"] = vecs["sparse"][[i]]
# 
#     return table
# 

#
# async def rerank_knowledges(query: str, knowledge_dict: dict):
#     """
#     knowledge_dict: {id: Knowledge, ...}
# 
#     Returns:
#         A list like [[Knowledge, score], ...]
#     """
#     from .kernel import rf
#     contents = [k.context for k in knowledge_dict.values()]
#     scores = await rf(query, contents, batch_size=conf().retrieval.rerank_batch)
#     return sorted(
#         [[k, s] for k, s in zip(knowledge_dict.values(), scores)],
#         key=lambda x: x[1],
#         reverse=True
#     )
# 
# async def summarize_communities(
#     graph,
#     partitions,
#     nodes,
#     batch_size=90,
#     min_size=10,
#     num_workers=20
# ):
#     """
#     Arguments:
#         graph: an igraph.Graph object
#         partitions: partitions resulted from igraph.community_leiden()
#         nodes: entities information dict { id: (name, description), ... }
# 
#     Return: a dict of community summaries { community_no: summary, ... }
#     """
#     def _nodes_batch_generator(community):
#         size = len(community)
#         for start in range(0, size, batch_size):
#             if size - start < batch_size + 10:
#                 yield community[start:]
#                 break
#             else:
#                 yield community[start:start+batch_size]
# 
#     async def _summarize_worker():
#         while True:
#             batch = await summarize_queue.get()
#             if batch is None:
#                 summarize_queue.task_done()
#                 return
#             try:
#                 ids = tuple(graph.vs["name"][i] for i in batch["vs"])
#                 pmt = create_community_summarize_prompt(
#                     [
#                         {
#                             "name": nodes[x][0],
#                             "description": nodes[x][1]
#                         }
#                         for x in ids
#                     ]
#                 )
#                 summaries[batch["c_no"]].append(await async_chat(pmt))
#                 summarize_pbar.update(1)
#             except Exception as e:
#                 logger().error(f"generate community summary error: {e!r}")
#             finally:
#                 summarize_queue.task_done()
# 
#     async def _aggregate_worker():
#         while True:
#             item = await aggregate_queue.get()
#             if item is None:
#                 aggregate_queue.task_done()
#                 return
#             if len(item[1]) <= 1:
#                 aggregate_pbar.update(1)
#                 aggregate_queue.task_done()
#                 continue
#             try:
#                 pmt = create_community_summary_aggregate_prompt(item[1])
#                 item[1].append(await async_chat(pmt))
#                 aggregate_pbar.update(1)
#             except Exception as e:
#                 logger().error(f"aggregate community summary error: {e!r}")
#             finally:
#                 aggregate_queue.task_done()
# 
#     num_batches = list(
#         map(
#             lambda x: (len(x)//batch_size)+(len(x)%batch_size>=min_size),
#             partitions
#         )
#     )
#     summarize_queue = asyncio.Queue()
#     summarize_workers = [
#         asyncio.create_task(_summarize_worker()) for _ in range(num_workers)
#     ]
#     summaries = {}
#     summarize_pbar = tqdm(
#         total=sum(num_batches),
#         ncols=80,
#         desc="Summarizing",
#         position=0
#     )
#     for c_no, c in enumerate(partitions):
#         if len(c) < min_size:
#             continue
#         summaries[c_no] = []
#         batches = _nodes_batch_generator(c)
#         for b in batches:
#             await summarize_queue.put({ "c_no": c_no, "vs": b })
#     await summarize_queue.join()
#     for worker in summarize_workers:
#         worker.cancel()
#     gathered = await asyncio.gather(*summarize_workers, return_exceptions=True)
#     summarize_pbar.close()
# 
#     aggregate_queue = asyncio.Queue()
#     aggregate_workers = [
#         asyncio.create_task(_aggregate_worker()) for _ in range(num_workers)
#     ]
#     aggregate_pbar = tqdm(
#         total=len(summaries),
#         ncols=80,
#         desc="Aggregating",
#         position=1
#     )
#     for item in summaries.items():
#         await aggregate_queue.put(item)
#     await aggregate_queue.join()
#     for worker in aggregate_workers:
#         worker.cancel()
#     gathered = await asyncio.gather(*aggregate_workers, return_exceptions=True)
#     aggregate_pbar.close()
# 
#     return summaries
# 
# async def extract_query_keywords(
#     query: str,
#     history: list[str] | None=None,
# ):
#     history = history or []
#     resp = await async_chat(create_keywords_extraction_prompt(query, history)) 
# 
#     try:
#         keywords = json_repair.loads(resp)
#         if not keywords:
#             return {
#                 "high_level_keywords": [],
#                 "low_level_keywords": []
#             } 
#     except Exception as e:
#         logger.error(f"JSON parsing error while extract keywords: {e}")
#         logger.error(f"LLM respond: {resp}")
#         return {
#             "high_level_keywords": [],
#             "low_level_keywords": []
#         } 
# 
#     return {
#         "high_level_keywords": keywords.get("high_level_keywords", []),
#         "low_level_keywords": keywords.get("low_level_keywords", [])
#     }
# 
# async def extract_timings(query: str):
#     resp = await async_chat(create_timing_prompt(query))
# 
#     try:
#         timings = json_repair.loads(resp)
#         if not timings:
#             return [datetime.today()]
#     except Exception as e:
#         logger.error(f"JSON parsing error while extract timings: {e}")
#         logger.error(f"LLM respond: {resp}")
#         return [datetime.today()]
# 
#     as_of_date = sorted(
#         [datetime.strptime(d, "%Y-%m-%d") for d in timings],
#         reverse=True
#     )
# 
#     return as_of_date if as_of_date else [datetime.today()]
# 
# 
