from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from embedding_service.async_embedding_client import AsyncEmbeddingClient
    from openai import AsyncOpenAI
    from .schemas import Knowledge

import os
from datetime import datetime
from dataclasses import dataclass, field

from . import conf, logger
from .llm import (
    with_es_client,
    with_oa_client,
    extract_response,
)

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
async def rerank_knowledges(
    query: str,
    knowledge_dict: dict[Knowledge],
    esclient: AsyncEmbeddingClient | None = None,
) -> list[Knowledge, float]:
    """
    Rerank the input knowledge objects based on the query.

    Args:
        query (str): the user query.
        knowledge_dict: A dict of knowledge objects like {id: Knowledge, ...}

    Returns:
        A list like [[Knowledge, score], ...]
    """
    contents = [k.context for k in knowledge_dict.values()]
    scores = await esclient.rerank(query, contents)
    return sorted(
        [[k, s] for k, s in zip(knowledge_dict.values(), scores)],
        key=lambda x: x[1],
        reverse=True
    )

@with_es_client
@with_oa_client(
    base_url=os.getenv(f"{conf.llm.extraction}_BASE_URL"),
    api_key=os.getenv(f"{conf.llm.extraction}_API_KEY"),
)
async def prepare_for_searching(
    query: str,
    history: list[str] | None = None,
    esclient: AsyncEmbeddingClient | None = None,
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
            "low_level_keywords": keywords.get("low_level_keywords", [])
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
    embeddings = await embed_query(
        [query]
        + keywords["high_level_keywords"]
        + keywords["low_level_keywords"]
    )

    return QueryInfo(keywords=keywords, timings=timings, embeddings=embeddings)



