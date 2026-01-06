# 文集管理 SDK 文档

本文档提供了 `hurag.corpus` 模块中可用的文集管理 SDK 方法的使用说明。这些方法主要用于文档格式转换、元数据标记、文档切分和加载。

## 数据类

HuRAG SDK 使用 `Document`, `Segment`, `Chunk` 三个数据类来表示文档对象及其结构。类定义在 `hurag.schemas.document` 模块中。

### `Chunk`

表示文档中的最小文本块。

- `id` (str): 唯一标识符。
- `seg_id` (str): 所属段落的 ID。
- `text` (str): 文本内容。
- `seq_no` (int): 在段落中的序号。

### `Segment`

表示文档中的一个段落，包含一个或多个 `Chunk`。

- `id` (str): 唯一标识符。
- `doc_id` (str): 所属文档的 ID。
- `seq_no` (int): 在文档中的序号。
- `chunks` (list[Chunk]): 包含的 `Chunk` 对象列表。
- `text` (property): 返回段落包含的所有 Chunk 的拼接文本。

### `Document`

表示一个完整的文档，包含元数据和内容段落。

- `id` (str): 唯一标识符。
- `title` (str): 文档标题。
- `sn` (str): 文档编号。
- `date` (datetime): 文档日期。
- `segments` (list[Segment]): 包含的 `Segment` 对象列表。
- `fulltext` (property): 返回文档包含的所有 Segment 的拼接文本。

**主要方法:**

- `read(path: Path, markup: dict) -> Self`: 从指定路径和标记信息读取文档内容及元数据。
- `from_db(ids: list[str] | None, titles: list[str] | None) -> list[Self]`: （类方法）根据 ID 或标题从数据库加载文档列表。

## 方法

### `doc_convert`

将文档转换为 UTF-8 编码的文本或 Markdown 格式。

**签名:**

```python
def doc_convert(src_file: str, tgt_file: str | None, enc: bool) -> str
```

**参数:**

- `src_file` (str): 源文件路径。
- `tgt_file` (str | None): 目标文件路径。如果为 `None`，将根据源文件名创建默认目标文件。
- `enc` (bool): 如果为 `True`，将 GBK 编码的文本转换为 UTF-8。如果为 `False`，将源文件转换为 Markdown。

**返回:**

- `str`: 转换后的目标文件路径。

**示例:**

```python
from hurag.corpus import doc_convert

# 将 GBK 编码的文本文件转换为 UTF-8
utf8_file = doc_convert("data/raw_doc.txt", None, enc=True)

# 将 Word 文档转换为 Markdown
md_file = doc_convert("data/report.docx", "data/report.md", enc=False)
```

### `corpus_markup`

为指定文件夹中的文档生成 `corpus.json` 标记文件。该方法会扫描文件夹中的 `.txt`, `.csv`, `.md` 文件，提取元数据，并生成包含所有文档信息的 JSON 文件。

**签名:**

```python
def corpus_markup(path: str) -> list[dict]
```

**参数:**

- `path` (str): 包含文档的文件夹路径。

**返回:**

- `list[dict]`: 文档标记条目列表。

**示例:**

```python
from hurag.corpus import corpus_markup

# 为 'data/corpus' 目录下的文档生成标记文件
markups = corpus_markup("data/corpus")
print(f"Generated markups for {len(markups)} documents.")
```

### `corpus_split`

对文集中的文档进行切分。支持 'text' (普通文本/Markdown) 和 'regu' (法规) 布局的文档。

**签名:**

```python
async def corpus_split(path: str) -> tuple
```

**参数:**

- `path` (str): 包含 `corpus.json` 和文档的文件夹路径。

**返回:**

- `tuple`: 包含 (成功数, 跳过数, 失败数) 的元组。

**示例:**

```python
import asyncio
from hurag.corpus import corpus_split

async def main():
    # 切分 'data/corpus' 目录下的文档
    success, skipped, failed = await corpus_split("data/corpus")
    print(f"Split results: Success={success}, Skipped={skipped}, Failed={failed}")

asyncio.run(main())
```

### `corpus_load`

将指定文件夹中的文档加载为 `Document` 对象列表。

**签名:**

```python
async def corpus_load(
    path: Path,
    exclude_kb_docs: bool = False,
) -> list[Document]
```

**参数:**

- `path` (Path): 包含 `corpus.json` 和文档的文件夹路径。
- `exclude_kb_docs` (bool): 是否排除知识库中已存在的文档。默认为 `False`。

**返回:**

- `list[Document]`: 加载的 `Document` 对象列表。

**示例:**

```python
import asyncio
from pathlib import Path
from hurag.corpus import corpus_load

async def main():
    corpus_path = Path("data/corpus")
    # 加载文档，排除已入库的文档
    documents = await corpus_load(corpus_path, exclude_kb_docs=True)
    for doc in documents:
        print(f"Loaded document: {doc.title}")

asyncio.run(main())
```
