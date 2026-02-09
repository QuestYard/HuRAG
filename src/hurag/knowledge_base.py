from __future__ import annotations
from typing import Any, TYPE_CHECKING
from collections.abc import Collection

if TYPE_CHECKING:
    from .schemas import Document, Knowledge
    from .retrievers import QueryInfo

from .types import RetrieveMode, DocumentOrder, EmbeddingType
from .kvcache import KVCache

kn_cache = KVCache(max_size=1000, evict_ratio=0.2)

_HBASE = 5  # base of hierarchical decrease factor, 1 / log_b(b + dist)

# --- Document Management ---

SQL_INS_DOC = [
    """
    INSERT INTO documents (
        id, title, sn, date, valid_from, valid_to, replaces, pub_path, localizes,
        authors, kg_built
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """,
    "INSERT INTO segments (id, document_id, seq_no) VALUES (%s, %s, %s)",
    "INSERT INTO chunks (id, segment_id, seq_no, text) VALUES (%s, %s, %s, %s)",
]


async def stat() -> list[tuple]:
    from .dss import rss

    stat = await rss.query(
        """
        SELECT COUNT(*), '文档总数:' AS catalog FROM documents
        UNION ALL
        SELECT COUNT(*), '段落/条文数:' AS catalog FROM segments
        UNION ALL
        SELECT COUNT(*), '文本块数:' AS catalog FROM chunks
        UNION ALL
        SELECT COUNT(*), '知识图谱实体节点数:' AS catalog FROM entities
        UNION ALL
        SELECT COUNT(*), '知识图谱实体关系数:' AS catalog FROM relations
        UNION ALL
        SELECT COUNT(*), '知识社区数:' AS catalog FROM communities
        """
    )
    return stat


async def list_documents(
    keyword: str | None = None,
    order: DocumentOrder = "title",
) -> list[tuple]:
    """
    List documents in the knowledge base with optional keyword filtering and ordering.

    Arguments:
        keyword: Optional keyword to filter document titles.
        order: Field to order the results by. Can be "title", "date", or "org".

    Returns:
        A list of tuples containing document information.

        Elements in each tuple:
            - title (str): Document title.
            - sn (str | None): Document serial number.
            - valid_from (datetime): Document valid from date.
            - valid_to (datetime | None): Document valid to date.
            - pub_path (str): Document publication path.
            - segments (str): Number of segments in the document.
            - entities (str): Number of distinct entities in the document.
            - id (str): Document ID.
    """
    from .dss import rss

    if keyword:
        crieteria = f"WHERE title LIKE %s"
        kw_param = (f"%{keyword}%",)
    else:
        crieteria = ""
        kw_param = ()
    if order == "date":
        order_by = "ORDER BY valid_from DESC"
    elif order == "org":
        order_by = "ORDER BY pub_path ASC"
    else:
        order_by = "ORDER BY title ASC"
    sql = f"""
        SELECT
            d.title,
            d.sn,
            d.valid_from,
            d.valid_to,
            d.pub_path,
            (SELECT COUNT(*) FROM segments s WHERE s.document_id = d.id),
            (
                SELECT COUNT(distinct ec.entity_id) FROM entity_cite ec
                JOIN segments s ON ec.segment_id = s.id 
                WHERE s.document_id = d.id
            ),
            d.id
        FROM documents AS d
        {crieteria}
        {order_by}
        """
    docs = await rss.query(sql, kw_param)

    return docs


