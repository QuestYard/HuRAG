from __future__ import annotations
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import Document

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

