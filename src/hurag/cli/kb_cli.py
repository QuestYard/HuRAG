import typer

from . import (
    HURAG_EPILOG,
    show_msg,
    with_async_spinner,
    async_cmd,
)
from ..types import DocumentOrder

app = typer.Typer(
    help="QuestYard HuRAG CLI - KnowledgeBase Management Tools",
    add_completion=False,
    epilog=HURAG_EPILOG,
)


@app.command("init", epilog=HURAG_EPILOG)
def init():
    """初始化后台知识库，原有数据将被全部清除，请慎重操作。"""
    ensure = input("初始化将清空数据并重建后端数据库，请输入 Y 确认: ")
    if not ensure.strip().lower().startswith("y"):
        show_msg("用户取消初始化操作", style="info")
        return

    @async_cmd
    @with_async_spinner(text="初始化知识库中...", style="info")
    async def _init():
        from ..dss import init_ds

        try:
            await init_ds()
            show_msg("HuRAG 知识库初始化完成", style="info")
        except Exception as e:
            show_msg(f"HuRAG 知识库初始化失败: {e}", style="error", err=e)

    _init()


@app.command("init-webui", epilog=HURAG_EPILOG)
def init_webui():
    """初始化 HuRAG WebUI 应用，原有数据将被全部清除，请慎重操作。"""
    ensure = input("WebUI 初始化将清空数据、重建数据库和缓存，请输入 Y 确认: ")
    if not ensure.strip().lower().startswith("y"):
        show_msg("用户取消 WebUI 初始化操作", style="info")
        return

    @async_cmd
    @with_async_spinner(text="初始化 WebUI 应用...", style="info")
    async def _init():
        from ..hurag_webui import init_webui

        try:
            await init_webui()
            show_msg("HuRAG WebUI 初始化完成", style="info")
        except Exception as e:
            show_msg(f"HuRAG WebUI 初始化失败: {e!r}", style="error", err=e)

    _init()


@app.command("info", epilog=HURAG_EPILOG)
@async_cmd
async def info():
    """查看后台知识库信息。"""
    from ..kbman import kb_info

    try:
        stat = await kb_info()
    except Exception:
        show_msg("数据库尚未初始化，请先用 hurag init 初始化数据库", style="error")
        return

    from rich.table import Table
    from . import console

    table = Table(title="知识库统计信息", title_style="bold italic", box=None)
    table.add_column(
        "类别",
        width=24,
        justify="left",
        style="bold cyan",
        header_style="bold underline",
    )
    table.add_column(
        "数量",
        width=12,
        justify="right",
        style="bold green",
        header_style="bold underline",
    )
    for count, catalog in stat:
        table.add_row(catalog, f"{count:,}")
    console.print(table)


@app.command("list", epilog=HURAG_EPILOG)
@async_cmd
async def kb_list(
    keyword: str | None = typer.Option(
        None,
        "--keyword",
        "-k",
        help="文档标题关键词, 支持模糊匹配",
    ),
    order: DocumentOrder = typer.Option(
        "title",
        "--order",
        "-o",
        help="排序字段: 标题, 生效日期, 发布机构",
    ),
):
    """列出后台知识库中的文档列表及文档相关信息。"""
    from ..kbman import list_documents

    try:
        docs = await list_documents(keyword=keyword, order=order)
    except Exception:
        show_msg("数据库尚未初始化，请先用 hurag init 初始化数据库", style="error")
        return

    from rich.table import Table
    from . import console

    doc_info = [
        (
            f"{doc[0].lstrip('*')}（{doc[1]}）" if doc[1] else doc[0].lstrip("*"),
            doc[2].strftime("%Y-%m-%d"),  # valid_from
            doc[3].strftime("%Y-%m-%d") if doc[3] else "",  # valid_to
            doc[4].split("/")[-1].rstrip("*"),  # pub_org
            doc[4][0] == "/" and doc[4][-1] != "*",  # not propagate
            f"{doc[5]:,}",  # segments
            f"{doc[6]:,}",  # entities
            doc[0].startswith("*"),  # is extra document
        )
        for doc in docs
    ]
    table = Table(box=None)
    table.add_column("序号", header_style="underline", width=6, justify="center")
    table.add_column("文档标题", header_style="underline", width=100, no_wrap=True)
    table.add_column("生效日期", header_style="underline", width=12, justify="center")
    table.add_column("失效日期", header_style="underline", width=12, justify="center")
    table.add_column("发布机构", header_style="underline", width=28, no_wrap=True)
    table.add_column("仅本级", header_style="underline", width=8, justify="center")
    table.add_column("段落数", header_style="underline", width=8, justify="right")
    table.add_column("实体数", header_style="underline", width=8, justify="right")
    table.add_column("多模态", header_style="underline", width=8, justify="center")

    for ind, inf in enumerate(doc_info):
        table.add_row(
            f"{ind + 1}",
            inf[0],
            inf[1],
            inf[2],
            inf[3],
            "是" if inf[4] else "否",
            inf[5],
            inf[6],
            "是" if inf[7] else "否",
        )
    console.print(table)
    console.print()


