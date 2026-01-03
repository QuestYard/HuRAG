from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import Graph

from . import logger, conf
from .llm import (
    create_entity_extraction_prompt,
    create_entity_gleaning_prompt,
    create_summarize_descriptions_prompt,
    with_oa_client,
    chat_with_retry,
    extract_response,
)
from .utilities import generate_id
from .constants import GRAPH_FIELD_SEP

import os
from dataclasses import dataclass, field
from collections import Counter

@dataclass
class _Segment:
    id: str
    doc_id: str
    text: str
    chk_ids: list[str] = field(default_factory=list)
    history: list[dict[str, str]] = field(default_factory=list)

@with_oa_client(
    base_url=os.getenv(f"{conf.llm.extraction}_BASE_URL"),
    api_key=os.getenv(f"{conf.llm.extraction}_API_KEY"),
    timeout=120.0,
)
async def extract_kg_elements(
    document_ids: str | list[str] | None = None,
    num_extracting_workers: int = 10,
    num_gleaning_workers: int = 10,
    limit: int | None = None,
    oaclient = None,
) -> dict[str, dict[str, str]]:
    """
    Extract entities and relations from segments of documents in the rss with
    field kg_built == False.

    Segments that contain only one chunk and the chunk is detected to be a
    nonsense chunk will be skipped.

    Knowledge graph elements extracting will take a long time to complete.

    Args:
        document_ids: A single document ID or a list of document IDs to
            process. If None, process all documents with kg_built == False.
        num_extracting_workers: Number of concurrent workers for extracting.
            Default is 10.
        num_gleaning_workers: Number of concurrent workers for gleaning.
            Default is 10.
        limit: Limit the number of segments to process. If None, process all
            segments.
        oaclient: A placeholder for OpenAI client, will be injected by decorator.

    Returns:
        A list of dictionaries containing the document, segment, text and
        the raw responses from LLMs for parsing.

        The structure of each dictionary is:
        {
            "document_id": str,
            "title": str,
            "segment_id": str,
            "text": str,
            "extracting": str,
            "gleaning": str,
        }
    """
    model = os.getenv(f"{conf.llm.extraction}_MODEL")

    async def _extractor(queue, gleaning_queue):
        while True:
            _seg = await queue.get()
            if _seg is None:
                queue.task_done()
                return
            try:
                pmt = create_entity_extraction_prompt(_seg.text)
                res = await chat_with_retry(model, pmt, client=oaclient)
                _seg.history = [
                    {"role": "user", "content": pmt},
                    extract_response(res, content_only=False),
                ]
                await gleaning_queue.put(_seg)
            except Exception as e:
                logger.error(f"_extractor error: {e!r}")
            finally:
                queue.task_done()

    async def _gleaner(queue, pbar=None):
        while True:
            _seg = await queue.get()
            if _seg is None:
                queue.task_done()
                return
            try:
                pmt = create_entity_gleaning_prompt()
                res = await chat_with_retry(
                    model,
                    pmt,
                    history_messages=_seg.history,
                    client=oaclient,
                )
                _seg.history.extend(
                    [
                        {"role": "user", "content": pmt},
                        extract_response(res, content_only=False),
                    ]
                )
                if pbar:
                    pbar.update(1)
            except Exception as e:
                logger.error(f"_gleaner error: {e!r}")
            finally:
                queue.task_done()

    from .dss import rss

    sql = "SELECT id, title FROM documents WHERE kg_built = FALSE"
    params = ()
    if document_ids:
        if isinstance(document_ids, str):
            document_ids = [document_ids]
        sql += f" AND id IN ({','.join(['%s'] * len(document_ids))})"
        params = tuple(document_ids)
    docs = {d[0]: d[1] for d in await rss.query(sql, params)}
    if not docs:
        return []

    chunks = await rss.query(
        f"SELECT c.id, c.segment_id, c.seq_no, c.text, s.document_id "
        f"FROM chunks AS c "
        f"INNER JOIN segments AS s ON c.segment_id = s.id "
        f"WHERE s.document_id IN ({','.join(['%s'] * len(docs))}) "
        f"ORDER BY c.segment_id, c.seq_no",
        tuple(docs)
    )
    segs = []
    for chk in chunks:
        if segs and segs[-1].id == chk[1]:
            segs[-1].text += chk[3]
            segs[-1].chk_ids.append(chk[0])
        else:
            segs.append(
                _Segment(
                    id=chk[1],
                    doc_id=chk[4],
                    text=chk[3],
                    chk_ids=[chk[0]]
                )
            )
            if limit and len(segs) >= limit:
                break

    # extracting
    import asyncio
    from tqdm.asyncio import tqdm

    pbar = tqdm(total=len(segs), ncols=80, desc="Extracting")

    ex_queue = asyncio.Queue()
    gl_queue = asyncio.Queue()
    extractors = [
        asyncio.create_task(
            _extractor(ex_queue, gl_queue)
        ) for _ in range(num_extracting_workers)
    ]
    gleaners = [
        asyncio.create_task(
            _gleaner(gl_queue, pbar=pbar)
        ) for _ in range(num_gleaning_workers)
    ]

    for seg in segs:
        await ex_queue.put(seg)

    # Retry logic for failed extractions
    max_retries = 3
    for attempt in range(max_retries + 1):
        await ex_queue.join()
        await gl_queue.join()

        failed_segs = []
        for seg in segs:
            # Check if history is incomplete (missing gleaning) or has empty content
            # Expecting 4 messages: User(Ext), AI(Ext), User(Glean), AI(Glean)
            if (
                len(seg.history) < 4
                or not seg.history[1].get("content")
                or not seg.history[3].get("content")
            ):
                failed_segs.append(seg)

        if not failed_segs:
            break

        if attempt < max_retries:
            logger.warning(
                f"Retrying {len(failed_segs)} segments "
                f"(Attempt {attempt + 1}/{max_retries})"
            )
            for seg in failed_segs:
                await ex_queue.put(seg)
        else:
            logger.error(
                f"Failed to extract {len(failed_segs)} segments after "
                f"{max_retries} retries."
            )

    for worker in extractors:
        worker.cancel()
    for worker in gleaners:
        worker.cancel()

    gathered = await asyncio.gather(
        *extractors,
        *gleaners,
        return_exceptions=True
    )

    results = [
        {
            "document_id": seg.doc_id,
            "title": docs[seg.doc_id],
            "segment_id": seg.id,
            "text": seg.text,
            "extracting": seg.history[1]["content"] if seg.history else None,
            "gleaning": seg.history[-1]["content"] if seg.history else None,
        } for seg in segs
    ]

    return results

