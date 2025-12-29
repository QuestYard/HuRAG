# 文集管理 SDK 文档

本文档提供了 `hurag.corpus` 模块中可用的文集管理 SDK 方法的使用说明。这些方法主要用于文档格式转换、元数据标记、文档切分和加载。

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
