from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .llm import AsyncEmbeddingClient
    from openai import AsyncOpenAI

import os
from datetime import datetime
from dataclasses import dataclass, field

from . import conf, logger
from .types import RetrieveMode
from .llm import with_es_client, with_oa_client, extract_from_chat
from .schemas import Knowledge, Entity, Relation


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


@with_es_client
async def rerank_knowledge(
    query: str,
    knowledge_dict: dict[str, Knowledge],
    esclient: AsyncEmbeddingClient,
) -> list[list[Knowledge | float]]:
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
    if not response.scores:
        response.scores = [0.0] * len(contents)
    results = sorted(
        zip(knowledge_dict.values(), response.scores),
        key=lambda x: x[1],
        reverse=True,
    )
    return [[k, s] for k, s in results]


@with_oa_client(client_name="extraction")
async def prepare_for_searching(
    query: str,
    *,
    join_keywords: bool = False,
    history: list[str] | None = None,
    oaclient: AsyncOpenAI,
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
        chat_completion,
    )

    model = os.getenv(f"{conf.llm.extraction}_MODEL", "")

    async def _extract_query_keywords(query: str, history: list[str] | None = None):
        history = history or []
        resp = await chat_completion(
            client=oaclient,
            model=model,
            prompt=create_keywords_extraction_prompt(query, history),
        )
        resp = extract_from_chat(resp)["content"]
        try:
            keywords = json_repair.loads(resp)
            if not keywords or not isinstance(keywords, dict):
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
        resp = await chat_completion(
            client=oaclient,
            model=model,
            prompt=create_timing_prompt(query),
        )
        resp = extract_from_chat(resp)["content"]
        try:
            as_of_time = json_repair.loads(resp)
            if not as_of_time or not isinstance(as_of_time, list):
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
    if join_keywords:
        keywords["high_level_keywords"] = [
            ", ".join(keywords["high_level_keywords"])
            if keywords["high_level_keywords"]
            else query
        ]
        keywords["low_level_keywords"] = [
            ", ".join(keywords["low_level_keywords"])
            if keywords["low_level_keywords"]
            else query
        ]

    embeddings, _ = await embed_query(
        [query] + keywords["high_level_keywords"] + keywords["low_level_keywords"]
    )

    return QueryInfo(keywords=keywords, timings=timings, embeddings=embeddings)


