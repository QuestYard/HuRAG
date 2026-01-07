from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from embedding_service.async_embedding_client import AsyncEmbeddingClient
    from openai import AsyncOpenAI
    from .schemas import Knowledge

import os
from dataclasses import dataclass, field

from . import conf, logger
from .llm import with_es_client, with_oa_client

@dataclass
class QueryInfo:
    keywords: dict[str, list[str]] = field(default_factory=dict)
    timings: list[str] = field(default_factory=list)
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
    model = os.getenv(f"{conf.llm.extraction}_MODEL")

    # --- to refactor ---
    keywords = {"low_level_keywords": [], "high_level_keywords": []}
    async with asyncio.TaskGroup() as tg:
        t_timing = tg.create_task(extract_timings(query))
        if mode != "naive":
            t_keywords = tg.create_task(extract_query_keywords(query, history))
    as_of_date = t_timing.result()
    if mode != 'naive':
        keywords = t_keywords.result()

    return as_of_date, keywords

# TODO: to test
async def extract_query_keywords(
    query: str,
    history: list[str] | None = None,
    oaclient = None,
    model = None,
):
    import json_repair
    from .llm import extract_response, create_keywords_extraction_prompt, chat

    history = history or []
    # resp = await async_chat(create_keywords_extraction_prompt(query, history)) 
    resp = extract_response(
        await chat(create_keywords_extraction_prompt(query, history)) 
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

