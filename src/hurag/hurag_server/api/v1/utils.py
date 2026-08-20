from ....schemas import Document, Attachment, Community
from ....dss import with_rdb


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur", dict_cursor=True)
async def list_documents(
    org_path: str | None,
    category_ids: list[str],
    title_keywords: list[str],
    conn,
    cur,
) -> list[Document]:
    sql = "SELECT * FROM documents"
    conds = []
    args = []
    if org_path is not None:
        path = org_path.split("/")
        paths = ["/".join(path[:i]) + "*" for i in range(2, len(path) + 1)]
        paths.append(org_path)
        placeholder = ", ".join(["%s"] * len(paths))
        conds.append(
            f"(pub_path IN ({placeholder}) OR pub_path NOT LIKE '/%%')"
        )
        args.extend(paths)
    if category_ids:
        conds.append(
            f"category_id IN ({','.join(['%s'] * len(category_ids))})"
        )
        args.extend(category_ids)
    if title_keywords:
        keywords = "|".join(title_keywords)
        conds.append(
            f"title REGEXP '{keywords}'"
        )
    cond = " AND ".join(conds)
    if cond:
        sql = f"{sql} WHERE {cond}"

    await cur.execute(sql, tuple(args))

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
