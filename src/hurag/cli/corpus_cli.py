import typer

from . import (
    HURAG_EPILOG,
    show_msg,
    with_spinner,
)

app = typer.Typer(
    help="QuestYard HuRAG CLI - Corpus & Document Tools",
    add_completion=False,
    epilog=HURAG_EPILOG,
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
    ),
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
        from ..kbman import doc_convert

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
def markup(path: str = typer.Argument(..., help="需要标注的文集所在目录")):
    """
    在指定的目录下检查知识文档原文件，收集文档元数据并创建文集标注。

    文集标注文件名称为 corpus.json ，如果标注文件已存在，则会被覆盖。
    可以使用 meta.json 文件提供元数据信息，v0.3.2 之前版本的标注文件可以直接更名为
    meta.json，其中的文档元数据信息会被自动继承并写入标注文件中。

    自动预标注生成的元数据并不保证完整和准确，完成预标注后应当手动修正。
    如有修改或删除库内已有文档的，手动添加 "update" 和 "delete" 信息。

    标注文件内容完整无误，且已经完成文集中的 `.regu`, `.text`, `.markdown` 文件分割后，
    即可使用 hurag load 命令把文集加载入知识库。
    """

    @with_spinner(text="预标注进行中...", style="info")
    def _markup():
        from ..kbman import corpus_markup

        try:
            markups = corpus_markup(path)
            return {
                "msg": f"文集 {path} 预标注完成，共 {len(markups['insert'])} 份文档",
                "style": "success" if markups["insert"] else "warning",
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
def split(path: str = typer.Argument(..., help="需要分割文档的文集所在目录")):
    """
    根据文集标注文件，查找并分割文集中的 `.regu`, `.text`, `.markdown` 文件。

    `.regu` 文件会以条文和附件为单位进行拆分，每段一条条文或一个附件，
    段内按照长度进一步拆分为 size = 500, overlap = 0 的小块。

    `.text` 文件会被递归拆分为 size = 500, overlap = 100 的小块。

    `.markdown` 文件会先按五级标题拆分为若干段落，然后将每个段落拆分为
    size = 500, overlap = 0 的小块。

    文档的拆分结果会被写入一个与源文件同名、后缀为 '.idx' 的文本文件中。
    例如源文件 'example.txt' 的拆分结果会被写入 'example.idx' 文件中。
    """

    @with_spinner(text="文档分割进行中...", style="info")
    def _split():
        from ..kbman import corpus_split

        try:
            splitted = corpus_split(path)
            return {
                "msg": (f"文集 {path} 文档分割完成，共分割文档 {len(splitted)} 份，"),
                "style": "info",
                "err": None,
            }
        except Exception as e:
            return {
                "msg": f"文集 {path} 分割文档失败：{e}",
                "style": "error",
                "err": e,
            }

    result = _split()
    show_msg(**result)