async def indexing_documents(
    docs: list[Document],
    embeddings: list[dict[EmbeddingType, Any]],
) -> tuple[int, int, int]:
    """
    Indexing documents into the knowledge base with provided embeddings.

    Args:
        docs (list[Document]):
            List of Document objects to be indexed.
        embeddings (list[dict]):
            A list of dictionary containing embeddings for each document.

    Returns:
        list[Document]: List of successfully indexed Document objects.
    """
    from .dss import rss, vss
    from .utilities import generate_id
    from . import logger

    # store into rdb
    for doc in docs:
        doc.id = generate_id()
        for seg in doc.segments:
            seg.id = generate_id()
            seg.doc_id = doc.id
            for chk in seg.chunks:
                chk.id = generate_id()
                chk.seg_id = seg.id
    data = []
    data.append(
        [
            (
                doc.id,
                doc.title,
                doc.sn,
                doc.date,
                doc.valid_from,
                doc.valid_to,
                doc.replaces,
                doc.pub_path,
                doc.localizes,
                doc.authors,
                doc.kg_built,
            )
            for doc in docs
        ]
    )
    data.append(
        [
            (
                seg.id,
                seg.doc_id,
                seg.seq_no,
            )
            for doc in docs
            for seg in doc.segments
        ]
    )
    data.append(
        [
            (
                chk.id,
                chk.seg_id,
                chk.seq_no,
                chk.text,
            )
            for doc in docs
            for seg in doc.segments
            for chk in seg.chunks
        ]
    )
    try:
        await rss.transact(SQL_INS_DOC, data)
    except Exception as e:
        logger.error(f"Failed save documents into rdb: {e}")
        raise

    # store into vdb
    data = [
        {
            "id": chk.id,
            "dense_vec": None,
            "sparse_vec": None,
            "doc_id": doc.id,
        }
        for doc in docs
        for seg in doc.segments
        for chk in seg.chunks
    ]
    _embeddings = (
        {"dense_vec": d, "sparse_vec": s}
        for embedding in embeddings
        for d, s in zip(embedding["dense_vecs"], embedding["sparse_vecs"])
    )
    for chk, vecs in zip(data, _embeddings):
        chk.update(vecs)

    try:
        await vss.upsert("chunks", data)
    except Exception as e:
        logger.error(f"Failed save chunk vectors into vdb: {e}")
        raise

    # statistic and log
    ds, ss, cs = len(docs), 0, 0
    for doc in docs:
        ss += len(doc.segments)
        for seg in doc.segments:
            cs += len(seg.chunks)
    logger.info(f"{ds} documents containing {ss} segments and {cs} chunks are stored.")

    return (ds, ss, cs)


# --- Knowledge Management ---


async def _load_metadata(doc_ids: Collection[str]):
    from .dss import rss

    sql = f"""
        SELECT
            id,
            title,
            sn,
            date,
            pub_path,
            valid_from,
            valid_to,
            replaces,
            localizes,
            authors
        FROM documents
        WHERE id IN ({",".join(["%s"] * len(doc_ids))})
    """
    rows = await rss.query(sql, tuple(doc_ids), as_dict=True)
    return {row["id"]: row for row in rows}


async def load_knowledge(
    chunks: Collection[str],
    docs: dict[str, dict] | None = None,
    limit: int | None = None,
) -> dict[str, Knowledge]:
    """
    Load knowledge by chunk IDs.

    Arguments:
        chunks: Collection of chunk IDs.
        docs: Optional dictionary of document metadata.
        limit: Optional limit on number of chunks to process.

    Returns:
        A dictionary mapping segment IDs to Knowledge objects.
    """
    from .dss import rss
    from .schemas import Knowledge, KnowledgeMetadata

    if not chunks:
        return {}

    chk_ids = list(chunks) if limit is None else list(chunks)[:limit]

    sdc = await rss.query(
        f"""
        SELECT s.id, d.id, c.id
        FROM chunks c
        JOIN segments s ON c.segment_id = s.id
        JOIN documents d ON s.document_id = d.id
        WHERE c.id IN ({",".join(["%s"] * len(chk_ids))})
        """,
        tuple(chk_ids),
    )
    # Reorder sdc to match chk_ids order
    sdc_map = {row[2]: row for row in sdc}
    sdc = [sdc_map[chk_id] for chk_id in chk_ids if chk_id in sdc_map]

    doc_ids = set(did for _, did, _ in sdc)
    if docs is None:
        docs = await _load_metadata(doc_ids)

    results = {}
    for sid, did, _ in sdc:
        if sid in results:
            continue
        if did not in docs:
            continue
        if kn_cache.contains(sid):
            results[sid] = kn_cache.get(sid)
            continue
        content = "".join(
            t[0]
            for t in await rss.query(
                "SELECT text FROM chunks WHERE segment_id = %s ORDER BY seq_no",
                (sid,),
            )
        )
        kn = Knowledge(
            segment_id=sid,
            content=content,
            metadata=KnowledgeMetadata.from_dict(docs[did]),
        )
        kn_cache.put(sid, kn)
        results[sid] = kn

    return results


