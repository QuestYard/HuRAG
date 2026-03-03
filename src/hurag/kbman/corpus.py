from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas import Document

from pathlib import Path
from .. import conf, logger


def doc_convert(src_file: str, tgt_file: str | None, enc: bool) -> str:
    """
    Convert document to UTF-8 encoded text or Markdown.

    Args:
        src_file (str): Path to the source file.
        tgt_file (str | None): Path to the target file. If None, a default
            target file will be created based on the source file name.
        enc (bool): If True, convert from GBK to UTF-8 text. If False,
            convert src_file to Markdown.

    Returns:
        str: Path to the converted target file.
    """
    src = Path(src_file).expanduser().resolve()
    if tgt_file is None:
        if enc:
            tgt = src.with_suffix(".utf8" + src.suffix)
        else:
            tgt = src.with_suffix(".md")
    else:
        tgt = Path(tgt_file)

    result = None
    if enc:
        with open(src, "r", encoding="gbk") as f:
            result = f.read()
    else:
        from markitdown import MarkItDown

        md = MarkItDown(enable_plugins=False)
        result = md.convert(src).markdown

    with open(tgt, "w", encoding="utf-8", newline="\n") as f:
        f.write(result)
    return tgt.as_posix()


def corpus_markup(path: str) -> dict[str, Any]:
    """
    Generate markup file `corpus.json` for documents in the given corpus directory.
    1. Scan the directory for all files except `*.idx`, `meta.json` and `corpus.json`;
    2. For each file, create the metadata entry;
    3. Using metadata in `meta.json` if exists;
    4. Generate the markup dict and save into `corpus.json`

    The structure of `corpus.json` is like:
    ```
    {
        "insert": {
            "filename": { metadata },
            ...
        },
        "update": {},
        "delete": []
    }
    ```

    The values of `update` and `delete` leaves empty.

    Args:
        path (str): Path to the corpus directory

    Returns:
        dict[str, Any]: Dict of `corpus.json`
    """
    import json
    from datetime import datetime

    markups = {"insert": {}, "update": {}, "delete": []}
    metadata = []

    corpus = Path(path).expanduser().resolve()
    if not corpus.exists() or not corpus.is_dir():
        return markups
    meta_file = corpus / "meta.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    metadata = {x["filename"]: x for x in metadata}

    for file in corpus.iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() == ".idx":
            continue
        if file.name.lower() in ["meta.json", "corpus.json"]:
            continue
        if file.name.startswith("."):
            continue

        meta = metadata.get(file.name, {})
        title = file.stem.split("_")[-1]
        if not title.startswith("《"):
            title = f"《{title}"
        if not title.endswith("》"):
            title = f"{title}》"
        markup = {
            "title": meta.get("title", title),
            "sn": meta.get("sn", None),
            "date": meta.get("date", f"{datetime.today():%Y-%m-%d}"),
            "valid_from": meta.get("valid_from", f"{datetime.today():%Y-%m-%d}"),
            "valid_to": meta.get("valid_to", None),
            "replaces": meta.get("replaces", None),
            "pub_path": meta.get("pub_path", conf.app.org_path),
            "localizes": meta.get("localizes", None),
            "authors": meta.get("authors", None),
        }
        markups["insert"][file.name] = markup

    markups["insert"] = {k: markups["insert"][k] for k in sorted(markups["insert"])}
    markup_file = corpus / "corpus.json"
    with open(markup_file, "w", encoding="utf-8") as f:
        json.dump(
            markups,
            f,
            indent=4,
            ensure_ascii=False,
            default=lambda x: f"{x:%Y-%m-%d}" if isinstance(x, datetime) else x,
        )
    return markups


def corpus_split(path: str) -> list[str]:
    """
    Split documents with suffix of .regu, .text, .markdown and .[csv_layout] in the
    given corpus.

    Already splitted documents with an existing indexing file (.idx) will be skipped.

    Args:
        path (str): Path to the directory containing the documents to be splitted.

    Returns:
        tuple: A tuple containing counts of (success, skipped, failed) splits.
    """
    from ..splitters import (
        plain_text_splitter,
        regulation_splitter,
        markdown_splitter,
    )

    corpus = Path(path).expanduser().resolve()
    splitted = []

    # Prepare tasks for documents that need splitting
    for file in corpus.iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() == ".idx":
            continue
        if file.name.lower() in ["meta.json", "corpus.json"]:
            continue
        if file.name.startswith("."):
            continue
        if file.suffix.lower() not in [".regu", ".text", ".markdown"]:
            continue

        if file.with_suffix(".idx").exists():
            logger.warning(f"{file.name} has the indexing file exists, skipped.")
            continue
        # Determine which splitter to use
        match file.suffix.lower():
            case ".regu":
                splitter_func = regulation_splitter
            case ".text":
                splitter_func = plain_text_splitter
            case ".markdown":
                splitter_func = markdown_splitter
            case _:
                splitter_func = plain_text_splitter

        try:
            target = splitter_func(file, file.with_suffix(".idx"))
            logger.info(f"{target.name} is splitted.")
            splitted.append(target.name)
        except Exception as e:
            logger.warning(f"Error and skipped: {e!r}")

    return splitted


def corpus_load(path: Path) -> list[Document]:
    import json
    from ..schemas import Document

    with open(path / "corpus.json", "r", encoding="utf-8") as f:
        markups = json.load(f).get("insert", {})
    docs = [Document.from_corpus(path / fn, meta) for fn, meta in markups.items()]
    return docs
