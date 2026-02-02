from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from .schemas import Graph
    import igraph as ig
    from igraph.clustering import VertexClustering

from . import logger, conf
from .llm import (
    create_entity_extraction_prompt,
    create_entity_gleaning_prompt,
    create_summarize_descriptions_prompt,
    create_community_summarize_prompt,
    create_community_summary_aggregate_prompt,
    with_oa_client,
    chat_with_retry,
    extract_response,
)
from .utilities import generate_id
from .constants import GRAPH_FIELD_SEP

import os
from dataclasses import dataclass, field
from collections import Counter, defaultdict

@dataclass
class _Segment:
    id: str
    doc_id: str
    text: str
    chk_ids: list[str] = field(default_factory=list)
    history: list[dict[str, str]] = field(default_factory=list)

@with_oa_client(client_name="extraction", timeout=120.0)
async def extract_kg_elements(
    document_ids: str | list[str] | None = None,
    num_extracting_workers: int = 10,
    num_gleaning_workers: int = 10,
    limit: int | None = None,
    oaclient: AsyncOpenAI | None = None,
) -> list[dict[str, str]]:
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
                    extract_response(res, content_only=False), # type: ignore
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
                        extract_response(res, content_only=False),  # type: ignore
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
        return list()

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
        asyncio.create_task(_extractor(ex_queue, gl_queue))
        for _ in range(num_extracting_workers)
    ]
    gleaners = [
        asyncio.create_task(_gleaner(gl_queue, pbar=pbar))
        for _ in range(num_gleaning_workers)
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

    _ = await asyncio.gather(*extractors, *gleaners, return_exceptions=True)

    results = [
        {
            "document_id": seg.doc_id,
            "title": docs[seg.doc_id],
            "segment_id": seg.id,
            "text": seg.text,
            "extracting": seg.history[1]["content"] if seg.history else None,
            "gleaning": seg.history[-1]["content"] if seg.history else None,
        }
        for seg in segs
    ]

    return results

@with_oa_client(client_name="extraction", timeout=120.0)
async def normalize_kg_elements(
    g: Graph,
    num_workers: int = 20,
    oaclient: AsyncOpenAI | None = None,
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
    failed_elements = []

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
                _element.description = extract_response(_desc)  # type: ignore
                if pbar:
                    pbar.update(1)
            except Exception as e:
                logger.error(f"summarize description error: {e!r}")
                failed_elements.append(_element)
            finally:
                queue.task_done()

    import asyncio
    from tqdm.asyncio import tqdm
    pbar = tqdm(total=len(g.nodes) + len(g.edges), ncols=80, desc="Normalizing")

    queue = asyncio.Queue()
    workers = [
        asyncio.create_task(_normalize_single_element(queue, pbar=pbar))
        for _ in range(num_workers)
    ]
    for node in g.nodes:
        await queue.put(node)
    for edge in g.edges:
        await queue.put(edge)

    # Retry logic for failed extractions
    max_retries = 3
    for attempt in range(max_retries + 1):
        await queue.join()

        if not failed_elements:
            break

        if attempt < max_retries:
            logger.warning(
                f"Retrying {len(failed_elements)} elements "
                f"(Attempt {attempt + 1}/{max_retries})"
            )
            while failed_elements:
                await queue.put(failed_elements.pop())
        else:
            logger.error(
                f"Failed to extract {len(failed_elements)} segments after "
                f"{max_retries} retries."
            )

    for worker in workers:
        worker.cancel()

    _ = await asyncio.gather(*workers, return_exceptions=True)

    return g

async def community_leiden(resolution: float = 0.5) -> tuple[
    ig.Graph,
    VertexClustering,
    dict[str, tuple[str, str]]
]:
    """
    Create undirect graph from entities and relations in database and evaluate
    the partitions by using Leiden algorithm.

    The default value of parameter 'resolution' is set to 0.5, it's under
    tested and it's not suggested to be larger than 1.

    Return an igraph.Graph object, its partitions and a dict maps entity ids
    to their entity names and descriptions.

    Arguments:
        resolution: float, the resolution parameter for Leiden algorithm

    Return:
        g: igraph.Graph object
        partitions: the partitions resulted from Leiden algorithm
        nodes: dict, maps entity ids to (name, description)
    """
    import igraph as ig
    from .dss import rss

    nodes = {
        n[0]: (n[1], n[2])
        for n in await rss.query("SELECT id, name, description FROM entities")
    }
    edges = await rss.query("SELECT source_id, target_id, strength FROM relations")
    # aggregate edges so the graph is undirected
    agg = defaultdict(float)
    for src, tgt, w in edges:
        if src == tgt:
            continue  # ignore self-loops
        # always order the pair alphabetically to ensure (A,B) == (B,A)
        key = tuple(sorted((src, tgt)))
        agg[key] += w

    # build edge list and weights
    edges_with_weights = [(u, v, w) for (u, v), w in agg.items()]

    # create the graph, letting igraph assign vertex indices automatically
    g = ig.Graph.TupleList(
        edges_with_weights,
        directed=False,
        edge_attrs=["weight"]
    )

    # create partitions by using Leiden algorithm
    partitions = g.community_leiden(
        objective_function="modularity",
        resolution=resolution,
        weights=g.es["weight"]
    )

    return g, partitions, nodes

@with_oa_client(client_name="extraction", timeout=120.0)
async def summarize_communities(
    graph: ig.Graph,
    partitions: VertexClustering,
    nodes: dict[str, tuple[str, str]],
    batch_size: int = 90,
    min_size: int = 10,
    num_workers: int = 20,
    oaclient: AsyncOpenAI | None = None,
) -> dict[int, list[str]]:
    """
    Summarize each community in the graph by using LLM.

    Arguments:
        graph: an igraph.Graph object
        partitions: partitions resulted from igraph.community_leiden()
        nodes: entities information dict { id: (name, description), ... }

    Return:
        a dict of community summaries { community_no: summary, ... }
    """
    import asyncio
    from tqdm.asyncio import tqdm

    model = os.getenv(f"{conf.llm.extraction}_MODEL")

    def _nodes_batch_generator(community):
        size = len(community)
        for start in range(0, size, batch_size):
            if size - start < batch_size + min_size:
                yield community[start:]
                break
            else:
                yield community[start : start + batch_size]

    async def _summarize_worker():
        while True:
            batch = await summarize_queue.get()
            if batch is None:
                summarize_queue.task_done()
                return
            try:
                ids = tuple(graph.vs["name"][i] for i in batch["vs"])
                pmt = create_community_summarize_prompt(
                    [{"name": nodes[x][0], "description": nodes[x][1]} for x in ids]
                )
                _resp = await chat_with_retry(model, pmt, client=oaclient)
                summaries[batch["c_no"]].append(extract_response(_resp))  # type: ignore
                summarize_pbar.update(1)
            except Exception as e:
                logger.error(f"generate community summary error: {e!r}")
            finally:
                summarize_queue.task_done()

    async def _aggregate_worker():
        while True:
            item = await aggregate_queue.get()
            if item is None:
                aggregate_queue.task_done()
                return
            if len(item[1]) <= 1:
                aggregate_pbar.update(1)
                aggregate_queue.task_done()
                continue
            try:
                pmt = create_community_summary_aggregate_prompt(item[1])
                _resp = await chat_with_retry(model, pmt, client=oaclient)
                item[1].append(extract_response(_resp))  # type: ignore
                aggregate_pbar.update(1)
            except Exception as e:
                logger.error(f"aggregate community summary error: {e!r}")
            finally:
                aggregate_queue.task_done()

    num_batches = list(
        map(
            lambda x: (len(x) // batch_size) + (len(x) % batch_size >= min_size),
            partitions,
        )
    )
    summarize_queue = asyncio.Queue()
    summarize_workers = [
        asyncio.create_task(_summarize_worker()) for _ in range(num_workers)
    ]
    summaries = {}
    summarize_pbar = tqdm(
        total=sum(num_batches), ncols=80, desc="Summarizing", position=0
    )
    for c_no, c in enumerate(partitions):
        if len(c) < min_size:
            continue
        summaries[c_no] = []
        batches = _nodes_batch_generator(c)
        for b in batches:
            await summarize_queue.put({ "c_no": c_no, "vs": b })
    await summarize_queue.join()
    for worker in summarize_workers:
        worker.cancel()
    _ = await asyncio.gather(*summarize_workers, return_exceptions=True)
    summarize_pbar.close()

    aggregate_queue = asyncio.Queue()
    aggregate_workers = [
        asyncio.create_task(_aggregate_worker()) for _ in range(num_workers)
    ]
    aggregate_pbar = tqdm(
        total=len(summaries), ncols=80, desc="Aggregating", position=1
    )
    for item in summaries.items():
        await aggregate_queue.put(item)
    await aggregate_queue.join()
    for worker in aggregate_workers:
        worker.cancel()
    _ = await asyncio.gather(*aggregate_workers, return_exceptions=True)
    aggregate_pbar.close()

    return summaries
