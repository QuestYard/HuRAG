from ..schemas import Document, Attachment, Community
from ..dss import with_rdb

@with_rdb(connection_arg_name="conn", cursor_arg_name="cur", dict_cursor=True)
async def list_documents(conn, cur) -> list[Document]:
    await cur.execute("SELECT * FROM documents")
    docs = await cur.fetchall()
    doc_map = {doc["id"]: Document(**doc) for doc in docs}
    await cur.execute("SELECT * FROM attachments")
    atts = await cur.fetchall()
    for att in atts:
        doc_map[att["document_id"]].attachments.append(
            Attachment(id=att["id"], title=att["title"])
        )
    await conn.commit()

    return list(doc_map.values())


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur", dict_cursor=True)
async def list_communities(conn, cur) -> list[Community]:
    await cur.execute("SELECT * FROM communities")
    rows = await cur.fetchall()
    await conn.commit()

    return [Community(**row) for row in rows]
