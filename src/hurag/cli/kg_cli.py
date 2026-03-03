import typer

from . import (
    HURAG_EPILOG,
    show_msg,
    async_cmd,
)

app = typer.Typer(
    help="QuestYard HuRAG CLI - Knowledge Graph Management Tools",
    add_completion=False,
    epilog=HURAG_EPILOG,
)


@app.command("criteria", epilog=HURAG_EPILOG)
def criteria(
    criteria_path: str | None = typer.Option(
        None,
        "--criteria-path",
        "-p",
        help="规则文件所在目录或文件路径，默认目录为当前目录，默认文件名 kgraph.toml",
    ),
):
    """
    列出当前配置文件中的知识图谱提取规则，包括实体名称阻止模式和实体名称-别名对应表。
    """
    from pathlib import Path

    path = Path.cwd() if criteria_path is None else Path(criteria_path)
    if path.is_dir():
        path = path / "kgraph.toml"
    if not path.exists():
        show_msg(f"找不到规则文件 {path.as_posix()}")
        return

    from ..constants import KGExtractionCriteria

    criteria = KGExtractionCriteria.load_criteria(path)

    from . import print_regex_literal
    from rich.table import Table
    from . import console

    show_msg(f"规则文件：{path.as_posix()}", style="info")
    console.print()
    show_msg("实体名称阻止规则，名称匹配以下规则的实体将被忽略：", style="info")
    console.print()
    for blocked_entity in criteria.blocked_entities:
        print_regex_literal(blocked_entity)
    console.print()

    show_msg("实体别名-名称对映规则，别名实体将被更名为正式名称：", style="info")
    console.print()
    table = Table(box=None)
    table.add_column(
        "别名",
        width=40,
        justify="left",
        style="bold cyan",
        header_style="bold underline",
    )
    table.add_column(
        "正式名称",
        width=60,
        justify="left",
        style="bold green",
        header_style="bold underline",
    )
    for alias, name in criteria.entity_aliases.items():
        table.add_row(alias, name)
    console.print(table)


@app.command("build", epilog=HURAG_EPILOG)
@async_cmd
async def build(
    criteria_path: str | None = typer.Option(
        None,
        "--criteria-path",
        "-p",
        help="指定规则文件或规则文件所在目录，默认当前目录下 kgraph.toml",
    ),
    force_rebuild: bool = typer.Option(
        False,
        "--force-rebuild",
        "-f",
        help=(
            "是否全部重建，默认 False 只对尚未生成图谱的文档进行构建。"
            "重建将清除所有已经构建的知识图谱!"
        ),
    ),
):
    """提取知识实体和实体间关系，构建知识图谱。"""
    from pathlib import Path
    from . import console
    from ..constants import KGExtractionCriteria

    path = Path.cwd() if criteria_path is None else Path(criteria_path)
    if path.is_dir():
        path = path / "kgraph.toml"
    criteria = KGExtractionCriteria.load_criteria(path)
    if not criteria.entity_aliases or not criteria.blocked_entities:
        show_msg("规则文件无效，构建的图谱可能存在无效实体。", style="warning")

    # build knowledge graph
    # 1.1 clean existed graph if force_rebuild = True
    # 1.2 show documents list and choose documents, elsewise
    if force_rebuild:
        from ..dss import clear_graph

        await clear_graph()

    from ..kbman import list_documents

    docs = await list_documents()
    doc_info = [
        (f"{doc[0]}（{doc[1]}）" if doc[1] else doc[0], doc[7])
        for doc in docs
        if doc[6] == 0 and not doc[0].startswith("*")
    ]  # doc_info := [(fullname, id), ...]
    from rich.table import Table

    table = Table(title="尚未构建知识图谱文档清单", title_style="bold italic", box=None)
    table.add_column("序号", header_style="underline", width=6, justify="right")
    table.add_column("文档", header_style="underline", width=100, no_wrap=True)
    for ind, inf in enumerate(doc_info):
        table.add_row(f"{ind + 1}", inf[0])
    console.print(table)
    choices = console.input(
        "请选择要构建图谱的文档序号，多个文档用英文逗号分隔，"
        "连续多个文档用 n-m 表示，例如 1,3,7-12，不输入表示全选："
    ).strip()
    from ..utilities import str2int

    if choices:
        choices = choices.split(",")
        indice = []
        for choice in choices:
            try:
                indice.extend(str2int(choice))
            except ValueError:
                pass
        indice = set(ind - 1 for ind in indice if 1 <= ind <= len(doc_info))
        doc_info = [d for i, d in enumerate(doc_info) if i in indice]

    if not doc_info:
        console.print("无选中的文档，本次构建结束。")
        return

    console.print(f"1. 为下列 {len(doc_info)} 篇文档构建知识图谱：")
    for d in doc_info:
        console.print(d[0])
    # 2. extract from LLM
    from ..schemas import Graph
    from ..knowledge_graph import extract_kg_elements, normalize_kg_elements

    console.print("2. 提取实体与实体间关系")
    resp = await extract_kg_elements([d[1] for d in doc_info])
    # 3. Graph.from_responses
    console.print()
    console.print("3. 去重并生成图谱")
    g = Graph.from_responses(resp, alias=criteria.entity_aliases)
    # 4. Graph.resolve
    console.print("4. 实体关系解析归并")
    _ = await g.resolve(blacklist=criteria.blocked_entities)
    # 5. normalization
    console.print("5. 实体关系描述规范化")
    _ = await normalize_kg_elements(g)
    console.print()
    show_msg(
        f"已经提取形成以上文档的知识图元素，包含 {len(g.nodes)} 个知识实体、"
        f"{(len(g.edges))} 对实体关系",
        style="info",
    )
    # 6. embedding
    console.print("6. 实体关系向量化")
    from ..llm.embedder import embed_kg_elements
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeRemainingColumn,
        MofNCompleteColumn,
    )

    total_elements = len(g.nodes) + len(g.edges)
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(elapsed_when_finished=True),
            MofNCompleteColumn(),
        ) as progress:
            task = progress.add_task("图谱元素向量化", total=total_elements)
            embeddings = []
            async for vecs, _ in embed_kg_elements(g):
                embeddings.append(vecs)
                progress.update(task, advance=vecs["dense_vecs"].shape[0])
    except Exception as e:
        show_msg(f"图谱向量化失败: {e}", style="error", err=e)
        show_msg("知识图谱构建未完成", style="error")
        return
    # 7. saving to database
    console.print("7. 保存知识图谱")
    from ..dss import gss

    try:
        await gss.upsert_graph(g, embeddings, [d[1] for d in doc_info])
        show_msg("知识图谱构建全部完成", style="success")
    except Exception as e:
        show_msg(f"保存知识图谱失败: {e}", style="error", err=e)
        show_msg("知识图谱构建未完成，建议下次使用 -f 参数重建", style="error")


