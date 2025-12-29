# HuRAG SDK Documentation

HuRAG 提供了 Python SDK，方便开发者在自己的应用中集成 HuRAG 的 RAG 检索和 LLM 调用能力。通过 HuRAG SDK，可以快速构建面向法律法规解释的智能问答系统、文档检索系统等应用。

HuRAG SDK 包括多个模块，涵盖了知识库管理、文档管理、用户管理、RAG 检索和 LLM 调用等功能。开发者可以根据自己的需求，灵活调用 SDK 提供的接口，实现各种应用场景。

## 通用工具

HuRAG SDK 提供了一些常用的工具函数、工具类和单例模式的工具变量，方便开发者进行日志管理、配置管理等操作。

### 系统配置

HuRAG SDK 使用 `hurag.yaml` 配置文件进行配置管理，开发者可以通过 `hurag` 模块中的单例全局变量 `conf` 获取全部配置项。

`conf` 是一个嵌套的 `namespace` 对象，成员和结构与 `hurag.yaml` 配置文件中的内容一一对应。例如，可以通过 `conf.milvus.uri` 获取 Milvus 的连接 URI。

```python
from hurag import conf
# 获取 Milvus 连接 URI
milvus_uri = conf.milvus.uri
# 获取 MariaDB 数据库名称
mariadb_database = conf.mariadb.database
```

### 日志

HuRAG SDK 在 `hurag` 模块中提供单例全局变量 `logger` 实现日志记录功能，开发者可以直接使用 `logger` 进行日志记录。

配置项 `log.log_in_file` 控制是否将日志写入文件，如写入文件，系统加载时将在当前工作目录下创建名为 `hurag.log` 的日志文件。

HuRAG 的命令行工具也使用 `logger` 进行日志记录，但在命令行工具中会将默认的 `StreamHandler` 替换为 `RichHandler`，以提供更丰富的终端输出效果。

```python
from hurag import logger
# 记录信息级别日志
logger.info("This is an info message.")
# 记录错误级别日志
logger.error("This is an error message.")
```

默认日志级别：

- FileHandler: DEBUG
- StreamHandler: WARNING
- RichHandler (CLI): INFO

`hurag.change_console_log_handler` 函数可以动态更改控制台日志处理器，把默认的控制台日志交给一个其他管理器，例如 `RichHandler`。

`hurag.reset_console_log_handler` 函数可以将控制台日志处理器重置为默认的 `StreamHandler`。

## 数据存储服务

HuRAG 使用 Milvus 作为向量数据存储，使用 MariaDB/MySQL 作为关系型数据存储，并通过二者自行构建了一套图数据存储，实现简洁高效的知识图谱能力。HuRAG SDK 提供了对这些数据存储服务的封装，方便开发者进行数据存储和管理操作。

数据存储服务集中在 `hurag.dss` 模块下，包含以下子模块：
- `hurag.dss.vss`: 向量数据存储服务，封装了对 Milvus 的操作。
- `hurag.dss.rss`: 关系型数据存储服务，封装了对 MariaDB/MySQL 的操作。
- `hurag.dss.gss`: 图数据存储服务，基于 Milvus 和 MariaDB/MySQL 实现。

数据存储服务 SDK 的使用说明和 HuRAG 数据结构请参考 [HuRAG 数据存储服务 SDK 文档](sdk_docs/data_storage_sdk.md)。

## LLM 调用

HuRAG SDK 提供了对大语言模型（LLM）和 QuestYard/embedding-service 提供的 Embedding/Reranker 微服务的调用封装，方便开发者在应用中集成 LLM 能力。

### with_es_client 装饰器

HuRAG SDK 在 `hurag.llm` 模块中提供了装饰器 `with_es_client`，封装了对 QuestYard Embedding Service 的调用，提供了获取文本嵌入向量和重排序文本块的功能。

使用 `with_es_client` 装饰器可以简化对 Embedding Service 的调用过程，自动处理请求和响应。

```python
from hurag.llm import with_es_client
@with_es_client
async def get_text_embedding(es_client, text: str) -> list[float]:
    embedding = await es_client.embed(text)
    return embedding
```

### 具体 embedding 方法

HuRAG SDK 在 `hurag.llm` 模块中提供了多个具体的 Embedding 方法，封装了对 QuestYard Embedding Service 的调用，方便开发者获取文本的嵌入向量。

- `embed_query`: 获取一个或多个查询字符串的嵌入向量。
- `embed_documents`: 获取一组文档 (Document 对象列表) 的嵌入向量。
- `embed_keywords`: 获取用户查询关键词的嵌入向量。

**函数签名**

```python
@with_es_client
async def embed_query(
    query: str | list[str],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> tuple[dict[str, Any], EmbeddingPayloadMeta]:

@with_es_client
async def embed_documents(
    docs: Document | list[Document],
    *,
    batch_type: int = 1,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> AsyncGenerator[tuple[dict[str, Any], EmbeddingPayloadMeta], None, None]:

@with_es_client
async def embed_keywords(
    keywords: dict[Literal["low_level_keywords", "high_level_keywords"], list[str]],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> tuple[dict[str, Any], EmbeddingPayloadMeta]:
```

**参数说明**
`return_sparse` 控制是否返回稀疏向量，默认为 `True`。

`embed_documents` 方法支持批量处理文档，通过 `batch_type` 参数控制批量方式：
- `batch_type = 0`: 部分批次，所有文本块一次性处理。
- `batch_type = 1`: 按文档分批处理，每次处理一个文档中的所有文本块。
- `batch_type > 1`: 按文本块分批处理，每次处理 `batch_type` 个文本块。

`esclient` 参数由装饰器自动传入，开发者无需手动提供。

### OpenAI LLM 调用

TODO： Add more details about OpenAI LLM usage.

## 文集管理

Corpus Management (文集管理) 是 HuRAG SDK 的核心功能模块，提供了以文集 (Corpus) 为组织单元的文档标注、分割、加载等功能。文集管理模块封装在 `hurag.corpus` 模块中，方便开发者进行文集相关的操作。

SDK 详情请参考: [文集管理 SDK 文档](sdk_docs/corpus_management_sdk.md)

## 知识库管理

Knowledge Base Management (知识库管理) 是 HuRAG SDK 的核心功能模块，提供了对知识库的创建、更新、查询和删除等操作。知识库管理模块封装在 `hurag.knowledge_base` 模块中，方便开发者进行知识库相关的操作。

SDK 详情请参考: [知识库管理 SDK 文档](sdk_docs/knowledge_base_sdk.md)
