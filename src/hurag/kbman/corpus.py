from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas import Document

from pathlib import Path
from .. import logger


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


def corpus_markup(path: str) -> list[dict]:
    """
    Generate corpus.json markup file for documents in the given folder.
    1. Scan the folder for .txt, .csv, .md files.
    2. For each file, create a markup entry with metadata.
    3. Save all markup entries to corpus.json in the folder.
    4. Return the list of markup entries.

    Args:
        path (str): Path to the folder containing documents.

    Returns:
        list[dict]: List of markup entries for the documents.
    """
    import json
    from datetime import datetime
    from .. import conf

    folder = Path(path).expanduser().resolve()
    markups = []
    for file in folder.iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() not in [".txt", ".csv", ".md"]:
            continue

        markup = {
            "filename": file.name,
            "title": file.stem if file.stem.endswith("》") else f"《{file.stem}》",
            "sn": None,
            "date": "",
            "valid_from": "",
            "valid_to": None,
            "replaces": None,
            "pub_path": conf.app.org_path,
            "localizes": None,
            "authors": None,
            "layout": "normal" if file.suffix.lower() == ".csv" else "text",
        }
        # load metadata if v1 doc
        if file.suffix.lower() != ".md":
            # maybe a HuRAG-pre document, try to get v1_metadata
            meta = _fetch_v1_meta(file)
            # update markup if any v1_metadata exists
            if "title" in meta:
                markup["title"] = meta["title"]
            if "sn" in meta:
                markup["sn"] = meta["sn"] or None
            if "date" in meta:
                markup["date"] = datetime.strptime(meta["date"], "%Y-%m-%d")
                markup["valid_from"] = markup["date"]
            if "expired" in meta:
                markup["valid_to"] = (
                    datetime.strptime(meta["expired"], "%Y-%m-%d")
                    if meta["expired"]
                    else None
                )
            if "authors" in meta:
                markup["authors"] = meta["authors"] or None
            if meta and file.suffix.lower() != ".csv":
                markup["layout"] = "v1_doc"  # actually a HuRAG-pre document
        markups.append(markup)
    # write markup file
    markup_file = folder / "corpus.json"
    with open(markup_file, "w", encoding="utf-8") as f:
        json.dump(
            markups,
            f,
            indent=4,
            ensure_ascii=False,
            default=lambda x: f"{x:%Y-%m-%d}" if isinstance(x, datetime) else x,
        )
    return markups


def _fetch_v1_meta(file: Path) -> dict:
    """
    Fetch metadata from a HuRAG-pre document's .meta file.
    If no metadata fetched, return empty dict.

    Args:
        file (Path): Path to the document file.

    Returns:
        dict: Metadata dictionary.
    """
    ext = ".meta" if file.suffix.lower() == ".csv" else file.suffix
    meta = {}
    with open(file.with_suffix(ext), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == "":
                continue
            if not line.startswith("@"):
                break
            k, v = line.lstrip("@").split("=")
            if k == "domain":
                meta[k] = [d.strip() for d in v.split(",")]
            else:
                meta[k] = v.strip()
    return meta


async def corpus_split(path: str) -> tuple:
    """
    Split documents with layout of 'text' or 'regu' in the given corpus.

    Args:
        path (str): Path to the folder containing corpus.json and documents.

    Returns:
        tuple: A tuple containing counts of (success, skipped, failed) splits.
    """
    import json
    import asyncio
    from ..splitters import (
        plain_text_splitter,
        regulation_splitter,
        markdown_splitter,
    )

    # check for corpus.json
    folder = Path(path).expanduser().resolve()
    corpus = folder / "corpus.json"
    # load corpus.json, loop for 'text' and 'regu' documents
    with open(corpus, "r", encoding="utf-8") as f:
        docs = json.load(f)
    count = [0, 0, 0]  # success, skipped, failed

    # Prepare tasks for documents that need splitting
    tasks_to_run = []
    for doc in docs:
        if doc["layout"] not in ["text", "regu"]:
            # needn't splitting, skip
            logger.warning(f"{doc['filename']}: no need to split, skipped.")
            count[1] += 1
            continue
        src = folder / doc["filename"]
        if not src.exists() or not src.is_file():
            # not exists, skip
            logger.warning(f"{doc['filename']}: not exists, skipped.")
            count[1] += 1
            continue

        # Determine which splitter to use
        match doc["layout"]:
            case "regu":
                splitter_func = regulation_splitter
            case "text" if src.suffix.lower() == ".txt":
                splitter_func = plain_text_splitter
            case "text" if src.suffix.lower() == ".md":
                splitter_func = markdown_splitter
            case _:
                splitter_func = plain_text_splitter

        tasks_to_run.append((splitter_func, src, src.with_suffix(".idx")))

    # Execute tasks using TaskGroup
    async def run_splitter_task(splitter_func, src, tgt):
        try:
            ret = await splitter_func(src, tgt)
            return True, ret
        except Exception as e:
            return False, str(e)

    if tasks_to_run:
        async with asyncio.TaskGroup() as tg:
            tasks = []
            for splitter_func, src, tgt in tasks_to_run:
                task = tg.create_task(run_splitter_task(splitter_func, src, tgt))
                tasks.append(task)

        # Wait for all tasks to complete and collect results
        for task in tasks:
            success, error = task.result()
            if success:
                count[0] += 1
            else:
                logger.warning(f"Error and skipped: {error}")
                count[2] += 1

    return tuple(count)


async def corpus_load(path: Path, exclude_kb_docs: bool = False) -> list[Document]:
    """
    Load documents in the given folder into a list of Document objects.

    Args:
        path (Path):
            Path to the folder containing corpus.json and documents.
        exclude_kb_docs (bool):
            Whether to exclude documents already in the knowledge base.

    Returns:
        list[Document]: List of loaded Document objects.
    """
    import json
    import concurrent.futures
    import asyncio
    from ..schemas import Document

    with open(path / "corpus.json", "r", encoding="utf-8") as f:
        markups = json.load(f)
    if exclude_kb_docs:
        from ..dss import rss

        docs_in_kb = {x[0] for x in await rss.query("SELECT title FROM documents")}
        markups = [m for m in markups if m["title"] not in docs_in_kb]

    loop = asyncio.get_running_loop()
    docs = []

    with concurrent.futures.ThreadPoolExecutor() as pool:
        tasks = [
            loop.run_in_executor(pool, Document().read, path, markup)
            for markup in markups
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                title = markups[i]["title"]
                logger.warning(f"Failed loading {title} and skipped: {result}")
            else:
                docs.append(result)

    return docs