@app.command("create-communities", epilog=HURAG_EPILOG)
@async_cmd
async def create_communities(
    resolution: float = typer.Option(
        0.5,
        "--resolution-gamma",
        "-r",
        help="Leiden算法聚类参数，数值越大聚类越细，建议介于0.5至1.0之间。",
    ),
    min_size: int = typer.Option(
        10,
        "--min-size",
        "-m",
        help="社区中实体数量下限，少于此限的分区不视为有效社区。",
    ),
):
    """根据已有的知识图谱，采用 Leiden 算法构建知识社区。"""
    from . import console
    from ..knowledge_graph import community_leiden, summarize_communities
    from ..llm import embed_community_summaries
    from ..dss import gss

    try:
        console.print("1. 聚类生成社区")
        g, p, n = await community_leiden(resolution=resolution)
        console.print("2. 生成社区摘要")
        summarise = await summarize_communities(g, p, n, min_size=min_size)
        console.print()
        console.print("3. 社区向量化")
        emb = await embed_community_summaries(summarise)
        console.print("4. 保存知识社区")
        c, e = await gss.save_communities(g, p, emb)
        show_msg(
            f"知识社区构建完毕，共生成有效社区 {c} 个，覆盖知识实体 {e} 个。",
            style="success",
        )
    except Exception as e:
        show_msg(f"构建知识社区失败: {e}", style="error")


@app.command("communities", epilog=HURAG_EPILOG)
@async_cmd
async def communities():
    """列出当前所有知识社区。"""
    from . import console
    from rich.table import Table
    from ..dss import rss

    rows = await rss.query(
        """
        SELECT c.id , c.summary, COUNT(ce.entity_id) AS cnt
        FROM communities c
        JOIN community_entity ce ON c.id = ce.community_id
        GROUP BY c.id
        ORDER BY cnt DESC
        """
    )
    table = Table(box=None)
    table.add_column(
        "社区ID",
        width=8,
        justify="center",
        header_style="bold underline",
    )
    table.add_column(
        "社区摘要",
        width=160,
        justify="left",
        header_style="bold underline",
    )
    table.add_column(
        "实体数",
        width=10,
        justify="right",
        header_style="bold underline",
    )
    for cid, csum, ecnt in rows:
        table.add_row(f"{cid}", csum, f"{ecnt}")
    console.print(table)
