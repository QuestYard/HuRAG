from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiomysql import Connection, Cursor

from dataclasses import dataclass

from .. import logger
from ..utilities import generate_id
from ..dss import with_rdb


@dataclass
class Category:
    id: str | None
    external_id: str | None
    path: str
    description: str | None

    @property
    def level(self) -> int:
        return len(self.path.split("/"))

    @property
    def ancestors(self) -> list[str]:
        pcs = self.path.split("/")
        anc = []
        for i in range(1, len(pcs)):
            anc.append("/".join(pcs[:i]))

        return anc

    @property
    def parent(self) -> str:
        pcs = self.path.split("/")
        return "/".join(pcs[:len(pcs)-1])

    @property
    def name(self) -> str:
        return self.path.split("/")[-1]

    def __post_init__(self):
        if isinstance(self.id, str) and not self.id.strip():
            self.id = None
        if isinstance(self.external_id, str) and not self.external_id.strip():
            self.external_id = None
        self.path = normalize_path(self.path)


def normalize_path(path: str) -> str:
    import re

    p = re.sub(r"^/+|/+$", "", re.sub(r"\s+", "", path))
    if not p:
        raise ValueError("Invalid category path")

    return p


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur")
async def get_category_id_by_path(
    path: str,
    conn: Connection,
    cur: Cursor,
) -> str | None:
    assert conn is not None

    try:
        path = normalize_path(path)
    except ValueError:
        path = ""

    sql = "SELECT id FROM categories WHERE path = %s"
    await cur.execute(sql, (path,))
    results = await cur.fetchall()

    return results[0][0] if results else None


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur")
async def sync_from_csv(
    data: list[dict[str, str]],
    conn: Connection,
    cur: Cursor,
) -> list[tuple[str, str]]:
    assert conn is not None

    from ..utilities import generate_id

    results: list[tuple[str, str]] = []

    for row in data:
        _type = row.get("TYPE", None)
        if not _type:
            continue
        if _type.lower() == "c":
            _path = row.get("CATEGORY_PATH", "")
            _desc = row.get("DOC_TITLE_OR_DESCRIPTION", "")

            try:
                _path = normalize_path(_path)
            except ValueError:
                results.append((f"新增类目 {_path} 路径不合法", "error"))
                continue

            _sql = """
            INSERT INTO categories (id, path, description) VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE description = %s
            """
            _data = (generate_id(), _path, _desc, _desc)
            await cur.execute(_sql, _data)
            results.append((f"新增/修改类目 {_path} 完成", "info"))
        elif _type.lower() == "d":
            _path = row.get("CATEGORY_PATH", "")
            _title = row.get("DOC_TITLE_OR_DESCRIPTION", "").strip()

            try:
                _path = normalize_path(_path)
            except ValueError:
                results.append((f"文档 {_title} 要设置的类目路径不合法", "error"))
                continue

            await cur.execute("SELECT id FROM documents WHERE title = %s", (_title,))
            rows = await cur.fetchall()
            if not rows:
                results.append((f"文档 {_title} 不存在", "error"))
                continue
            _doc_id = rows[0][0]

            await cur.execute("SELECT id FROM categories WHERE path = %s", (_path,))
            rows = await cur.fetchall()
            if not rows:
                results.append((f"文档 {_title} 要设置的类目 {_path} 不存在", "error"))
                continue
            _cat_id = rows[0][0]

            _sql = """
            UPDATE documents SET category_id = %s WHERE id = %s
            """
            await cur.execute(_sql, (_cat_id, _doc_id))
            results.append((f"设置文档 {_title} 的类目为 {_path}", "info"))

    return results


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur")
async def upsert_categories(
    categories: list[Category],
    conn: Connection,
    cur: Cursor,
) -> list[Category]:
    assert conn is not None

    if not categories:
        return []

    saved_categories: list[Category] = []
    for cat in categories:
        if cat.id is None:
            new_id = generate_id()
            try:
                await cur.execute(
                    "INSERT INTO categories (id, external_id, path, description) "
                    "VALUES (%s, %s, %s, %s)",
                    (new_id, cat.external_id, cat.path, cat.description),
                )
                cat.id = new_id
                saved_categories.append(cat)
            except Exception as e:
                logger.error(f"Failed to insert category '{cat.path}': {e}")
        else:
            try:
                await cur.execute(
                    """
                    UPDATE categories
                    SET external_id = %s, path = %s, description = %s
                    WHERE id = %s
                    """,
                    (cat.external_id, cat.path, cat.id, cat.description),
                )
                saved_categories.append(cat)
            except Exception as e:
                logger.error(
                    f"Failed to update category '{cat.path}' (id: {cat.id}): {e}"
                )

    return saved_categories


@with_rdb(connection_arg_name="conn", cursor_arg_name="cur", dict_cursor=True)
async def list_categories(
    path: str = "",
    include_docs: bool = False,
    recursive: bool = False,
    *,
    conn: Connection,
    cur: Cursor,
) -> tuple[list, dict]:
    """Return: list[Category], dict[category_id, list[Document]]"""
    assert conn is not None

    catas = []
    docs = {}
    sql = "SELECT id, external_id, path, description FROM categories "
    try:
        path = normalize_path(path)
    except ValueError:
        path = ""

    if path:
        if recursive:
            sql += f"WHERE path = '{path}' OR path LIKE '{path}/%' "
        else:
            sql += f"WHERE path = '{path}' "
    sql += "ORDER BY path"
    await cur.execute(sql)
    ret = await cur.fetchall()
    catas = [Category(**x) for x in ret]

    if not include_docs or not catas:
        return catas, docs

    from ..schemas import Document

    cata_ids = [x.id for x in catas]
    sql = f"""
    SELECT * FROM documents
    WHERE category_id IN ({",".join(["%s"] * len(cata_ids))})
    """
    await cur.execute(sql, cata_ids)
    ret = await cur.fetchall()
    documents = [Document(**x) for x in ret]
    docs = {x.id: [] for x in catas}
    for doc in documents:
        docs[doc.category_id].append(doc)
    
    return catas, docs
