from __future__ import annotations
from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    from embedding_service.async_embedding_client import AsyncEmbeddingClient
    from embedding_service.schemas import EmbeddingPayloadMeta
    from .schemas import Document

from .llm import with_es_client
from . import logger

@with_es_client
async def embed_query(
    query: str | list[str],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> tuple[dict[str, Any], EmbeddingPayloadMeta]:
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
    esclient: AsyncEmbeddingClient | None = None,
) -> AsyncGenerator[tuple[dict[str, Any], EmbeddingPayloadMeta], None, None]:
    from itertools import islice

    if batch_type == 0: # all-in-one
        chunks = [
            chk.text
            for doc in docs
            for seg in doc.segments
            for chk in seg.chunks
        ]
        try:
            results = await esclient.embed(chunks, return_sparse=True)
            yield results
        except Exception as e:
            logger.error(f"Failed embedding documents: {e}")
            raise
    elif batch_type == 1: # doc-by-doc
        for doc in docs:
            chunks = [chk.text for seg in doc.segments for chk in seg.chunks]
            try:
                results = await esclient.embed(chunks, return_sparse=True)
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
        while batch_chunks := list(islice(all_chunks, batch_type)):
            try:
                results = await esclient.embed(batch_chunks, return_sparse=True)
                yield results
            except Exception as e:
                logger.error(f"Failed embedding documents: {e}")
                raise


