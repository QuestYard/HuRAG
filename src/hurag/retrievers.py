from __future__ import annotations
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from embedding_service.async_embedding_client import AsyncEmbeddingClient
    from openai import AsyncOpenAI
    from .schemas import Knowledge

import os
from datetime import datetime
from dataclasses import dataclass, field

from . import conf, logger
from .llm import with_es_client, with_oa_client, extract_response


@dataclass
class QueryInfo:
    """
    keywords: high level and low level keywords extracted from the query.
    timings: time points extracted from the query, today if no time info in the query.
    embeddings: vector representations of the query, the high level keywords and the
        low level keywords, in order.
    """

    keywords: dict[str, list[str]] = field(default_factory=dict)
    timings: list[datetime] = field(default_factory=list)
    embeddings: dict[str, Any] = field(default_factory=dict)


async def rerank_knowledge(
    query: str,
    knowledge_dict: dict[str, Knowledge],
) -> list[tuple[Knowledge, float]]:
    """
    Rerank the input knowledge objects based on the query.

    Args:
        query (str): the user query.
        knowledge_dict: A dict of knowledge objects like {id: Knowledge, ...}

    Returns:
        A list like [[Knowledge, score], ...]
    """
    if conf.llm.reranker.lower() == "glm":
        return await rerank_knowledge_by_glm(query, knowledge_dict)
    else:
        return await rerank_knowledge_by_es(query, knowledge_dict)


@with_es_client
async def rerank_knowledge_by_es(
    query: str,
    knowledge_dict: dict[str, Knowledge],
    esclient: AsyncEmbeddingClient | None = None,
) -> list[tuple[Knowledge, float]]:
    """
    Rerank the input knowledge objects based on the query by using embedding-service.

    Args:
        query (str): the user query.
        knowledge_dict: A dict of knowledge objects like {id: Knowledge, ...}

    Returns:
        A list like [[Knowledge, score], ...]
    """
    contents = [k.context for k in knowledge_dict.values()]
    response = await esclient.rerank(query, contents)
    return sorted(
        [[k, s] for k, s in zip(knowledge_dict.values(), response.scores)],
        key=lambda x: x[1],
        reverse=True,
    )

async def rerank_knowledge_by_glm(
    query: str,
    knowledge_dict: dict[str, Knowledge],
) -> list[tuple[Knowledge, float]]:
    """
    Rerank the input knowledge objects based on the query by using GLM rerank in parallel.

    Args:
        query (str): the user query.
        knowledge_dict: A dict of knowledge objects like {id: Knowledge, ...}

    Returns:
        A list like [[Knowledge, score], ...]
    """
    from .llm import parallel_glm_rerank
    contents = [k.context for k in knowledge_dict.values()]
    reranked = await parallel_glm_rerank(query, contents)
    return sorted(
        [[k, s] for k, s in zip(knowledge_dict.values(), reranked)],
        key=lambda x: x[1],
        reverse=True,
    )

# @with_rr_client
# async def rerank_knowledge_by_glm(
#     query: str,
#     knowledge_dict: dict[str, Knowledge],
#     rrclient: AsyncClient | None = None,
# ) -> list[tuple[Knowledge, float]]:
#     """
#     Rerank the input knowledge objects based on the query by using GLM rerank.
# 
#     Args:
#         query (str): the user query.
#         knowledge_dict: A dict of knowledge objects like {id: Knowledge, ...}
# 
#     Returns:
#         A list like [[Knowledge, score], ...]
#     """
#     import asyncio
#     from .llm import glm_rerank
# 
#     # --- worker ---
#     async def _rerank_worker(queue: asyncio.Queue):
#         while True:
#             batch = await queue.get()  # batch: ([Knowledge, float], ...)
#             if batch is None:
#                 queue.task_done()
#                 return
#             try:
#                 reranked = await glm_rerank(
#                     query,
#                     [kn[0].context for kn in batch],
#                     client=rrclient,
#                 )
#                 for score in reranked:
#                     batch[score["index"]][1] = score["relevance_score"]
#             except Exception as e:
#                 logger.error(f"Failed to rerank batch using GLM: {e!r}")
#             finally:
#                 queue.task_done()
#     # --- main process ---
#     from itertools import batched
# 
#     _items = [[k, 0.0] for k in knowledge_dict.values()]
#     queue = asyncio.Queue()
#     rerankers = [asyncio.create_task(_rerank_worker(queue)) for _ in range(20)]
#     for batch in batched(_items, n=2):
#         await queue.put(batch)
#     await queue.join()
#     for worker in rerankers:
#         worker.cancel()
#     gathered = await asyncio.gather(*rerankers, return_exceptions=True)
#     return sorted(_items, key=lambda x: x[1], reverse=True)


