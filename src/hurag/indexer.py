from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import Document

from .types import EmbeddingType


SQL_INS_DOC = [
    """
    INSERT INTO documents (
        id, title, sn, date, valid_from, valid_to, replaces, pub_path, localizes,
        authors, kg_built, category_id
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """,
    "INSERT INTO segments (id, document_id, seq_no) VALUES (%s, %s, %s)",
    "INSERT INTO chunks (id, segment_id, seq_no, text) VALUES (%s, %s, %s, %s)",
]


async def save_attachments(atts: list[dict]) -> int:
    from .dss import rss, fss, FileContent, AT_FOLDER
    from .utilities import generate_id

    if not atts:
        return 0

    for att in atts:
        att["att"].id = generate_id()

    sql = "INSERT INTO attachments (id, title, document_id) VALUES (%s, %s, %s)"
    data = [(att["att"].id, att["att"].title, att["doc_id"]) for att in atts]
    total = await rss.dml(sql, data)
    fcs = [
        FileContent(id=att["att"].id, folder=AT_FOLDER, content=att["content"])
        for att in atts
    ]
    fss.save_files(fcs, overwrite_duplicates=False)

    return total


async def save_multimodal_docs(docs: list[dict]) -> int:
    from .dss import rss, fss, FileContent, MM_FOLDER
    from .utilities import generate_id

    if not docs:
        return 0

    for doc in docs:
        doc["doc"].id = generate_id()

    sql = SQL_INS_DOC[0]
    data = [
        (
            doc["doc"].id,
            doc["doc"].title,
            doc["doc"].sn,
            doc["doc"].date,
            doc["doc"].valid_from,
            doc["doc"].valid_to,
            doc["doc"].replaces,
            doc["doc"].pub_path,
            doc["doc"].localizes,
            doc["doc"].authors,
            False,
            doc["doc"].category_id,
        )
        for doc in docs
    ]
    total = await rss.dml(sql, data)
    fcs = [
        FileContent(id=doc["doc"].id, folder=MM_FOLDER, content=doc["content"])
        for doc in docs
    ]
    fss.save_files(fcs, overwrite_duplicates=False)

    return total


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
                doc.category_id,
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
