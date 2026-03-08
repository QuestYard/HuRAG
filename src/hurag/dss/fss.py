# File Storage Service
# - The CRUD service for text files, e.g., content of multimodal documents.
# - The base directory is configured in hurag.yaml as app.extra_docs_dir.
# - Files are saved in sub-directories under the base, we call them the folders.
# - There are two reserved folders: 'multimodals' and 'attachments'.
# - Files are named as `<id>.content`, text, utf-8.
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

_base = None  # the base directory of the content storage.

MM_FOLDER = "multimodals"
AT_FOLDER = "attachments"


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


def save_files(
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


def delete_files(ids: str | list[str] | None, folder: str):
    folder_path = get_folder(folder)

    if not ids:  # remove the whole folder
        paths = [folder_path]
    else:
        if isinstance(ids, str):
            ids = [ids]
        paths = [folder_path / f"{id}.content" for id in ids]

    import shutil

    for path in paths:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


def load_files(ids: str | list[str] | None, folder: str) -> list[FileContent | None]:
    folder_path = get_folder(folder)

    if not ids:  # load the whole folder
        paths = [
            p
            for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() == ".content"
        ]
    else:
        if isinstance(ids, str):
            ids = [ids]
        paths = [folder_path / f"{id}.content" for id in ids]

    ret = []
    for path in paths:
        if not path.exists():
            ret.append(None)
            continue
        with open(path, "r", encoding="utf-8") as f:
            fc = f.read()
        ret.append(FileContent(id=path.stem, content=fc, folder=folder))

    return ret
