def doc_convert(src_file: str, tgt_file: str | None, enc: bool)-> str:
    from pathlib import Path

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

