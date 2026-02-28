from __future__ import annotations
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from aiomysql import Connection, Cursor
    from pymilvus import AsyncMilvusClient

from .. import logger
from ..dss import with_rdb, with_vdb
from ..types import DocumentOrder

from dataclasses import dataclass


@dataclass
class DeletionResults:
    type: Literal["document", "segment"]
    id: str | None = None
    segments: int = 0
    chunks: int = 0
    entities: int = 0
    relations: int = 0
    communities: int = 0


@with_vdb(client_arg_name="cli")
@with_rdb(connection_arg_name="conn", cursor_arg_name="cur")
async def _delete_knowledge(
    id: str,
    id_type: Literal["document", "segment"],
    cli: AsyncMilvusClient,
    conn: Connection,
    cur: Cursor,
) -> DeletionResults:
    await cur.execute(f"SELECT * FROM {id_type}s WHERE id = %s", (id,))
    rows = await cur.fetchall()
    if not rows:
        return DeletionResults(type=id_type)

    ret = DeletionResults(type=id_type, id=id)
    # delete from rdb
    try:
        if id_type == "document":
            await cur.execute("SELECT id FROM segments WHERE document_id = %s", (id,))
            seg_ids = [x[0] for x in await cur.fetchall()]
        else:
            seg_ids = [id]
        ret.segments = len(seg_ids)

        phd = f"({','.join(['%s'] * len(seg_ids))})"
        await cur.execute(f"SELECT id FROM chunks WHERE segment_id IN {phd}", seg_ids)
        chunk_ids = [x[0] for x in await cur.fetchall()]
        # delete document or segment, then will cascade deleting chunks, entity_cites
        # relation_cites where segment_id in seg_ids
        await cur.execute(f"DELETE FROM {id_type}s WHERE id = %s", (id,))
        # find out orphan entities that all segment citations are deleted
        await cur.execute(
            """
            SELECT id FROM entities WHERE NOT EXISTS (
                SELECT 1 FROM entity_cite WHERE entity_cite.entity_id = entities.id
            )
            """
        )
        orphan_entity_ids = [x[0] for x in await cur.fetchall()]
        cut_relation_ids = []
        if len(orphan_entity_ids) > 0:
            # deleting orphan entities will cause relations that start from or end at
            # any of them be cascade deleted, so we should find them out first.
            phd = f"({','.join(['%s'] * len(orphan_entity_ids))})"
            await cur.execute(
                f"""
                SELECT id FROM relations WHERE source_id IN {phd}
                UNION
                SELECT id FROM relations WHERE target_id IN {phd}
                """,
                orphan_entity_ids + orphan_entity_ids,
            )
            cut_relation_ids = [x[0] for x in await cur.fetchall()]
            # now delete orphan entites and cascade relations
            await cur.execute(
                f"DELETE FROM entities WHERE id IN {phd}", orphan_entity_ids
            )
        # find out orphan relations and delete them
        await cur.execute(
            f"""
            SELECT id FROM relations WHERE NOT EXISTS (
                SELECT 1 FROM relation_cite
                WHERE relation_cite.relation_id = relations.id
            )
            """
        )
        orphan_relation_ids = [x[0] for x in await cur.fetchall()]
        if len(orphan_relation_ids) > 0:
            phd = f"({','.join(['%s'] * len(orphan_relation_ids))})"
            await cur.execute(
                f"DELETE FROM relations WHERE id IN {phd}", orphan_relation_ids
            )
        # find out communities containing less than 10 entities and delete them
        await cur.execute(
            """
            SELECT community_id, count(*) AS entity_count FROM community_entity
            GROUP BY community_id HAVING entity_count < 10
            """
        )
        community_ids = [x[0] for x in await cur.fetchall()]
        if len(community_ids) > 0:
            phd = f"({','.join(['%s'] * len(community_ids))})"
            await cur.execute(
                f"DELETE FROM communities WHERE id IN {phd}", community_ids
            )
        await conn.commit()
    except Exception as e:
        await conn.rollback()
        logger.error(f"Delete {id_type} from rdb failed: {e!r}")
        raise

    # delete from vdb
    try:
        if chunk_ids:
            r = await cli.delete("chunks", ids=chunk_ids)
            ret.chunks = r["delete_count"]
        if orphan_entity_ids:
            r = await cli.delete("nodes", ids=orphan_entity_ids)
            ret.entities = r["delete_count"]
        if orphan_relation_ids or cut_relation_ids:
            r = await cli.delete("edges", ids=orphan_relation_ids + cut_relation_ids)
            ret.relations = r["delete_count"]
        if community_ids:
            r = await cli.delete("communities", ids=community_ids)
            ret.communities = r["delete_count"]
    except Exception as e:
        logger.error(f"Delete {id_type} from vdb failed: {e!r}")
        raise

    return ret


async def delete_document(id: str) -> DeletionResults:
    return await _delete_knowledge(id, id_type="document")


async def delete_segment(id: str) -> DeletionResults:
    return await _delete_knowledge(id, id_type="segment")


async def kb_info() -> list[tuple]:
    from ..dss import rss

    stat = await rss.query(
        """
        SELECT COUNT(*), '文档总数:' AS catalog FROM documents
        UNION ALL
        SELECT COUNT(*), '多模态文档:' AS catalog FROM documents WHERE title LIKE '*%%'
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
    from ..dss import rss

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