# import os
# import asyncio
# import json_repair
# 
# from tqdm.asyncio import tqdm
# from dataclasses import dataclass, field
# from collections import Counter
# from datetime import datetime
# 
# from .kernel import (
#     logger,
#     conf,
#     log_err,
#     async_chat,
#     async_chat_bak,
# )
# from .dss import rss
# from .prompts import (
#     create_entity_extraction_prompt,
#     create_entity_gleaning_prompt,
#     create_summarize_descriptions_prompt,
#     create_community_summarize_prompt,
#     create_community_summary_aggregate_prompt,
#     create_keywords_extraction_prompt,
#     create_timing_prompt,
# )
# from .kg import (
#     Entity,
#     Relation,
#     Graph,
#     GRAPH_FIELD_SEP
# )
# from .utils import generate_id
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
# async def embed_query(query: str):
#     from .kernel import ef
#     return await ef(query)
# 
# async def embed_keywords(keywords: dict[str, list[str]]):
#     from .kernel import ef
#     return await ef(
#         keywords["low_level_keywords"] + keywords["high_level_keywords"]
#     )
# 
# def _chunks_batch_generator(docs, batch_size):
#     batch = []
#     for doc in docs:
#         for seg in doc.segments:
#             for chk in seg.chunks:
#                 batch.append(chk)
#                 if len(batch) == batch_size:
#                     yield batch
#                     batch = []
#     if batch:
#         yield batch
# 
# async def embed_documents(docs: list, batch_size: int=1024):
#     from .kernel import ef
# 
#     async def _embed(chunks):
#         vecs = await ef([chk.text for chk in chunks])
#         for i, chk in enumerate(chunks):
#             chk.dense_vec = vecs["dense"][i]
#             chk.sparse_vec = vecs["sparse"][[i]]
# 
#     _batches = _chunks_batch_generator(docs, batch_size)
#     total = 0
#     for batch in _batches:
#         total += len(batch)
#         await _embed(batch)
# 
#     logger().info(f"{total} chunks embedded.")
# 
#     return docs
# 
# def _kg_elements_batch_generator(g, batch_size):
#     batch = { "elements": [], "texts": [] }
#     for e in g.nodes + g.edges:
#         batch["elements"].append(e)
#         if isinstance(e, Entity):
#             batch["texts"].append("## " + e.name + ":\n\n- " + e.description)
#         else:
#             batch["texts"].append(
#                 "## " + e.source + " - " + e.target + ":\n\n- " + e.description
#             )
#         if len(batch["elements"]) == batch_size:
#             yield batch
#             batch["elements"].clear()
#             batch["texts"].clear()
#     if batch:
#         yield batch
# 
# async def embed_kg_elements(g: Graph, batch_size: int=1024):
#     from .kernel import ef
# 
#     _batches = _kg_elements_batch_generator(g, batch_size)
#     for batch in _batches:
#         vecs = await ef(batch["texts"])
#         for i, e in enumerate(batch["elements"]):
#             e.dense_vec = vecs["dense"][i]
#             e.sparse_vec = vecs["sparse"][[i]]
# 
#     return g
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
# @dataclass
# class _Segment:
#     id: str
#     doc_id: str=field(repr=False, compare=False)
#     text: str=field(repr=False, compare=False)
#     chk_ids: list[str]=field(default_factory=list, repr=False, compare=False)
#     history: list[dict]=field(default_factory=list, repr=False, compare=False)
# 
# async def _extractor(queue, gleaning_queue):
#     while True:
#         _seg = await queue.get()
#         if _seg is None:
#             queue.task_done()
#             return
#         try:
#             pmt = create_entity_extraction_prompt(_seg.text)
#             res = await async_chat(pmt)
#             _seg.history = [
#                 {
#                     "role": "user",
#                     "content": pmt,
#                 },
#                 {
#                     "role": "assistant",
#                     "content": res,
#                 }
#             ]
#             await gleaning_queue.put(_seg)
#         except Exception as e:
#             logger().error(f"_extractor error: {e!r}")
#         finally:
#             queue.task_done()
# 
# async def _gleaner(queue, using_backup_llm=False, pbar=None):
#     while True:
#         _seg = await queue.get()
#         if _seg is None:
#             queue.task_done()
#             return
#         try:
#             pmt = create_entity_gleaning_prompt()
#             if using_backup_llm:
#                 res = await async_chat_bak(pmt, history_messages=_seg.history)
#             else:
#                 res = await async_chat(pmt, history_messages=_seg.history)
#             _seg.history.extend([
#                 {
#                     "role": "user",
#                     "content": pmt,
#                 },
#                 {
#                     "role": "assistant",
#                     "content": res,
#                 }
#             ])
#             if pbar:
#                 pbar.update(1)
#         except Exception as e:
#             logger().error(f"_gleaner error: {e!r}")
#         finally:
#             queue.task_done()
# 
# async def extract_kg_elements(
#     using_backup_llm_for_gleaning: bool=False,
#     num_extracting_workers: int=10,
#     num_gleaning_workers: int=10,
# )-> dict[str, dict]:
#     """
#     Extract entities and relations from segments of documents in the rss with
#     field kg_built == False.
# 
#     Segments that contain only one chunk and the chunk is detected to be a
#     nonsense chunk will be skipped.
# 
#     Knowledge graph elements extracting will take a long time to complete.
# 
#     Args:
#         using_backup_llm_for_gleaning: Whether to use the backup LLM for
#             gleaning. Default is False.
#         num_extracting_workers: Number of concurrent workers for extracting.
#             Default is 10.
#         num_gleaning_workers: Number of concurrent workers for gleaning.
#             Default is 10.
#     
#     Returns:
#         A list of dictionaries containing the document, segment, text and
#         the raw responses from LLMs for parsing.
# 
#         The structure of each dictionary is:
#         {
#             "document_id": str,
#             "title": str,
#             "segment_id": str,
#             "text": str,
#             "extracting": str,
#             "gleaning": str,
#         }
#     """
#     from .kg.nonsenses import detect_nonsense_chunks
# 
#     docs = {
#         d[0]: d[1] for d in rss.query(
#             "SELECT id, title FROM documents WHERE kg_built = FALSE"
#         )
#     }
#     if not docs:
#         return []
#     nonsense_map = detect_nonsense_chunks(list(docs.keys()))
#     chunks = rss.query(
#         f"SELECT c.id, c.segment_id, c.seq_no, c.text, s.document_id "
#         f"FROM chunks AS c INNER JOIN segments AS s ON c.segment_id = s.id "
#         f"WHERE c.id IN ({','.join(['?'] * len(nonsense_map))}) "
#         f"ORDER BY c.segment_id, c.seq_no",
#         tuple(chk_id for chk_id in nonsense_map)
#     )
#     segs = []
#     for chk in chunks:
#         if segs and segs[-1].id == chk[1]:
#             segs[-1].text += chk[3]
#             segs[-1].chk_ids.append(chk[0])
#         else:
#             segs.append(
#                 _Segment(
#                     id=chk[1],
#                     doc_id=chk[4],
#                     text=chk[3],
#                     chk_ids=[chk[0]]
#                 )
#             )
# 
#     # extracting
#     pbar = tqdm(total=len(segs), ncols=80, desc="Extracting")
# 
#     ex_queue = asyncio.Queue()
#     gl_queue = asyncio.Queue()
#     extractors = [
#         asyncio.create_task(
#             _extractor(ex_queue, gl_queue)
#         ) for _ in range(num_extracting_workers)
#     ]
#     gleaners = [
#         asyncio.create_task(
#             _gleaner(
#                 gl_queue,
#                 using_backup_llm=using_backup_llm_for_gleaning,
#                 pbar=pbar
#             )
#         ) for _ in range(num_gleaning_workers)
#     ]
# 
#     for seg in segs:
#         if len(seg.chk_ids) == 1 and nonsense_map[seg.chk_ids[0]] > 0.68:
#             pbar.update(1)
#             continue
#         await ex_queue.put(seg)
# 
#     await ex_queue.join()
#     await gl_queue.join()
# 
#     for worker in extractors:
#         worker.cancel()
#     for worker in gleaners:
#         worker.cancel()
# 
#     gathered = await asyncio.gather(
#         *extractors,
#         *gleaners,
#         return_exceptions=True
#     )
# 
#     results = [
#         {
#             "document_id": seg.doc_id,
#             "title": docs[seg.doc_id],
#             "segment_id": seg.id,
#             "text": seg.text,
#             "extracting": seg.history[1]["content"] if seg.history else None,
#             "gleaning": seg.history[-1]["content"] if seg.history else None,
#         } for seg in segs
#     ]
# 
#     return results
# 
# async def _normalize_single_element(queue, pbar=None):
#     while True:
#         _element = await queue.get()
#         if _element is None:
#             queue.task_done()
#             return
#         if not _element.id:
#             _element.id = generate_id()
#         _element.type = sorted(
#             Counter(_element.type.split(GRAPH_FIELD_SEP)).items(),
#             key = lambda x: x[1],
#             reverse = True,
#         )[0][0]
#         descriptions = set(_element.description.split(GRAPH_FIELD_SEP))
#         if len(descriptions) == 1:
#             _element.description = descriptions.pop()
#             if pbar:
#                 pbar.update(1)
#             queue.task_done()
#             continue
# 
#         entity_name = (
#             [_element.name] if isinstance(_element, Entity) else
#             [_element.source, _element.target]
#         )
#         try:
#             pmt = create_summarize_descriptions_prompt(
#                 entity_name = entity_name,
#                 descriptions = descriptions,
#             )
#             _element.description = await async_chat(pmt)
#             if pbar:
#                 pbar.update(1)
#         except Exception as e:
#             logger().error(f"summarize description error: {e!r}")
#         finally:
#             queue.task_done()
# 
# async def normalize_kg_elements(g: Graph, num_workers=20)-> Graph:
#     """
#     Normalize the knowledge graph elements in the graph.
# 
#     The normalization includes:
#     1. Type voting: Vote the most common type for each entity and relation.
#     2. Description rewriting: Rewrite the description using LLM.
# 
#     Args:
#         g: The knowledge graph to be normalized.
#         num_workers: Number of concurrent workers for normalization.
#             Default is 20.
# 
#     Returns:
#         The normalized knowledge graph.
#     """
#     pbar = tqdm(total=len(g.nodes)+len(g.edges), ncols=80, desc="Normalizing")
# 
#     queue = asyncio.Queue()
#     workers = [
#         asyncio.create_task(
#             _normalize_single_element(queue, pbar=pbar)
#         ) for _ in range(num_workers)
#     ]
#     for node in g.nodes:
#         await queue.put(node)
#     for edge in g.edges:
#         await queue.put(edge)
# 
#     await queue.join()
# 
#     for worker in workers:
#         worker.cancel()
# 
#     gathered = await asyncio.gather(*workers, return_exceptions=True)
# 
#     return g
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
