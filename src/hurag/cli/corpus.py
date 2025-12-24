import asyncio
import typer

from typing import Literal

from . import (
    HURAG_EPILOG,
    show_msg,
    with_spinner,
    with_async_spinner,
)
from .. import logger

app = typer.Typer(
    help = "QuestYard HuRAG CLI - Corpus & Document Tools",
    add_completion = False,
    epilog = HURAG_EPILOG,
)

@app.command("convert", epilog=HURAG_EPILOG)
def convert(
    src_file: str = typer.Argument(..., help="需要转换的源文件名"),
    output_file: str | None = typer.Option(
        None,
        "--output-file",
        "-o",
        help="输出文件名，默认使用源文件名。",
    ),
    encoding_only: bool = typer.Option(
        False,
        "--encoding-only",
        "-e",
        help=(
            "仅转换文字编码，将 TXT, CSV, HTML, XML, JSON, MD 等文本型文件"
            "转为 UTF-8 编码，而非转换为 Markdown 文件。"
        ),
    )
):
    """
    提取 PDF, Word, Excel, Powerpoint, CSV, HTML, JSON, XML 文件的内容，保存为
    Markdown 文件，或将 Windows 环境下生成的文本型文件的文字编码转为 UTF-8。

    默认情况下，使用微软开源工具 markitdown 从 PDF, Word, Excel, Powerpoint,
    CSV, HTML, JSON, XML 文件中提取内容，转为 Markdown 格式文件。

    使用 --encode-only (-e) 选项则为编码转换模式，将不会处理 PDF, Word
    等二进制文件，仅对 TXT, CSV, HTML, JSON, XML, MD
    等文本型文件进行文字编码转换，由 Windows 的 GBK 编码转为 UTF-8
    编码，源格式保存，不会转为 Markdown。
    """
    @with_spinner(text="文件转换中...", style="info")
    def _convert():
        from ..documents import doc_convert
        try:
            tgt = doc_convert(src_file, output_file, encoding_only)
            return {
                "msg": f"文件转换成功，结果另存为：{tgt}",
                "style": "success",
                "err": None,
            }
        except Exception as e:
            return {
                "msg": f"文件转换失败: {e}",
                "style": "error",
                "err": e,
            }

    result = _convert()
    show_msg(**result)

@app.command("markup", epilog=HURAG_EPILOG)
def markup(
    path: str = typer.Argument(..., help="需要标注的文集所在目录")
):
    """
    在指定的目录下检查 TXT, CSV, Markdown 文件，收集文档元数据并创建文集标注。
    
    文集标注文件名称为 corpus.json ，如果标注文件已存在，则会被覆盖。HuRAG-pre
    使用的文档元数据信息会被自动继承并写入标注文件中。

    自动预标注仅生成部分元数据字段，且并不保证完全准确，完成后应当手动修正。
    标注文件内容完全准确后即可进行文档内容分割（corpus split）。
    """
    @with_spinner(text=f"预标注进行中...", style="info")
    def _markup():
        from ..documents import corpus_markup
        try:
            markups = corpus_markup(path)
            return {
                "msg": f"文集 {path} 预标注完成，共标注 {len(markups)} 份文档",
                "style": "success" if markups else "warning",
                "err": None,
            }
        except Exception as e:
            return {
                "msg": f"文集 {path} 预标注失败：{e}",
                "style": "error",
                "err": e,
            }

    result = _markup()
    show_msg(**result)

@app.command("split", epilog=HURAG_EPILOG)
def split(
    path: str = typer.Argument(..., help="需要分割文档的文集所在目录")
):
    """
    根据文集标注文件，查找并分割文集中 'text' 或 'regu' 布局的文档。

    'text' 布局的 TXT 文件会被递归拆分为 size = 500, overlap = 100 的小块。

    'text' 布局的 Markdown 文件会先按标题拆分为若干段落，然后将每个段落拆分为
    size = 500, overlap = 0 的小块。

    'regu' 布局的文件会以条文和附件为单位进行拆分，每段一条条文或一个附件，
    段内按照长度进一步拆分为 size = 500, overlap = 0 的小块。

    其他布局包括 'manual', 'v1_doc' 和 8 种 CSV 表格布局不会进行分割。

    文档的拆分结果会被写入一个与源文件同名、后缀为 '.idx' 的文本文件中。
    例如源文件 'example.txt' 的拆分结果会被写入 'example.idx' 文件中。
    """
    @with_async_spinner(text=f"文档分割进行中...", style="info")
    async def _split():
        from ..documents import corpus_split
        try:
            stat = await corpus_split(path)
            return {
                "msg": (
                    f"文集 {path} 文档分割完成，共分割 {stat[0]} 份，"
                    f"跳过 {stat[1]} 份，失败 {stat[2]} 份。"
                ),
                "style": "info",
                "err": None,
            }
        except Exception as e:
            return {
                "msg": f"文集 {path} 预标注失败：{e}",
                "style": "error",
                "err": e,
            }

    result = asyncio.run(_split())
    show_msg(**result)