@app.command("store", epilog=HURAG_EPILOG)
@async_cmd
async def store(path: str = typer.Argument(..., help="需要入库的文集所在目录")):
    """
    以文集为单位，读取已经标注和分割完毕的文档进入知识库。

    注意：仅完成向量化入库，不提取知识图谱，图谱管理请使用 kgraph 命令。
    """
    from pathlib import Path

    corpus = Path(path).expanduser().resolve()
    if not corpus.is_dir():
        show_msg(f"指定的文集目录 {path} 不存在或不是一个目录", style="error")
        return

    show_msg(f"加载文集 {path} 中待入库的文档...", style="info")

    import json
    from ..kbman import corpus_load, get_category_id_by_path

    try:
        with open(corpus / "corpus.json", "r", encoding="utf-8") as f:
            markups = json.load(f)

        _ins = markups.get("insert", {})
        for d in _ins.values():
            cate = d.pop("category", None)
            d["category_id"] = await get_category_id_by_path(cate) if cate else None

        docs = corpus_load(corpus, _ins)
        show_msg(f"加载完成，共 {len(docs)} 份文档待入库", style="info")
    except Exception as e:
        show_msg(f"加载文集 {path} 失败: {e}", style="error", err=e)
        return

    # query existing documents, set IDs.
    from ..kbman import check_existance

    await check_existance(docs)
    new_multimodals = [doc for doc in docs if not doc.id and doc.is_multimodal]
    new_normal_docs = [doc for doc in docs if not doc.id and not doc.is_multimodal]

    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeRemainingColumn,
        MofNCompleteColumn,
    )
    from ..llm import extract_files
    from ..indexer import save_multimodal_docs

    # multimodal documents
    if new_multimodals:
        _total = len(new_multimodals)
        show_msg("提取待入库多模态文档内容...", style="info")
        # extract contents and save
        fn_doc_map = {
            fn: {"doc": doc, "content": None}
            for doc in new_multimodals
            for fn, m in markups["insert"].items()
            if doc.title == f"*{m['title']}"
        }
        files = [corpus / fn for fn in fn_doc_map]
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(elapsed_when_finished=True),
                MofNCompleteColumn(),
            ) as progress:
                task = progress.add_task("多模态文档内容提取", total=_total)
                async for ret in extract_files(files):
                    # ret: {"path": src_file_path, "content": content}
                    if ret is not None:
                        fn_doc_map[ret["path"].name]["content"] = ret["content"]
                    progress.update(task, advance=1)
        except Exception as e:
            show_msg(f"提取多模态文档内容失败: {e!r}", style="error", err=e)
            return

        show_msg("新增多模态文档内容保存入数据库...", style="info")
        # save new multimodal documents
        try:
            _total = await save_multimodal_docs(
                [v for v in fn_doc_map.values() if v["content"] is not None]
            )
            show_msg(f"{_total} 份新增多模态文档入库完成", style="info")
        except Exception as e:
            show_msg(f"保存新增多模态文档失败: {e!r}", style="error", err=e)
            return
    else:
        show_msg("文集中没有新增的多模态文档", style="warning")

    # normal documents
    if new_normal_docs:
        show_msg("向量化待入库文本文档...", style="info")
        from ..llm.embedder import embed_documents

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(elapsed_when_finished=True),
                MofNCompleteColumn(),
            ) as progress:
                task = progress.add_task("文档文本向量化", total=len(new_normal_docs))
                embeddings = []
                async for vecs, _ in embed_documents(new_normal_docs, batch_type=1):
                    embeddings.append(vecs)
                    progress.update(task, advance=1)
            show_msg(f"{len(embeddings)} 份文档向量化完成", style="info")
        except Exception as e:
            show_msg(f"文档向量化失败: {e!r}", style="error", err=e)
            return

        show_msg("文本文档内容保存入数据库...", style="info")
        from ..indexer import indexing_documents

        try:
            ds, ss, cs = await indexing_documents(new_normal_docs, embeddings)
            show_msg(f"{ds} 份文档，共 {ss} 知识段、{cs} 文本块入库完成", style="info")
        except Exception as e:
            show_msg(f"文档内容保存入库失败: {e}", style="error", err=e)
            return
    else:
        show_msg("文集中没有新增的文本文档", style="warning")

    # attachments
    show_msg("检查需要新增的文档附件...", style="info")
    fn_doc_att_map = {
        (Path(Path(fn).stem) / att.title).as_posix(): {
            "doc_id": doc.id,
            "att": att,
            "content": None,
        }
        for doc in docs
        for att in doc.attachments
        for fn, m in markups["insert"].items()
        if att.title and doc.title and doc.title.lstrip() == m["title"]
    }

    from ..kbman import check_attachments_existance

    await check_attachments_existance(list(fn_doc_att_map.values()))
    new_atts = {k: v for k, v in fn_doc_att_map.items() if v["att"].id is None}

    if new_atts:
        _total = len(new_atts)
        show_msg("提取新增文档附件的内容...", style="info")
        # extract content of attachments
        files = [corpus / fn for fn in new_atts]
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(elapsed_when_finished=True),
                MofNCompleteColumn(),
            ) as progress:
                task = progress.add_task("文档附件内容提取", total=_total)
                async for ret in extract_files(files):
                    # ret: {"path": src_file_path, "content": content}
                    if ret is not None:
                        _rpath = ret["path"].relative_to(corpus).as_posix()
                        new_atts[_rpath]["content"] = ret["content"]
                    progress.update(task, advance=1)
        except Exception as e:
            show_msg(f"提取文档附件内容失败: {e!r}", style="error", err=e)
            return

        show_msg("新增文档附件内容保存入数据库...", style="info")
        from ..indexer import save_attachments

        try:
            _total = await save_attachments(
                [v for v in new_atts.values() if v["content"] is not None]
            )
            show_msg(f"{_total} 份新增文档附件入库完成", style="info")
        except Exception as e:
            show_msg(f"保存新增文档附件失败: {e!r}", style="error", err=e)
            return
    else:
        show_msg("文集中没有需要新增的文档附件", style="warning")

    # update
    if markups["update"]:
        show_msg("修改文档元数据...", style="info")
        from ..kbman import update_metadata

        _total = len(markups["update"])
        try:
            for title, new_meta in markups["update"].items():
                _rows = await update_metadata(title=title, new_meta=new_meta)
                _updated = ",".join([f"{k} 修改为 {v}" for k, v in new_meta.items()])
                _affected = f"共影响 {_rows} 份文档"
                show_msg(
                    f"{title} 元数据修改完成: {_updated}, {_affected}", style="info"
                )
        except Exception as e:
            show_msg(f"修改文档元数据失败: {e!r}", style="error", err=e)
            return
    else:
        show_msg("文集中没有指定修改文档元数据", style="warning")

    # delete
    if markups["delete"]:
        show_msg("删除文档及文档附件...", style="info")
        from ..kbman import delete_documents_by_title, delete_attachments_by_title

        docs_to_del = [x for x in markups["delete"] if isinstance(x, str)]
        atts_to_del = [x for x in markups["delete"] if not isinstance(x, str)]
        try:
            _del_doc_ret = await delete_documents_by_title(docs_to_del)
            _atts = await delete_attachments_by_title(atts_to_del)
            _del_doc_ret = [x for x in _del_doc_ret if x.id is not None]
            _total = len(_del_doc_ret)
            show_msg(f"删除文档完成，共删除知识文档 {_total} 份，文档附件 {_atts} 份")
        except Exception as e:
            show_msg(f"删除文档失败: {e!r}", style="error", err=e)
            return
    else:
        show_msg("文集中没有指定删除文档或附件", style="warning")

    show_msg(f"文集 {corpus.as_posix()} 加载完成", style="success")
    return