async def load_knowledge_by_segments(
    segments: Collection[tuple[str, str]],
    docs: dict[str, dict] | None = None,
    limit: int | None = None,
) -> dict[str, Knowledge]:
    """
    Load knowledge by segment IDs along with document ID that the segment belongs to.

    Arguments:
        segments: Collection[tuple[str, str]], list of (segment_id, document_id).
        docs: Optional dictionary of document metadata.
        limit: Optional limit on number of segments to process.

    Returns:
        A dictionary mapping segment IDs to Knowledge objects.
    """
    from .dss import rss
    from .schemas import Knowledge, KnowledgeMetadata

    if not segments:
        return {}

    seg_doc = list(segments) if limit is None else list(segments)[:limit]

    if docs is None:
        doc_ids = set(did for _, did in seg_doc)
        docs = await _load_metadata(doc_ids)

    results = {}
    for sid, did in seg_doc:
        if sid in results:
            continue
        if did not in docs:
            continue
        if kn_cache.contains(sid):
            results[sid] = kn_cache.get(sid)
            continue
        content = "".join(
            t[0]
            for t in await rss.query(
                "SELECT text FROM chunks WHERE segment_id = %s ORDER BY seq_no",
                (sid,),
            )
        )
        kn = Knowledge(
            segment_id=sid,
            content=content,
            metadata=KnowledgeMetadata.from_dict(docs[did]),
        )
        kn_cache.put(sid, kn)
        results[sid] = kn

    return results


async def load_knowledge_by_segment_ids(
    ids: Collection[str],
    docs: dict[str, dict] | None = None,
    limit: int | None = None,
) -> dict[str, Knowledge]:
    """
    Load knowledge by segment IDs.

    Arguments:
        ids: Collection of segment IDs.
        docs: Optional dictionary of document metadata.
        limit: Optional limit on number of segments to process.

    Returns:
        A dictionary mapping segment IDs to Knowledge objects.
    """
    from .dss import rss

    segments = await rss.query(
        f"""
        SELECT id, document_id FROM segments
        WHERE id IN ({",".join(["%s"] * len(ids))})
        """,
        tuple(ids),
    )
    return await load_knowledge_by_segments(segments, docs, limit)


async def search(
    query: str,
    mode: RetrieveMode,
    query_info: QueryInfo,
    *,
    user_path: str,
    top_k: int,
    top_a: int,
    top_k_naive: int,
    rrf_k_naive: float,
    top_k_graph: int,
    num_hops: int,
    max_communities: int,
    max_nodes: int,
) -> list[tuple[Knowledge, float]]:
    """
    user_path: the organization path of current user, or None (defult) to
        use conf().app.org_path instead.
    mode:
        "mix" (default): naive + graph
        "naive": only naive
        "graph": only graph
        "global": nodes and edges in the whole graph
        "community": nodes and edges inside communities
        "agentic": retrieve knowledge via some agentic skill
    Returns:
        A list like [(Knowledge, score), ...], descending ordered by scores.
    """
    docs, scope = await _th_scope(query_info.timings, user_path)
    embeddings = query_info.embeddings

    async def _naive_search():
        from .dss import vss

        naive_search_results = await vss.search(
            collection_name="chunks",
            scope=scope,
            vecs={
                "dense": [embeddings["dense_vecs"][0]],
                "sparse": embeddings["sparse_vecs"][0],
            },
            top_k=top_k_naive,
            rrf_k=rrf_k_naive,
        )
        return naive_search_results

    async def _graph_search():
        from .dss import gss

        graph_search_results = await gss.search(
            keywords=query_info.keywords,
            vecs=embeddings,
            docs=docs,
            top_k=top_k_graph,
            max_nodes=max_nodes,
            hops=num_hops,
            rrf_k=rrf_k_naive,
        )
        return graph_search_results

    async def _associations():
        from .dss import gss

        associations_results = await gss.associations(
            keywords=query_info.keywords,
            vecs=embeddings,
            docs=docs,
            top_k=top_a,
            hops=num_hops,
            max_communities=max_communities if mode == "community" else 0,
            max_nodes=max_nodes,
            rrf_k=rrf_k_naive,
        )
        return associations_results

    if mode in ["naive", "graph", "mix", "agentic"]:
        from .retrievers import rerank_knowledge

        naive_search_results = await _naive_search()
        graph_search_results = await _graph_search()
        kns_naive = await load_knowledge(set(naive_search_results), docs)
        kns_graph = await load_knowledge(set(graph_search_results), docs)
        kn_scores = (await rerank_knowledge(query, kns_naive | kns_graph))[:top_k]
    else:  # global, community, or else
        associations_results = await _associations()
        kns_comms = await load_knowledge_by_segments(associations_results, docs)
        kn_scores = [[x, 1.0] for x in kns_comms.values()]

    for entry in kn_scores:
        kn, sc = entry
        entry[1] = sc * docs[kn.metadata.id]["decrease_factor"]
    final = sorted(kn_scores, key=lambda x: x[1], reverse=True)

    return [tuple(f) for f in final]