@with_oa_client(
    base_url=os.getenv(f"{conf.llm.extraction}_BASE_URL"),
    api_key=os.getenv(f"{conf.llm.extraction}_API_KEY"),
    timeout=120.0,
)
async def normalize_kg_elements(
    g: Graph,
    num_workers: int = 20,
    oaclient = None,
) -> Graph:
    """
    Normalize the knowledge graph elements in the graph.

    The normalization includes:
    1. Type voting: Vote the most common type for each entity and relation.
    2. Description rewriting: Rewrite the description using LLM.

    Args:
        g: The knowledge graph to be normalized.
        num_workers: Number of concurrent workers for normalization.
            Default is 20.

    Returns:
        The normalized knowledge graph.
    """
    model = os.getenv(f"{conf.llm.extraction}_MODEL")

    async def _normalize_single_element(queue, pbar=None):
        while True:
            _element = await queue.get()
            if _element is None:
                queue.task_done()
                return
            if not _element.id:
                _element.id = generate_id()
            _element.type = sorted(
                Counter(_element.type.split(GRAPH_FIELD_SEP)).items(),
                key = lambda x: x[1],
                reverse = True,
            )[0][0]
            descriptions = set(_element.description.split(GRAPH_FIELD_SEP))
            if len(descriptions) == 1:
                _element.description = descriptions.pop()
                if pbar:
                    pbar.update(1)
                queue.task_done()
                continue

            entity_name = (
                [_element.name]
                if hasattr(_element, "name")
                else [_element.source, _element.target]
            )
            try:
                pmt = create_summarize_descriptions_prompt(
                    entity_name = entity_name,
                    descriptions = descriptions,
                )
                _desc = await chat_with_retry(model, pmt, client=oaclient)
                _element.description = extract_response(_desc)
                if pbar:
                    pbar.update(1)
            except Exception as e:
                logger.error(f"summarize description error: {e!r}")
            finally:
                queue.task_done()

    import asyncio
    from tqdm.asyncio import tqdm
    pbar = tqdm(total = len(g.nodes) + len(g.edges), ncols=80, desc="Normalizing")

    queue = asyncio.Queue()
    workers = [
        asyncio.create_task(_normalize_single_element(queue, pbar=pbar))
        for _ in range(num_workers)
    ]
    for node in g.nodes:
        await queue.put(node)
    for edge in g.edges:
        await queue.put(edge)

    await queue.join()

    for worker in workers:
        worker.cancel()

    gathered = await asyncio.gather(*workers, return_exceptions=True)

    return g