async def retrieve(
    query: str,
    *,
    history: list[str] | None = None,
    mode: RetrieveMode = "mix",
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
) -> list[tuple[Knowledge, float]]:
    """
    RetrieveMode of "agentic" and "none" will be implemented in another application
    named Alaya, which is the agentic rag application based on HuRAG.

    To support Alaya for agentic rag, hurag-server will provide new APIs for tool
    calling. New retrieval logics needed by Alaya's tools will be implemented in
    hurag-server modules.

    Arguments:
        query: current user query.
        history: history queries, history responses are not needed.
        mode:
            "mix" (default): naive + graph;
            "naive": (deprecated) only naive;
            "graph": (deprecated) only graph search with top_k_graph segments;
            "global": nodes and edges in the whole graph;
            "community": nodes and edges inside communities;
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
        A list like [(Knowledge, score), ...], descending ordered by scores.
    """
    from .knowledge_base import search

    logger.info(f"[QUERY]: {query} [MODE]: {mode}")

    return await search(
        query,
        mode=mode,
        query_info=query_info or await prepare_for_searching(query, history=history),
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


async def graph_search(
    query: str,
    *,
    rerank: bool = False,
    user_org_path: str | None = None,
    top_k_entities: int | None = None,
    top_k_relations: int | None = None,
    top_k_segments: int | None = None,
) -> tuple[list[Entity], list[Relation], list[Knowledge]]:
    # 0. preparation
    from .dss import rss, vss, gss

    top_k_e = top_k_entities or conf.retrieval.entity_top_k
    top_k_r = top_k_relations or conf.retrieval.relation_top_k
    top_k_s = top_k_segments or conf.retrieval.segment_top_k
    user_org_path = user_org_path or conf.app.org_path

    # 1. 提取 low level keywords 和 high level keywords，分别用 ", " 连接为字符串;
    if not query:
        return [], [], []

    logger.info(f"[QUERY]: {query} [MODE]: agentic_graph")

    query_info =  await prepare_for_searching(query, join_keywords=True)

    # 2. 使用 low level keywords 字符串搜索最相似的 entity_top_k 个 entities
    #    及其直接关联的 relations，得到 local entities (相似度排序) 和
    #    local relations (先 degree，后 relation weight 排序);
    local_nodes = await vss.search(
        collection_name="nodes",
        vecs={
            "dense": [query_info.embeddings["dense_vecs"][2]],
            "sparse": query_info.embeddings["sparse_vecs"][2],
        },
        top_k=top_k_e,
    )
    local_entities = sorted(local_nodes, key=lambda k: local_nodes[k], reverse=True)

    conn_edges = await gss.edge_degrees(await gss.one_hop_edges(list(local_entities)))
    local_relations = sorted(conn_edges, key=lambda k:conn_edges[k], reverse=True)

    # 3. 使用 high level keywords 字符串搜索最相似的 relation_top_k 个 relations
    #    及其两个端点上的 entities，得到 global entities (按 relations 序先 src 后 tgt)
    #    和 global relations (相似度排序);
    global_edges = await vss.search(
        collection_name="edges",
        vecs={
            "dense": [query_info.embeddings["dense_vecs"][1]],
            "sparse": query_info.embeddings["sparse_vecs"][1],
        },
        top_k=top_k_r,
    )
    global_relations = sorted(global_edges, key=lambda k: global_edges[k], reverse=True)
    global_entities = await gss.one_hop_nodes(global_relations)

    # 4. 使用 query 搜索最相似的 segment_top_k 个 query_segments (相似度序);
    from .knowledge_base import _th_scope

    _, scope = await _th_scope(query_info.timings, user_org_path)
    query_segments = await vector_search(
        query_info.embeddings,
        scope=scope,
        top_k=top_k_s,
    )

    # 5. 使用 Round-robin 归并 local entities 和 global entities，得到 final entities：
    #    - 按照先 local 后 global 的次序，从向量相似度由高到低逐个抽取；
    #    - 如有重复直接跳过。
    from itertools import zip_longest

    pairs = zip_longest(local_entities, global_entities, fillvalue=None)

    def _round_robin():
        for l_ent, g_ents in pairs:
            if l_ent is not None:
                yield l_ent

            if g_ents is not None:
                for g_ent in g_ents:
                    yield g_ent

    final_entities = list(dict.fromkeys(_round_robin()))

    # 6. 使用 Round-robin 归并 local 和 global relations 为 final relations;
    pairs = zip_longest(local_relations, global_relations, fillvalue=None)
    merged = (rel for pair in pairs for rel in pair if rel is not None)
    final_relations = list(dict.fromkeys(merged))

    # 7. 归并根据 query 搜索得到的 segments 和 final entities, final relations 上引用
    #    的 segments：
    #    - 在 final entities 所引用的所有 segments 中搜索最多 2 倍于实体数的与 query
    #      最相似的 entity_segments;
    #    - 在 final relations 所引用的所有 segments 中做同样的搜索，在搜索前先依照上
    #      一步得到的 entity_segments 进行去重，得到 relation_segments;
    #    - 使用 Round-robin 归并 query_segments, entity_segments, relation_segments
    #    - (if needed) rerank 最终的 segments，返回前 segment_top_k 个。

    entity_segments = []
    relation_segments = []
    if final_entities:
        entity_cites_scope = [
            x[0]
            for x in await rss.query(
                f"""
                SELECT c.id FROM chunks c
                JOIN segments s ON s.id = c.segment_id
                JOIN entity_cite ec ON ec.segment_id = s.id
                JOIN entities e ON e.id = ec.entity_id
                WHERE e.id IN ({','.join(['%s'] * len(final_entities))})
                """,
                tuple(final_entities),
            )
        ]
        entity_segments = await vector_search(
            query,
            scope=entity_cites_scope,
            top_k=len(final_entities) * 2,
        )

    if final_relations:
        relation_cites_scope = [
            x[0]
            for x in await rss.query(
                f"""
                SELECT c.id FROM chunks c
                JOIN segments s ON s.id = c.segment_id
                JOIN relation_cite rc ON rc.segment_id = s.id
                JOIN relations r ON r.id = rc.relation_id
                WHERE r.id IN ({','.join(['%s'] * len(final_relations))})
                """,
                tuple(final_relations),
            )
        ]
        relation_segments = await vector_search(
            query,
            scope=relation_cites_scope,
            top_k=len(final_relations) * 2,
        )

    final_segments = dict.fromkeys(query_segments)
    final_segments.update(dict.fromkeys(entity_segments))
    final_segments.update(dict.fromkeys(relation_segments))
    final_segments = list(final_segments)

    # 8. load knowledge, entities, relations
    from .knowledge_base import load_knowledge_by_segment_ids
    kns = await load_knowledge_by_segment_ids(final_segments)

    if rerank:
        rr = (await rerank_knowledge(query, kns))[:top_k_s]
        result_kns: list[Knowledge] = [x[0] for x in rr]
    else:
        result_kns = list(dict.fromkeys(kns[k] for k in final_segments[:top_k_s]))

    result_entities = [
        Entity(**p)
        for p in await gss.load_nodes(final_entities[:top_k_e])
    ]
    result_relations = [
        Relation(**p)
        for p in await gss.load_edges(final_relations[:top_k_r])
    ]

    return result_entities, result_relations, result_kns


async def vector_search(
    query_or_embeddings: str | dict,
    *, 
    scope: list[str] | None = None,
    top_k: int | None = None,
    rrf_k: float | None = None,
) -> list[str]: 
    if not query_or_embeddings:
        return []

    from .dss import vss, rss
    from .llm import embed_query

    if top_k is None:
        top_k = int(conf.retrieval.top_k)
    if rrf_k is None:
        rrf_k = float(conf.retrieval.rrf_k)

    if isinstance(query_or_embeddings, str):
        logger.info(f"[QUERY]: {query_or_embeddings} [MODE]: agentic_vector")
        embeddings = (await embed_query(query_or_embeddings))[0]
    else:
        logger.info(f"[QUERY]: EMBEDDINGS [MODE]: agentic_vector")
        embeddings = query_or_embeddings

    chunks = await vss.search(
        collection_name="chunks",
        scope=scope,
        vecs={
            "dense": [embeddings["dense_vecs"][0]],
            "sparse": embeddings["sparse_vecs"][0],
        },
        top_k=top_k * 2,
        rrf_k=rrf_k,
    )
    chk_ids = sorted(chunks, key=lambda k: chunks[k], reverse=True)

    placeholder = ",".join(["%s"] * len(chk_ids))
    chk_seg = {
        x[0]: x[1]
        for x in await rss.query(
            f"SELECT id, segment_id FROM chunks WHERE id IN ({placeholder})",
            tuple(chk_ids),
        )
    }
    segments = list(dict.fromkeys(chk_seg[chk_id] for chk_id in chk_ids))

    return segments[:top_k]
