# Content Storage Service
# - The CRUD service for contents of multimodal documents and document attachments.
# - The base directory is configured in hurag.yaml as app.extra_docs_dir.
# - The contents of multimodal documents stored in `<extra_docs_dir>/extra`.
# - The contents of attachments stored in `<extra_docs_dir>/attachments`.
# - Contents files named as `<uuid>.content`, text, utf-8.
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

_base = None


@dataclass
class FileContent:
    id: str | None = None
    title: str | None = None
    document_title: str | None = None
    content: str | None = None


def _base_path() -> Path:
    global _base

    if _base is None:
        from .. import conf
        _base = Path.cwd() / conf.app.extra_docs_dir
        if _base.exists() and not _base.is_dir():
            raise ValueError(f"Invalid extra_docs_dir: {_base.resove().as_posix()}")
        if not _base.exists():
            _base.mkdir()

    return _base


def _attachments_path() -> Path:
    att_path = _base_path() / "attachments"
    if att_path.exists() and not att_path.is_dir():
        raise ValueError(f"Invalid attachments dir: {att_path.resolve().as_posix()}")
    if not att_path.exists():
        att_path.mkdir()

    return att_path

def _documents_path() -> Path:
    doc_path = _base_path() / "attachments"
    if doc_path.exists() and not doc_path.is_dir():
        raise ValueError(f"Invalid attachments dir: {doc_path.resolve().as_posix()}")
    if not doc_path.exists():
        doc_path.mkdir()

    return doc_path


async def query_attachments(contents: FileContent | list[FileContent]):
    ...

def save_contents(
    contents: FileContent | list[FileContent],
    *,
    replace_exists: bool = False,
) -> list[FileContent]:
    from ..utilities import generate_id
    from . import rss
    
    att_dir = _attachments_path()
    doc_dir = _documents_path()

    if isinstance(contents, FileContent):
        contents = [contents]

    atts = [c for c in contents if c.document_title and c.title]
    docs = [c for c in contents if not c.document_title and c.title]

