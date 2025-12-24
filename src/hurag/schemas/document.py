from __future__ import annotations
from typing import Self, TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Chunk:
    id: str = field(default=None)
    seg_id: str = field(default=None, compare=False, repr=False)
    text: str = field(default=None, compare=False, repr=False)
    seq_no: int = field(default=0, compare=False, repr=False)

    def __repr__(self):
        return (
            f"Chunk(id={self.id}, seq_no={self.seq_no}, brief="
            f"'{' '.join(self.text.split('\n'))[:40]}"
            f"{'...' if len(self.text) > 40 else ''}')"
        )

@dataclass
class Segment:
    id: str = field(default=None)
    doc_id: str = field(default=None, compare=False, repr=False)
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
        return "".join([chk.text for chk in self.chunks])

@dataclass
class Document:
    id: str = field(default=None)
    title: str = field(default=None, compare=False)
    sn: str = field(default=None, compare=False)
    date: datetime = field(default=None, compare=False, repr=False)
    valid_from: datetime = field(default=None, compare=False, repr=False)
    valid_to: datetime = field(default=None, compare=False, repr=False)
    replaces: str = field(default=None, compare=False, repr=False)  # title
    pub_path: str = field(default=None, compare=False)
    localizes: str = field(default=None, compare=False, repr=False) # title
    authors: str = field(default=None, compare=False, repr=False)
    segments: list[Segment] = field(default_factory=list, compare=False, repr=False)
    kg_built: bool = field(default=False, compare=False, repr=False)

    @property
    def fulltext(self):
        return "".join([seg.text for seg in self.segments])

    def read(self, path: Path, markup: dict) -> Self:
        """
        Read metadat and content from the document given by path and markup.
        """
        path = path / markup["filename"]
        if markup["layout"] in ["text", "regu", "manual"]:
            path = path.with_suffix(".idx")
        # clear self and read metadata
        self.id = None
        self.title = markup["title"]
        self.sn = markup["sn"]
        self.date = datetime.strptime(markup["date"], "%Y-%m-%d")
        self.valid_from = datetime.strptime(markup["valid_from"], "%Y-%m-%d")
        self.valid_to = markup["valid_to"] and datetime.strptime(
            markup["valid_to"],
            "%Y-%m-%d",
        )
        self.replaces = markup["replaces"]
        self.pub_path = markup["pub_path"]
        self.localizes = markup["localizes"]
        self.authors = markup["authors"]
        self.segments.clear()
        self.kg_built = False
        # read segments and chunks
        if markup["layout"] in ["text", "regu", "v1_doc", "manual"]:
            self._read_text(path)
        else:
            self._read_csv(path, markup["layout"])

        return self

    def _read_text(self, file):
        from .. import OPTIONS as opt

        with open(file, "r", encoding="utf-8", newline="\n") as f:
            st_list = f.read().split(opt["chunk"]["seg_delimiter"])[1:]
        for si, st in enumerate(st_list):
            seg = Segment(seq_no=si)
            ct_list = st.split(opt["chunk"]["delimiter"])
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
                    seg = Segment(seq_no = si)
                    chk = Chunk(text = cell)
                    seg.chunks.append(chk)
                    self.segments.append(seg)
                    si += 1
        elif layout == "cross":
            for i in range(1, len(x)):
                for j in range(1, len(x[i])):
                    t = f"{x[0][j]}, {x[i][0]}: {x[i][j]}"
                    seg = Segment(seq_no = si)
                    chk = Chunk(text = t)
                    seg.chunks.append(chk)
                    self.segments.append(seg)
                    si += 1
        elif layout[:4] in ["rows", "cols"]:
            _list = [int(i) for i in layout[5:].split(",") if i.strip()]
            _list.append(len(x))
            for h in range(len(_list) - 1):
                head = x[_list[h]]
                for row in x[_list[h]+1:_list[h+1]]:
                    dic = dict(zip(head, row))
                    t = "\n".join([f"{k}: {v}" for k, v in dic.items()])
                    seg = Segment(seq_no = si)
                    chk = Chunk(text = t)
                    seg.chunks.append(chk)
                    self.segments.append(seg)
                    si += 1
        elif layout in ["stripes", "vstripes"]:
            for h in range(0, len(x), 2):
                if h == len(x) - 1:
                    break
                dic = dict(zip(x[h], x[h+1]))
                t = "\n".join([f"{k}: {v}" for k, v in dic.items()])
                seg = Segment(seq_no = si)
                chk = Chunk(text = t)
                seg.chunks.append(chk)
                self.segments.append(seg)
                si += 1
        else:
            head = x[0]
            for row in x[1:]:
                dic = dict(zip(head, row))
                t = "\n".join([f"{k}: {v}" for k, v in dic.items()])
                seg = Segment(seq_no = si)
                chk = Chunk(text = t)
                seg.chunks.append(chk)
                self.segments.append(seg)
                si += 1

