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

### Embedding Service 调用

HuRAG 使用 QuestYard Embedding Service 作为文本嵌入向量和重排序文本块的服务，HuRAG SDK 在 `hurag.llm` 模块中封装了对 Embedding Service 的调用，提供了简化的接口，方便开发者获取文本的嵌入向量和进行文本块重排序。

#### with_es_client 装饰器

HuRAG SDK 在 `hurag.llm` 模块中提供了装饰器 `with_es_client`，封装了对 QuestYard Embedding Service 的调用，提供了获取文本嵌入向量和重排序文本块的功能。

使用 `with_es_client` 装饰器可以简化对 Embedding Service 的调用过程，自动处理请求和响应。

```python
from hurag.llm import with_es_client
@with_es_client
async def get_text_embedding(es_client, text: str) -> list[float]:
    embedding = await es_client.embed(text)
    return embedding
```

#### 具体 embedding 方法

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

@with_es_client
async def embed_kg_elements(
    g: Graph,
    *,
    return_sparse: bool = True,
    batch_size: int=1024,
    esclient: AsyncEmbeddingClient | None = None,
) -> AsyncGenerator[tuple[dict[str, Any], EmbeddingPayloadMeta], None, None]:

@with_es_client
async def embed_community_summaries(
    summaries: dict[int, list[str]],
    *,
    return_sparse: bool = True,
    esclient: AsyncEmbeddingClient | None = None,
) -> list[dict[str, Any]]:
```

**参数说明**
`return_sparse` 控制是否返回稀疏向量，默认为 `True`。

`embed_documents` 方法支持批量处理文档，通过 `batch_type` 参数控制批量方式：
- `batch_type = 0`: 部分批次，所有文本块一次性处理。
- `batch_type = 1`: 按文档分批处理，每次处理一个文档中的所有文本块。
- `batch_type > 1`: 按文本块分批处理，每次处理 `batch_type` 个文本块。

`esclient` 参数由装饰器自动传入，开发者无需手动提供。

### OpenAI LLM 调用

HuRAG 采用 OpenAI SDK 作为大语言模型（LLM）的调用接口，所有支持 OpenAI 接口的模型均可调用。HuRAG SDK 在 `hurag.llm` 模块中封装了对 OpenAI SDK 的调用，提供了简化的接口，方便开发者在应用中集成 LLM 能力。

关于 LLM 的配置，请参考: [配置文件说明](../README.md#generate-configuration-file)

#### 基础调用

`hurag.llm.openai_client` 模块提供了 `chat` 函数，用于调用 LLM 模型。该函数支持非流式和流式两种调用方式。

**函数签名**

```python
async def chat(
    model: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    stream: bool = False,
    client: AsyncOpenAI | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.0,
    timeout: float = 60.0,
    max_retries: int = 3,
) -> ChatCompletion | AsyncStream:
```

**参数说明**

- `model`: 模型名称。
- `prompt`: 用户输入的提示词。
- `system_prompt`: 可选的系统提示词。
- `history_messages`: 可选的历史对话记录，格式为 `[{"role": "user", "content": "..."}, ...]`。
- `stream`: 是否开启流式输出，默认为 `False`。
- `client`: 可选的 `AsyncOpenAI` 客户端实例。如果未提供，则需提供 `base_url` 和 `api_key`。
- `base_url`: OpenAI API 的基础 URL。
- `api_key`: OpenAI API 的密钥。
- `temperature`: 采样温度，默认为 0.0。
- `timeout`: 请求超时时间（秒），默认为 60.0。
- `max_retries`: 最大重试次数，默认为 3。

注意，`client`、`base_url` 和 `api_key` 三者中必须提供 `client`，或者同时提供 `base_url` 和 `api_key`。如果提供了 `client`，则忽略 `base_url` 和 `api_key`。

*提供 `client` 参数时，函数退出不会关闭客户端连接，客户端的生命周期由调用方管理。提供 `base_url` 和 `api_key` 参数时，函数内部会自动创建和关闭客户端实例。*

#### 结果提取

`hurag.llm.llm_common_tools` 模块提供了两个工具函数，用于从 LLM 返回的结果中提取内容：

- `extract_response(response: ChatCompletion, content_only: bool = True) -> str | dict[str, str]`: 用于提取非流式调用的结果。
- `extract_chunk(chunk: ChatCompletionChunk, previous_content: str | None = None) -> str`: 用于提取流式调用的结果块。

#### 使用示例

**非流式调用示例**

```python
import asyncio
from hurag.llm.openai_client import chat
from hurag.llm.llm_common_tools import extract_response

async def main():
    # 假设已有 base_url 和 api_key
    response = await chat(
        model="gpt-3.5-turbo",
        prompt="你好，请介绍一下你自己。",
        base_url="https://api.openai.com/v1",
        api_key="your-api-key"
    )
    content = extract_response(response)
    print(content)

if __name__ == "__main__":
    asyncio.run(main())
