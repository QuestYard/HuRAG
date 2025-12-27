import typer

from typing import Literal

from . import (
    HURAG_EPILOG,
    show_msg,
    with_async_spinner,
    async_cmd,
)

app = typer.Typer(
    help = "QuestYard HuRAG CLI - KnowledgeBase Management Tools",
    add_completion = False,
    epilog = HURAG_EPILOG,
)

@app.command("init", epilog=HURAG_EPILOG)
def init():
    """
    初始化后台知识库，原有数据将被全部清除，请慎重操作。
    """
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

@app.command("info", epilog=HURAG_EPILOG)
@async_cmd
async def info():
    """
    查看后台知识库信息。
    """
    from ..knowledge_base import stat
    stat = await stat()

    from rich.table import Table
    from . import console
    table = Table(
        title="知识库统计信息",
        title_style="bold italic",
        box=None
    )
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
async def list(
    keyword: str | None = typer.Option(
        None,
        "--keyword",
        "-k",
        help="文档标题关键词, 支持模糊匹配",
    ),
    order: Literal["title", "date", "org"] = typer.Option(
        "title",
        "--order",
        "-o",
        help="排序字段: 标题, 生效日期, 发布机构",
    ),
):
    """
    列出后台知识库中的文档列表及文档相关信息。
    """
    from ..knowledge_base import list_documents
    docs = await list_documents(
        keyword=keyword,
        order=order,
    )
    from rich.table import Table
    from . import console
    doc_info = [
        (
            f"{doc[0]}（{doc[1]}）" if doc[1] else doc[0],  # title + sn
            doc[2].strftime("%Y-%m-%d"),    # valid_from
            doc[3].strftime("%Y-%m-%d") if doc[3] else "",  # valid_to
            doc[4].split("/")[-1].rstrip("*"),  # pub_org
            doc[4][0] == "/" and doc[4][-1] != "*",    # not propagate
            f"{doc[5]:,}",  # segments
            f"{doc[6]:,}",  # entities
        )
        for doc in docs
    ]
    table = Table(box=None)
    table.add_column(
        "序号", header_style="underline", width=6, justify="center")
    table.add_column(
        "文档标题", header_style="underline", width=100, no_wrap=True)
    table.add_column(
        "生效日期", header_style="underline", width=12, justify="center")
    table.add_column(
        "失效日期", header_style="underline", width=12, justify="center")
    table.add_column(
        "发布机构", header_style="underline", width=28, no_wrap=True)
    table.add_column(
        "仅本级", header_style="underline", width=8, justify="center")
    table.add_column(
        "段落数", header_style="underline", width=8, justify="right")
    table.add_column(
        "实体数", header_style="underline", width=8, justify="right")

    for ind, inf in enumerate(doc_info):
        table.add_row(
            f"{ind+1}",
            inf[0],
            inf[1],
            inf[2],
            inf[3],
            "是" if inf[4] else "否",
            inf[5],
            inf[6],
        )
    console.print(table)

@app.command("store", epilog=HURAG_EPILOG)
@async_cmd
async def store(
    path: str = typer.Argument(..., help="需要入库的文集所在目录")
):
    """
    以文集为单位，读取已经标注和分割完毕的文档进入知识库。

    注意：仅完成向量化入库，不提取知识图谱，图谱管理请使用 kgraph 命令。
    """
    from pathlib import Path
    corpus = Path(path).expanduser().resolve()
    if not corpus.is_dir():
        show_msg(f"指定的文集目录 {path} 不存在或不是一个目录", style="error")
        return

    show_msg(f"加载文集 {path} 中的文档...", style="info")
    from ..corpus import corpus_load
    try:
        docs = await corpus_load(corpus, exclude_kb_docs=True)
        show_msg(f"加载完成，共 {len(docs)} 份文档待入库", style="info")
    except Exception as e:
        show_msg(f"加载文集 {path} 失败: {e}", style="error", err=e)
        return

    show_msg(f"向量化待入库文档...", style="info")
    from ..llm.embedder import embed_documents
    
    with typer.progressbar(docs, label="向量化进度") as progress:
        for doc in progress:
            typer.echo(f"  正在向量化: {doc.title}")
            # 这里调用向量化函数
            async for embeddings in embed_documents(doc, batch_type=1):
                pass  # embeddings 已被处理
