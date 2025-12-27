from __future__ import annotations
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import Document

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
    embeddings: dict[Literal["dense_vecs", "sparse_vecs"], Any],
) -> list[Document]:
    """
    Indexing documents into the knowledge base with provided embeddings.

    Args:
        docs (list[Document]):
            List of Document objects to be indexed.
        embeddings (dict):
            A dictionary containing 'dense_vecs' and 'sparse_vecs' for indexing.

    Returns:
        list[Document]: List of successfully indexed Document objects.
    """
    ...