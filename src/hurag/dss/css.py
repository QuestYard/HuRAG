# Content Storage Service
# - The CRUD service for contents of multimodal documents.
# - The base directory is configured in hurag.yaml as app.extra_docs_dir.
# - Content files saved in sub-directories under the base, we call them the folders.
# - There are two reserved folders: 'extra' and 'attachments'.
# - Contents files named as `<id>.content`, text, utf-8.
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

_base = None  # the base directory of the content storage.


@dataclass
class FileContent:
    id: str
    content: str
    folder: str


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


def get_folder(folder: str) -> Path:
    if not folder.strip():
        raise ValueError("A non-empty content folder name must be provided.")

    folder_path = _base_path() / folder.strip()
    if folder_path.exists() and not folder_path.is_dir():
        raise ValueError(f"Invalid folder: {folder_path.resolve().as_posix()}")

    if not folder_path.exists():
        folder_path.mkdir()

    return folder_path


def save_contents(
    contents: FileContent | list[FileContent],
    *,
    overwrite_duplicates: bool = True,  # leave existing contents unchanged if False
) -> list[Path]:

    if isinstance(contents, FileContent):
        contents = [contents]

    saved = [get_folder(c.folder) / f"{c.id}.content" for c in contents]
    for path, c in zip(saved, contents):
        if path.exists() and not overwrite_duplicates:
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(c.content)

    return saved


def delete_contents(ids: str | list[str], folder: str) -> int:
    ...


def load_contents(ids: str | list[str], folder: str) -> list[FileContent | None]:
    ...
