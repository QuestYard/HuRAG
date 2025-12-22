from pathlib import Path

def doc_convert(src_file: str, tgt_file: str | None, enc: bool)-> str:
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

    with open(tgt, "w", encoding="utf-8") as f:
        f.write(result)
    return tgt.as_posix()

def corpus_markup(path: str)-> list[dict]:
    import json
    from datetime import datetime
    from . import conf

    folder = Path(path).expanduser().resolve()
    markups = []
    for file in folder.iterdir():
        if not file.is_file():
            continue
        if file.suffix.lower() not in [".txt", ".csv", ".md"]:
            continue

        markup = {
            "filename": file.name,
            "title": (
                file.stem if file.stem.endswith("》")
                else "《" + file.stem + "》"
            ),
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
            # maybe a HuRAG-pre document
            meta = _fetch_v1_meta(file)
            # update markup
            if "title" in meta:
                markup["title"] = meta["title"]
            if "sn" in meta:
                markup["sn"] = meta["sn"] or None
            if "date" in meta:
                markup["date"] = datetime.strptime(meta["date"], "%Y-%m-%d")
                markup["valid_from"] = markup["date"]
            if "expired" in meta:
                markup["valid_to"] = datetime.strptime(
                    meta["expired"],
                    "%Y-%m-%d",
                ) if meta["expired"] else None
            if "authors" in meta:
                markup["authors"] = meta["authors"] or None
            if meta and file.suffix.lower() != ".csv":
                # actually a HuRAG-pre document
                markup["layout"] = "v1_doc"
        markups.append(markup)
    # write markup file
    markup_file = folder / "corpus.json"
    with open(markup_file, "w", encoding="utf-8") as f:
        json.dump(
            markups,
            f,
            indent=4,
            ensure_ascii=False,
            default=lambda x: f"{x:%Y-%m-%d}" if isinstance(x, datetime) else x
        )
    return markups

def _fetch_v1_meta(file: Path)-> dict:
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

def corpus_split(path: str)-> tuple:
    """
    Split documents with layout of 'text' or 'regu' in the given corpus.
    """
    # check for corpus.json
    _console = console()
    folder = Path(path).expanduser().resolve()
    if not folder.exists() or not folder.is_dir():
        return (2, f"{path} 不存在或不是目录")
    corpus = folder / "corpus.json"
    if not corpus.exists() or not corpus.is_file():
        return (2, f"标注文件 '{corpus}' 不存在")
    # load corpus.json, loop for 'text' and 'regu' documents
    try:
        with open(corpus, "r", encoding="utf-8") as f:
            docs = json.load(f)
    except Exception as e:
        return (2, f"标注文件读取失败: {e}")
    count = [0, 0, 0]
    for doc in docs:
        _console.print(f"{doc['filename']} ", end="")
        if doc["layout"] not in ["text", "regu"]:
            _console.print(" needn't splitting, skipped.")
            count[1] += 1
            continue
        src = folder / doc["filename"]
        if not src.exists() or not src.is_file():
            _console.print("not exists, skipped.")
            count[1] += 1
            continue
        match doc["layout"]:
            case "regu":
                ret = regulation_splitter(src, src.with_suffix(".idx"))
            case "text" if src.suffix.lower() == ".txt":
                ret = plain_text_splitter(src, src.with_suffix(".idx"))
            case "text" if src.suffix.lower() == ".md":
                ret = markdown_splitter(src, src.with_suffix(".idx"))
            case _:
                ret = plain_text_splitter(src, src.with_suffix(".idx"))
        if ret[0] == 0:
            _console.print("splitted okay.")
            count[0] += 1
        else:
            _console.print("[red]splitting failed![/]")
            _console.print(f"[red]>>>{ret[1]}[/]")
            count[2] += 1

    return (0, (f"文档分割完成. 分割 {count[0]} 篇, 忽略 {count[1]} 篇, "
                f"失败 {count[2]} 篇, 共计处理 {sum(count)} 篇."))

