from __future__ import annotations
from typing import Any, Self, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from dataclasses import dataclass, field
from datetime import datetime


_csv_p = r"^(normal|vertical|cross|plain|stripes|vstripes|rows(_\d+)+|cols(_\d+)+)$"


@dataclass
class Chunk:
    id: str | None = field(default=None)
    seg_id: str | None = field(default=None, compare=False, repr=False)
    text: str | None = field(default=None, compare=False, repr=False)
    seq_no: int = field(default=0, compare=False, repr=False)

    def __repr__(self):
        _txt = self.text or ""
        return (
            f"Chunk(id={self.id}, seq_no={self.seq_no}, brief="
            f"'{' '.join(_txt.split('\n'))[:40]}{'...' if len(_txt) > 40 else ''}')"
        )


@dataclass
class Segment:
    id: str | None = field(default=None)
    doc_id: str | None = field(default=None, compare=False, repr=False)
    seq_no: int = field(default=0, compare=False, repr=False)
    chunks: list[Chunk] = field(default_factory=list, compare=False, repr=False)

    def __repr__(self):
        return (
            f"Segment(id={self.id}, seq_no={self.seq_no}, brief="
            f"'{' '.join(self.text.split('\n'))[:40]}"
            f"{'...' if len(self.text) > 40 else ''}')"
        )

    @property
    def text(self) -> str:
        return "".join([chk.text or "" for chk in self.chunks])


@dataclass
class Attachment:
    id: str | None = field(default=None)
    title: str | None = field(default=None, compare=False)


