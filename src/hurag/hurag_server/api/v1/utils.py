from ....schemas import Document, Attachment, Community
from ....dss import with_rdb


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur", dict_cursor=True)
async def list_documents(org_path: str | None, conn, cur) -> list[Document]:
    sql = "SELECT * FROM documents"
    if org_path is not None:
        path = org_path.split("/")
        paths = ["/".join(path[:i]) + "*" for i in range(2, len(path) + 1)]
        paths.append(org_path)
        cond = f"""
        WHERE pub_path IN ({", ".join(["%s"] * len(paths))}) OR pub_path NOT LIKE "/%%"
        """
        await cur.execute(sql + cond, tuple(paths))
    else:
        await cur.execute(sql)

    docs = await cur.fetchall()
    doc_map = {doc["id"]: Document(**doc) for doc in docs}
    await cur.execute("SELECT * FROM attachments")
    atts = await cur.fetchall()
    for att in atts:
        if att["document_id"] not in doc_map:
            continue
        doc_map[att["document_id"]].attachments.append(
            Attachment(id=att["id"], title=att["title"], document_id=att["document_id"])
        )
    await conn.commit()

    return list(doc_map.values())


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur", dict_cursor=True)
async def list_communities(conn, cur) -> list[Community]:
    await cur.execute("SELECT * FROM communities")
    rows = await cur.fetchall()
    await conn.commit()

    return [Community(**row) for row in rows]
