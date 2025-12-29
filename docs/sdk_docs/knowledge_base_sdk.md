# 知识库 SDK 文档

本文档提供了 `src/hurag/knowledge_base.py` 中可用的知识库 SDK 方法的使用说明。

## 方法

### `stat`

获取关于知识库的统计信息，包括文档、段落、文本块、实体、关系和社区的数量。

**签名:**
```python
async def stat() -> tuple
```

**返回:**
- `tuple`: 包含计数和分类名称的元组列表。

### `list_documents`

列出知识库中的文档，支持可选的过滤和排序。

**签名:**
```python
async def list_documents(
    keyword: str | None = None,
    order: Literal["title", "date", "org"] = "title",
) -> tuple
```

**参数:**
- `keyword` (str | None): 用于按标题过滤文档的关键字。默认为 `None`。
- `order` (Literal["title", "date", "org"]): 排序顺序。选项包括 "title"（标题）、"date"（生效日期 valid_from）或 "org"（发布路径 pub_path）。默认为 "title"。

**返回:**
- `tuple`: 包含文档详情（标题、编号、生效日期、失效日期、发布路径、段落数、实体引用数）的元组列表。

### `indexing_documents`

将新文档索引到知识库中。这涉及将文档结构存储在关系数据库中，并将嵌入向量存储在向量数据库中。

**签名:**
```python
async def indexing_documents(
    docs: list[Document],
    embeddings: list[dict[Literal["dense_vecs", "sparse_vecs"], Any]],
) -> tuple[int, int, int]
```

**参数:**
- `docs` (list[Document]): 要索引的 `Document` 对象列表。
- `embeddings` (list[dict]): 包含每个文档嵌入向量的字典列表。每个字典应包含 "dense_vecs" 和 "sparse_vecs"。

**返回:**
- `tuple[int, int, int]`: 包含已索引文档、段落和文本块数量的元组。

此方法只负责将已有的完整数据存入数据库，调用之前必须先完成文档的加载和向量化。

- 调用 `hurag.corpus.corpus_load` 方法从一个已经完成标注和分割的文集中加载文档，*注意要使用 `exclude_kb_docs=True` 参数以避免重复加载已完成索引入库的文档。
- 调用 `hurag.llm.embed_documents` 方法获取文档的嵌入向量。
- 然后将加载的文档和对应的嵌入向量传递给 `indexing_documents` 方法进行索引入库。