@dataclass
class Document:
    """
    Support multimodal documents and attachments since v0.3.3:
        - `title`: starts with '*';
        - `is_multimodal`: new property = d.title.startswith("*");
        - `segments`: always [] for multimodal documents;
        - `kg_built`: always False for multimodal documents;
        - `attachments`: list[Attachment].
    """

    id: str | None = field(default=None)
    title: str | None = field(default=None, compare=False)
    sn: str | None = field(default=None, compare=False)
    date: datetime | None = field(default=None, compare=False, repr=False)
    valid_from: datetime | None = field(default=None, compare=False, repr=False)
    valid_to: datetime | None = field(default=None, compare=False, repr=False)
    replaces: str | None = field(default=None, compare=False, repr=False)  # title
    pub_path: str | None = field(default=None, compare=False)
    localizes: str | None = field(default=None, compare=False, repr=False)  # title
    authors: str | None = field(default=None, compare=False, repr=False)
    segments: list[Segment] = field(default_factory=list, compare=False, repr=False)
    kg_built: bool = field(default=False, compare=False, repr=False)
    attachments: list[Attachment] = field(default_factory=list, compare=False)

    @property
    def is_multimodal(self) -> bool | None:
        return self.title.startswith("*") if self.title else None

    @property
    def fulltext(self):
        return "".join([seg.text for seg in self.segments])

    @classmethod
    def from_corpus(cls, path: Path, meta: dict[str, Any]) -> Self:
        """Load documents in the given corpus."""
        import re

        if not path.exists() or not path.is_file():
            return cls()

        # Load content for regu, text, markdown and layout-csv docs,
        # Mark multimodal docs by adding the leading ast to the title.
        doc = cls(**meta)
        ext = path.suffix.lstrip(".").lower()
        if ext in ["regu", "text", "markdown"]:
            idx_fp = path.with_suffix(".idx")
            if idx_fp.exists() and idx_fp.is_file():
                doc._read_text(idx_fp)
        elif re.match(_csv_p, ext):
            doc._read_csv(path, ext)
        else:
            doc.title = f"*{doc.title}"

        # Load attachments
        att_path = path.with_suffix("")
        if att_path.exists() and att_path.is_dir():
            doc.attachments = sorted(
                [
                    Attachment(title=att.name)
                    for att in att_path.iterdir()
                    if att.is_file()
                ],
                key=lambda x: x.title or "",
            )

        return doc

    def _read_text(self, file):
        from ..constants import CHK_DELIMITER, SEG_DELIMITER

        with open(file, "r", encoding="utf-8", newline="\n") as f:
            st_list = f.read().split(SEG_DELIMITER)[1:]
        for si, st in enumerate(st_list):
            seg = Segment(seq_no=si)
            ct_list = st.split(CHK_DELIMITER)
            for ci, ct in enumerate(ct_list):
                seg.chunks.append(Chunk(text=ct, seq_no=ci))
            self.segments.append(seg)

    def _read_csv(self, file, layout):
        import csv

        with open(file, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            x = []
            for row in reader:
                x.append(row)
        if layout[:4] in ["vert", "vstr", "cols"]:
            x = list(map(list, zip(*x)))
        si = 0
        if layout == "plain":
            for row in x:
                for cell in row:
                    seg = Segment(seq_no=si)
                    chk = Chunk(text=cell)
                    seg.chunks.append(chk)
                    self.segments.append(seg)
                    si += 1
        elif layout == "cross":
            for i in range(1, len(x)):
                for j in range(1, len(x[i])):
                    t = f"{x[0][j]}, {x[i][0]}: {x[i][j]}"
                    seg = Segment(seq_no=si)
                    chk = Chunk(text=t)
                    seg.chunks.append(chk)
                    self.segments.append(seg)
                    si += 1
        elif layout[:5] in ["rows_", "cols_"]:
            _list = [int(i) for i in layout[5:].split("_") if i.strip()]
            _list.append(len(x))
            for h in range(len(_list) - 1):
                head = x[_list[h]]
                for row in x[_list[h] + 1 : _list[h + 1]]:
                    dic = dict(zip(head, row))
                    t = "\n".join([f"{k}: {v}" for k, v in dic.items()])
                    seg = Segment(seq_no=si)
                    chk = Chunk(text=t)
                    seg.chunks.append(chk)
                    self.segments.append(seg)
                    si += 1
        elif layout in ["stripes", "vstripes"]:
            for h in range(0, len(x), 2):
                if h == len(x) - 1:
                    break
                dic = dict(zip(x[h], x[h + 1]))
                t = "\n".join([f"{k}: {v}" for k, v in dic.items()])
                seg = Segment(seq_no=si)
                chk = Chunk(text=t)
                seg.chunks.append(chk)
                self.segments.append(seg)
                si += 1
        else:
            head = x[0]
            for row in x[1:]:
                dic = dict(zip(head, row))
                t = "\n".join([f"{k}: {v}" for k, v in dic.items()])
                seg = Segment(seq_no=si)
                chk = Chunk(text=t)
                seg.chunks.append(chk)
                self.segments.append(seg)
                si += 1

    @classmethod
    async def from_db(
        cls,
        ids: str | list[str] | None = None,
        titles: str | list[str] | None = None,
    ) -> list[Self]:
        """
        Load documents from database by IDs and titles.

        Both IDs and titles are used to load documents from database together.
        If only one of them is given, load documents by that only.

        Args:
            ids: IDs of the documents to load.
            titles: titles of the documents to load.

        Return:
            A list of loaded documents
        """
        doc_map = {}
        seg_map = {}
        chunks = []

        ids = ids or []
        if isinstance(ids, str):
            ids = [ids]
        titles = titles or []
        if isinstance(titles, str):
            titles = [titles]

        if not ids and not titles:
            return []

        from ..dss import rss
        from aiomysql import DictCursor

        pool = await rss.get_pool()
        async with pool.acquire() as conn, conn.cursor(DictCursor) as cur:
            select = "SELECT * FROM documents WHERE "
            cond_id = f"id IN ({','.join(['%s'] * len(ids))})" if ids else ""
            cond_tt = f"title IN ({','.join(['%s'] * len(titles))})" if titles else ""
            sql = f"{select}{' OR '.join(filter(None, [cond_id, cond_tt]))}"
            await cur.execute(sql, ids + titles)
            rows = await cur.fetchall()
            doc_map = {row["id"]: cls(**row) for row in rows}
            # load segments and chunks
            doc_ids = tuple(doc_map)
            sql_seg = f"""
            SELECT id, document_id as doc_id, seq_no
            FROM segments
            WHERE document_id IN ({",".join(["%s"] * len(doc_ids))})
            ORDER BY doc_id, seq_no
            """
            await cur.execute(sql_seg, doc_ids)
            seg_rows = await cur.fetchall()
            seg_map = {row["id"]: Segment(**row) for row in seg_rows}
            seg_ids = tuple(seg_map)
            sql_chk = f"""
            SELECT id, segment_id as seg_id, text, seq_no
            FROM chunks
            WHERE segment_id IN ({",".join(["%s"] * len(seg_ids))})
            ORDER BY seg_id, seq_no
            """
            await cur.execute(sql_chk, seg_ids)
            chk_rows = await cur.fetchall()
            chunks = [Chunk(**row) for row in chk_rows]
            # assemble documents
            for chk in chunks:
                seg_map[chk.seg_id].chunks.append(chk)
            for seg in seg_map.values():
                doc_map[seg.doc_id].segments.append(seg)
            # load attachments
            sql_att = f"""
            SELECT id, title, document_id FROM attachments
            WHERE document_id IN ({','.join(['%s'] * len(doc_map))})
            """
            await cur.execute(sql_att, tuple(doc_map))
            atts = await cur.fetchall()
            for att in atts:
                doc_map[att["document_id"]].attachments.append(
                    Attachment(id=att["id"], title=att["title"])
                )

        return list(doc_map.values())
