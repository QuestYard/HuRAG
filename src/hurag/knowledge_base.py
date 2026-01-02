from __future__ import annotations
from typing import Any, Literal, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import (
        Document,
        Segment,
        Chunk,
        Knowledge,
        KnowledgeMetadata,
    )

from .kvcache import KVCache

kn_cache = KVCache(max_size=1000, evict_ratio=0.2)

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

async def stat() -> tuple:
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
        SELECT COUNT(*), '知识社区数:' AS catalog FROM segments
        """
    )
    return stat

async def list_documents(
    keyword: str | None = None,
    order: Literal["title", "date", "org"] = "title",
) -> tuple:
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
            )
        FROM documents AS d
        {crieteria}
        {order_by}
        """
    docs = await rss.query(sql, kw_param)

    return docs

async def indexing_documents(
    docs: list[Document],
    embeddings: list[dict[Literal["dense_vecs", "sparse_vecs"], Any]],
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
    logger.info(
        f"{ds} documents containing {ss} segments and {cs} chunks are stored."
    )

    return (ds, ss, cs)

# --- Knowledge Management ---

from .dss import with_rdb

@with_rdb(dict_cursor=True, connection_name="conn", cursor_name="cur")
async def _load_metadata(doc_ids, conn, cur):
    sql = f"""
        SELECT id, title, sn, pub_path, valid_from, valid_to
        FROM documents
        WHERE id IN ({','.join(['%s'] * len(doc_ids))})
    """
    await cur.execute(sql, tuple(doc_ids))
    rows = await cur.fetchall()
    return {row["id"]: row for row in rows}

async def load_knowledge(
    chunks: Iterable[str],
    docs: dict[str, dict] | None = None,
    limit: int | None = None,
) -> dict[str, Knowledge]:
    """
    Load knowledge by chunk IDs.

    Arguments:
        chunks: Iterable of chunk IDs.
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
        WHERE c.id IN ({','.join(['%s'] * len(chk_ids))})
        """,
        tuple(chk_ids)
    )
    # Reorder sdc to match chk_ids order
    sdc_map = {row[2]: row for row in sdc}
    sdc = [sdc_map[chk_id] for chk_id in chk_ids if chk_id in sdc_map]

    doc_ids = set(did for _, did, _ in sdc)
    if docs is None:
        docs = await _load_metadata(doc_ids)

    results = {}
    for sid, did, cid in sdc:
        if sid in results:
            continue
        if did not in docs:
            continue
        if kn_cache.contains(sid):
            results[sid] = kn_cache.get(sid)
            continue
        content = "".join(
            t[0] for t in await rss.query(
                "SELECT text FROM chunks WHERE segment_id = %s ORDER BY seq_no",
                (sid, ),
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
    segments: Iterable[tuple[str, str]],
    docs: dict[str, dict] | None = None,
    limit: int | None = None,
) -> dict[str, Knowledge]:
    """
    Load knowledge by segment IDs along with document ID that the segment belongs to.

    Arguments:
        segments: Iterable[tuple[str, str]], list of (segment_id, document_id).
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
            t[0] for t in await rss.query(
                "SELECT text FROM chunks WHERE segment_id = %s ORDER BY seq_no",
                (sid, ),
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
    ids: Iterable[str],
    docs: dict[str, dict] | None = None,
    limit: int | None = None,
) -> dict[str, Knowledge]:
    """
    Load knowledge by segment IDs.

    Arguments:
        ids: Iterable of segment IDs.
        docs: Optional dictionary of document metadata.
        limit: Optional limit on number of segments to process.

    Returns:
        A dictionary mapping segment IDs to Knowledge objects.
    """
    from .dss import rss

    segments = await rss.query(
        f"""
        SELECT id, document_id FROM segments
        WHERE id IN ({','.join(['%s'] * len(ids))})
        """,
        tuple(ids),
    )
    return await load_knowledge_by_segments(segments, docs, limit)

async def load_knowledge_by_order(
    chunks_scores: dict[str, float],
    docs: dict[str, dict] | None = None,
)-> dict[str, tuple[Knowledge, float]]:
    """
    Load knowledge by chunk IDs with their scores, keeping the order of scores.

    Arguments:
        chunks_scores: dict of chunk IDs and their scores.
        docs: Optional dictionary of document metadata.

    Returns:
        A dictionary mapping segment IDs to tuples of (Knowledge, score):
    """
    from .dss import rss
    from .schemas import Knowledge, KnowledgeMetadata

    if not chunks_scores:
        return {}

    sdc_scores = sorted(
        [
            (*x, chunks_scores[x[2]])
            for x in await rss.query(
                f"""
                SELECT s.id, d.id, c.id
                FROM chunks c
                JOIN segments s ON c.segment_id = s.id
                JOIN documents d ON s.document_id = d.id
                WHERE c.id IN ({','.join(['%s'] * len(chunks_scores))})
                """,
                tuple(chunks_scores.keys()),
            )
        ],
        key = lambda x: x[3],
        reverse = True,
    )
    doc_ids = set(did for _, did, _, _ in sdc_scores)
    if docs is None:
        docs = await _load_metadata(doc_ids)

    results = {}
    for sid, did, cid, score in sdc_scores:
        if sid in results:
            continue
        if did not in docs:
            continue
        if kn_cache.contains(sid):
            results[sid] = (kn_cache.get(sid), score)
            continue
        ctx = "".join(
            t[0] for t in await rss.query(
                "SELECT text FROM chunks WHERE segment_id = %s ORDER BY seq_no",
                (sid, ),
            )
        )
        kn = Knowledge(
            segment_id=sid,
            content=ctx,
            metadata=KnowledgeMetadata.from_dict(docs[did]),
        )
        kn_cache.put(sid, kn)
        results[sid] = (kn, score)

    return results
