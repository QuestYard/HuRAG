import aiofiles
from pathlib import Path

from .constants import CHK_DELIMITER, SEG_DELIMITER, TXT_SEPARATORS

async def plain_text_splitter(src: str | Path, tgt: str | Path | None = None) -> str:
    """
    Split given plain text document and save into the 'tgt' file if given,
    otherwise the result will be written into the 'src' file itself.

    The whole text will be splitted into plain chunks, i.e., each segment
    contains exactly one chunk, with chunk-size = 500 and overlap = 100.
    """
    if isinstance(src, str):
        src = Path(src)
    if tgt is None:
        tgt = Path(src)
    elif isinstance(tgt, str):
        tgt = Path(tgt)

    async with aiofiles.open(src, "r", encoding="utf-8") as f:
        content = await f.read()
    # split
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=True,
        separators=TXT_SEPARATORS,
    )
    texts = text_splitter.split_text(content)
    # save to target file, append a newline to each segment.
    async with aiofiles.open(tgt, "w", encoding="utf-8", newline="\n") as f:
        await f.write(SEG_DELIMITER)
        await f.write(("\n" + SEG_DELIMITER).join(texts).strip())
        await f.write("\n")

    return tgt.as_posix()

async def markdown_splitter(src: str | Path, tgt: str | Path | None = None) -> str:
    """
    Split given markdown document and save into the 'tgt' file if given,
    otherwise the result will be written into the 'src' file itself.

    The whole text will be splitted on markdown headers (3 levels at most),
    each header per segment. Segments will be further splitted into one or
    several chunks with chunk-size = 500 and overlap = 0.
    """
    if isinstance(src, str):
        src = Path(src)
    if tgt is None:
        tgt = Path(src)
    elif isinstance(tgt, str):
        tgt = Path(tgt)

    async with aiofiles.open(src, "r", encoding="utf-8") as f:
        content = await f.read()
    # split
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_text_splitters import MarkdownHeaderTextSplitter
    headers_to_split_on = [
        ("#", "#"),
        ("##", "##"),
        ("###", "###"),
        ("####", "####"),
        ("#####", "#####"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(content)
    segs = ["" for _ in range(len(md_header_splits))]
    for i, seg in enumerate(md_header_splits):
        for k, v in seg.metadata.items():
            segs[i] += f"{k} {v}\n"
        segs[i] += seg.page_content
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=0,
        length_function=len,
        is_separator_regex=True,
        separators=TXT_SEPARATORS,
    )
    # save to target file, append a newline to each segment.
    async with aiofiles.open(tgt, "w", encoding="utf-8", newline="\n") as f:
        for seg in segs:
            await f.write(SEG_DELIMITER)
            if len(seg) < 500:
                await f.write(f"{seg}\n")
                continue
            chks = text_splitter.split_text(seg)
            await f.write(("\n" + CHK_DELIMITER).join(chks))
            await f.write("\n")

    return tgt.as_posix()

async def regulation_splitter(src: str | Path, tgt: str | Path | None = None) -> str:
    """
    Split given regulation-like document and save into the 'tgt' file if given,  
    otherwise the result will be written into the 'src' file itself.

    The whole text will be splitted by clauses, one segment per clause.
    Segments longer than 500 characters will be splitted into several chunks.
    """
    import re
    if isinstance(src, str):
        src = Path(src)
    if tgt is None:
        tgt = Path(src)
    elif isinstance(tgt, str):
        tgt = Path(tgt)
    async with aiofiles.open(src, "r", encoding="utf-8") as f:
        _text = [re.sub(r"\s", " ", l).strip() async for l in f if l.strip()]
    p_vol = re.compile(r"^第\s*[一二三四五六七八九十零百千]+\s*编")
    p_sub = re.compile(r"^第\s*[一二三四五六七八九十零百千]+\s*分编")
    p_cha = re.compile(r"^第\s*[一二三四五六七八九十零百千]+\s*章")
    p_sec = re.compile(r"^第\s*[一二三四五六七八九十零百千]+\s*节")
    p_art = re.compile(r"^第\s*[一二三四五六七八九十零百千]+\s*条")
    p_att = re.compile(r"^附件\s*\d+")

    _segs = []
    _chks = []
    _vol = ""
    _sub = ""
    _cha = ""
    _sec = ""
    _seg = None
    _chk = None
    for line in _text:
        if re.match(p_vol, line):
            _vol = line + " "
            _sub = ""
            _cha = ""
            _sec = ""
        elif re.match(p_sub, line):
            _sub = line + " "
            _cha = ""
            _sec = ""
        elif re.match(p_cha, line):
            _cha = line + " "
            _sec = ""
        elif re.match(p_sec, line):
            _sec = line + " "
        elif re.match(p_art, line) or re.match(p_att, line):
            if _seg is not None:
                _chks.append(_chk)
                _seg["end"] = len(_chks)
                _segs.append(_seg)
            _seg = {"start": len(_chks), "end": -1}
            _chk = _vol + _sub + _cha + _sec + line + "\n"
        else:
            if len(_chk) + len(line) < 500:
                _chk += line + "\n"
            else:
                _chks.append(_chk)
                _seg["end"] = len(_chks)
                _chk = line + "\n"
    # append the last chunk
    _chks.append(_chk)
    _seg["end"] = len(_chks)
    _segs.append(_seg)

    # save to target file
    async with aiofiles.open(tgt, "w", encoding="utf-8", newline="\n") as f:
        await f.write(SEG_DELIMITER)
        _text = []
        for seg in _segs:
            st = seg["start"]
            ed = seg["end"]
            _text.append(CHK_DELIMITER.join(_chks[st:ed]))
        await f.write(SEG_DELIMITER.join(_text).strip())
        await f.write("\n")

    return tgt.as_posix()