```

**流式调用示例**

```python
import asyncio
from hurag.llm.openai_client import chat
from hurag.llm.llm_common_tools import extract_chunk

async def main():
    stream = await chat(
        model="gpt-3.5-turbo",
        prompt="讲一个关于AI的故事。",
        stream=True,
        base_url="https://api.openai.com/v1",
        api_key="your-api-key"
    )
    
    print("Response:")
    async for chunk in stream:
        # extract_chunk 返回当前 chunk 的内容增量
        delta = extract_chunk(chunk)
        print(delta, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
```

#### 客户端装饰器

`hurag.llm.openai_client` 模块还提供了 `with_oa_client` 装饰器，用于自动创建和管理 `AsyncOpenAI` 客户端实例，并将其注入到被装饰的异步函数中。这在需要频繁创建客户端或希望简化客户端生命周期管理的场景下非常有用。

**函数签名**

```python
def with_oa_client(
    func: Callable | None = None,
    *,
    base_url: str,
    api_key: str,
    timeout: float = 60.0,
    max_retries: int = 3,
    client_name: str = "oaclient"
) -> Callable[..., Any]:
```

**参数说明**

- `base_url`: OpenAI API 的基础 URL。
- `api_key`: OpenAI API 的密钥。
- `timeout`: 请求超时时间（秒），默认为 60.0。
- `max_retries`: 最大重试次数，默认为 3。
- `client_name`: 注入到被装饰函数中的参数名称，默认为 `"oaclient"`。

**使用示例**

```python
import asyncio
from hurag.llm.openai_client import with_oa_client, chat
from hurag.llm.llm_common_tools import extract_response
from openai import AsyncOpenAI

# 使用装饰器自动注入 client
# 注意：被装饰的函数需要接收 client_name 指定的参数
@with_oa_client(
    base_url="https://api.openai.com/v1", 
    api_key="your-api-key", 
    client_name="client" # 将客户端注入到名为 'client' 的参数中
)
async def custom_chat_task(prompt: str, client: AsyncOpenAI):
    # 直接使用注入的 client 调用 chat 函数
    response = await chat(
        model="gpt-3.5-turbo",
        prompt=prompt,
        client=client 
    )
    return extract_response(response)

async def main():
    result = await custom_chat_task("简单介绍一下 Python 装饰器")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 文集管理

Corpus Management (文集管理) 是 HuRAG SDK 的核心功能模块，提供了以文集 (Corpus) 为组织单元的文档标注、分割、加载等功能。文集管理模块封装在 `hurag.corpus` 模块中，方便开发者进行文集相关的操作。

SDK 详情请参考: [文集管理 SDK 文档](sdk_docs/corpus_management_sdk.md)

## 知识库管理

Knowledge Base Management (知识库管理) 是 HuRAG SDK 的核心功能模块，提供了对知识库的创建、更新、查询和删除等操作。知识库管理模块封装在 `hurag.knowledge_base` 模块中，方便开发者进行知识库相关的操作。

SDK 详情请参考: [知识库管理 SDK 文档](sdk_docs/knowledge_base_sdk.md)

## 知识图谱管理

Knowledge Graph Management (知识图谱管理) 是 HuRAG SDK 的核心功能模块，提供了对知识图谱的创建、更新、查询和删除等操作。知识图谱管理模块封装在 `hurag.knowledge_graph` 模块中，方便开发者进行知识图谱相关的操作。

HuRAG 知识图谱管理模块支持从文本中抽取实体和关系，构建知识图谱，聚类生成知识社区，并提供了知识图谱的存储和检索功能。

### 图谱提取规则

HuRAG 支持通过配置文件 `kgraph.toml` 自定义知识图谱的提取规则，以提高图谱质量。规则由 `hurag.constants.KGExtractionCriteria` 类定义和加载。

主要包含以下三类规则：

1.  **blocked_entities (屏蔽实体)**: 定义一组正则表达式列表。在实体抽取过程中，匹配这些正则表达式的实体将被过滤掉，不会进入知识图谱。这通常用于屏蔽无意义的通用词汇（如“本文”、“相关部门”等）或特定格式的噪声数据。
2.  **blocked_segments (屏蔽片段)**: 定义一组字符串列表。包含这些字符串的文本片段（Segment）将不会参与知识图谱的构建。这常用于屏蔽法律法规中的“附则”等包含大量元数据但对知识关联贡献较小的部分。
3.  **entity_aliases (实体别名)**: 定义一个键值对映射（字典）。用于将实体的不同称呼（别名、简称）统一映射到标准名称。例如，将“招投标法”映射为“中华人民共和国招标投标法”。这有助于消除歧义，合并相同实体。

默认情况下，系统会在当前工作目录下查找 `kgraph.toml` 文件加载这些规则。

SDK 详情请参考: [知识图谱管理 SDK 文档](sdk_docs/knowledge_graph_sdk.md)