@with_oa_client(
    base_url=os.getenv(f"{conf.llm.extraction}_BASE_URL"),
    api_key=os.getenv(f"{conf.llm.extraction}_API_KEY"),
)
async def prepare_for_searching(
    query: str,
    history: list[str] | None = None,
    oaclient: AsyncOpenAI | None = None,
) -> QueryInfo:
    """
    Extract keywords, timings from the query and embed the query.

    Arguments:
        query: The user query
        history: History queries. History responses are not needed

    Return:
        A QueryInfo object contains keywords, timings and embeddings.
    """
    import asyncio
    import json_repair
    from .llm import (
        embed_query,
        create_keywords_extraction_prompt,
        create_timing_prompt,
        chat,
    )

    model = os.getenv(f"{conf.llm.extraction}_MODEL")

    async def _extract_query_keywords(query: str, history: list[str] | None = None):
        history = history or []
        resp = extract_response(
            await chat(
                model=model,
                prompt=create_keywords_extraction_prompt(query, history),
                client=oaclient,
            )
        )
        try:
            keywords = json_repair.loads(resp)
            if not keywords:
                return {"high_level_keywords": [], "low_level_keywords": []}
        except Exception as e:
            logger.error(f"JSON parsing error while extract keywords: {e}")
            logger.error(f"LLM respond: {resp}")
            return {"high_level_keywords": [], "low_level_keywords": []}

        return {
            "high_level_keywords": keywords.get("high_level_keywords", []),
            "low_level_keywords": keywords.get("low_level_keywords", []),
        }

    async def _extract_timings(query: str):
        resp = extract_response(
            await chat(
                model=model,
                prompt=create_timing_prompt(query),
                client=oaclient,
            )
        )

        try:
            as_of_time = json_repair.loads(resp)
            if not as_of_time:
                return [datetime.today()]
        except Exception as e:
            logger.error(f"JSON parsing error while extract timings: {e}")
            logger.error(f"LLM respond: {resp}")
            return [datetime.today()]

        timings = sorted(
            [datetime.strptime(d, "%Y-%m-%d") for d in as_of_time],
            reverse=True,
        )

        return timings if timings else [datetime.today()]

    async with asyncio.TaskGroup() as tg:
        t_timing = tg.create_task(_extract_timings(query))
        t_keywords = tg.create_task(_extract_query_keywords(query, history))

    timings = t_timing.result()
    keywords = t_keywords.result()
    embeddings, _ = await embed_query(
        [query] + keywords["high_level_keywords"] + keywords["low_level_keywords"]
    )

    return QueryInfo(keywords=keywords, timings=timings, embeddings=embeddings)


async def retrieve(
    query: str,
    *,
    history: list[str] | None = None,
    mode: Literal["mix", "naive", "graph", "global", "community"] = "mix",
    query_info: QueryInfo | None = None,
    user_path: str | None = None,
    top_k: int | None = None,
    top_a: int | None = None,
    top_k_naive: int | None = None,
    rrf_k_naive: float | None = None,
    top_k_graph: int | None = None,
    num_hops: int | None = None,
    max_communities: int | None = None,
    max_nodes: int | None = None,
) -> list[list[Knowledge, float]]:
    """
    Arguments:
        query: current user query.
        history: history queries, history responses are not needed.
        mode:
            "mix" (default): naive + graph;
            "naive": only naive;
            "graph": only graph search with top_k_graph segments;
            "global": nodes and edges in the whole graph;
            "community": nodes and edges inside communities.
        query_info: returned values of prepare_for_searching.
        user_path: the organization path of current user.
        top_k: number of knowledges in final results in K-RAG search,
        top_a: number of knowledges in final results of associations search.
        top_k_naive: number of chunks in naive search results,
        rrf_k_naive: rrf_k for hybrid search,
        top_k_graph: number of chunks in graph search results,
        num_hops: (BPS) number of hops,
        max_communities: (BPS) maximum number of communities,
        max_nodes: (BPS) maximum number of nodes.

    Returns:
        A list like [[Knowledge, score], ...], descending ordered by scores.
    """
    from .knowledge_base import search

    if mode not in ["mix", "naive", "graph", "global", "community"]:
        mode = "mix"

    query_info = query_info or await prepare_for_searching(query, history=history)

    if (
        not query_info.keywords["low_level_keywords"]
        and not query_info.keywords["high_level_keywords"]
    ):
        logger.warning("No keyword extracted, force to 'naive' mode")
        mode = "naive"

    logger.info(
        f"[QUERY]: {query} [MODE]: {mode}, [TIMINGS]: {query_info.timings}, "
        f"[KEYWORDS]: {query_info.keywords}"
    )

    return await search(
        query,
        mode=mode,
        query_info=query_info,
        user_path=user_path or conf.app.org_path,
        top_k=top_k or conf.retrieval.top_k,
        top_a=top_a or conf.retrieval.top_a,
        top_k_naive=top_k_naive or conf.retrieval.top_s,
        rrf_k_naive=rrf_k_naive or conf.retrieval.rrf_k,
        top_k_graph=top_k_graph or conf.retrieval.top_g,
        num_hops=num_hops or conf.retrieval.max_depth,
        max_communities=max_communities or conf.retrieval.max_comms,
        max_nodes=max_nodes or conf.retrieval.max_nodes,
    )
