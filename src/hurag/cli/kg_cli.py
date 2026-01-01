import typer

from typing import Literal

from . import (
    HURAG_EPILOG,
    show_msg,
    with_async_spinner,
    async_cmd,
)

app = typer.Typer(
    help = "QuestYard HuRAG CLI - Knowledge Graph Management Tools",
    add_completion = False,
    epilog = HURAG_EPILOG,
)

@app.command("criteria", epilog=HURAG_EPILOG)
@async_cmd
async def criteria(
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
    table = Table(
            # title="实体别名-名称对映规则，采用别名的实体将被更名为正式名称：",
            # title_style="bold italic",
        box=None,
    )
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
        help="是否全部重建，默认 False 只对尚未生成图谱的文档进行构建。"
    ),
):
    """
    提取知识实体和实体间关系，构建知识图谱。
    """
    from pathlib import Path
    from ..constants import KGExtractionCriteria

    path = Path.cwd() if criteria_path is None else Path(criteria_path)
    if path.is_dir():
        path = path / "kgraph.toml"
    if not path.exists():
        criteria = KGExtractionCriteria()
        show_msg(
            f"警告：无规则文件 {path.as_posix()} ，构建的图谱可能包含部分无效实体。",
            style="warning",
        )
    else:
        criteria = KGExtractionCriteria.load_criteria(path)

    # TODO: build knowledge graph
    ...