@app.command("categories", epilog=HURAG_EPILOG)
@async_cmd
async def cate_list(
    path: str | None = typer.Option(
        None,
        "--path",
        "-p",
        help="指定要查看的类目路径，不提供则为所有第一级类目",
    ),
    include_docs: bool = typer.Option(
        False,
        "--include-docs",
        "-d",
        help="同时列出类目下的文档",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="同时列出所有下级类目",
    ),
):
    """列出后台知识库中的文档类目，可同时列出类目下的文档。"""

    from ..kbman import list_categories

    cata, docs = await list_categories(
        path = path or "",
        include_docs = include_docs,
        recursive = recursive,
    )

    if not cata:
        show_msg("未找到类目", style="warning")
        return

    for c in cata:
        show_msg(f"{c.path} ({c.id} / {c.external_id or '无外部ID'})", style="info")
        if not include_docs:
            continue
        c_d = docs.get(c.id)
        if not c_d:
            show_msg(f"  |-- <空类目>", style="warning")
            continue
        for d in c_d:
            show_msg(f"  |-- {d.title} ({d.id} / {d.external_id or '无外部ID'})")


@app.command("sync-categories", epilog=HURAG_EPILOG)
@async_cmd
async def sync_cate(
    file: str = typer.Argument(..., help="指定要同步的 CSV 数据文件")
):
    """从指定的 CSV 数据文件中同步类目和文档类目归属信息。"""
    import csv
    from pathlib import Path
    from ..kbman import sync_from_csv

    sync_file = Path(file).expanduser().resolve()

    if not sync_file.exists() or not sync_file.is_file():
        show_msg("未找到指定的数据文件", style="error")
        return

    if sync_file.suffix.lower() != ".csv":
        show_msg("数据文件必须为 CSV 格式", style="error")
        return

    with open(sync_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    results = await sync_from_csv(data)
    for result in results:
        show_msg(result[0], style=result[1])