# --- Inner functions ---

_is_valid = lambda fr, to, date: fr <= date and (to is None or to >= date)

_org_level = lambda p: len(p.strip("*").split("/")) - 1


def _filter_docs(docs, timings):
    """Filter expired documents according to the timings"""
    final_docs = []
    cur_doc = 0
    n = len(docs)
    for cur_date in timings:
        while cur_doc < n and _is_valid(
            docs.iloc[cur_doc]["valid_from"],
            docs.iloc[cur_doc]["valid_to"],
            cur_date.date(),
        ):
            final_docs.append(docs.iloc[cur_doc])
            cur_doc += 1
    return final_docs


def _doc_paths(user_path):
    """Extract doc_paths under the user_path."""
    path = user_path.split("/")
    ret = ["/".join(path[:i]) + "*" for i in range(2, len(path) + 1)]
    ret.append(user_path)
    return ret


async def _th_scope(timings, user_path) -> tuple[dict[str, dict], list[str]]:
    """Find document searching scope."""
    import pandas as pd
    import numpy as np
    from .dss import rss

    # find search scope of documents
    paths = _doc_paths(user_path)
    pd_docs = pd.DataFrame(
        await rss.query(
            f"""
            SELECT
                id,
                title,
                sn,
                date,
                valid_from,
                valid_to,
                replaces,
                pub_path,
                localizes,
                authors
            FROM documents
            WHERE
                valid_from <= %s
                AND (
                    pub_path IN ({", ".join(["%s"] * len(paths))})
                    OR pub_path NOT LIKE '/%%'
                ) 
            ORDER BY
                valid_to IS NOT NULL,
                valid_to DESC
            """,
            tuple([timings[0]] + paths),
        ),
        columns=pd.Index(
            [
                "id",
                "title",
                "sn",
                "date",
                "valid_from",
                "valid_to",
                "replaces",
                "pub_path",
                "localizes",
                "authors",
            ]
        ),
    )
    docs = pd.DataFrame(_filter_docs(pd_docs, timings))
    docs["level"] = docs["pub_path"].map(_org_level)
    docs = docs.sort_values("level", ascending=False, ignore_index=True)
    docs["dist"] = 0
    localizes = tuple(docs["localizes"])
    for idx, loc in enumerate(localizes):
        if loc:
            docs.at[docs.index[docs["title"] == loc].item(), "dist"] = (
                docs.iloc[idx]["dist"] + 1
            )
    docs["decrease_factor"] = np.log(_HBASE) / np.log(docs["dist"] + _HBASE)
    # find search scope of chunks
    scope = (
        []
        if docs.empty
        else [
            x[0]
            for x in await rss.query(
                f"""
            SELECT c.id FROM chunks c
            JOIN segments s ON c.segment_id = s.id
            JOIN documents d ON s.document_id = d.id
            WHERE d.id IN ({",".join(["%s"] * len(docs))})
            """,
                tuple(docs["id"]),
            )
        ]
    )
    return {row["id"]: row for row in docs.to_dict(orient="records")}, scope


# --- Tool Functions for API Server or MCP/Tool Calling


async def get_knowledge_by_segment_ids(
    seg_ids: Collection[str],
    user_path: str | None = None,
) -> list[Knowledge]:
    """
    Get Knowledge objects by segment IDs.

    Arguments:
        seg_ids (Collection[str]): required, the segment IDs to load as Knowledge.
        user_path (str): required, the organization path of current user to determent
            the documents to search in.

    Return:
        A list of Knowledge objects corresponding to the input segment IDs.
    """
    from datetime import datetime
    from . import conf

    user_path = user_path or conf.app.org_path

    docs, _ = await _th_scope([datetime.today()], user_path)
    return list((await load_knowledge_by_segment_ids(seg_ids, docs)).values())
