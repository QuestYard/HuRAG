# HuRAG SDK Documentation

HuRAG 提供了 Python SDK，方便开发者在自己的应用中集成 HuRAG 的 RAG 检索和 LLM 调用能力。通过 HuRAG SDK，可以快速构建面向法律法规解释的智能问答系统、文档检索系统等应用。

HuRAG SDK 包括多个模块，涵盖了知识库管理、文档管理、用户管理、RAG 检索和 LLM 调用等功能。开发者可以根据自己的需求，灵活调用 SDK 提供的接口，实现各种应用场景。

## 通用工具

HuRAG SDK 提供了一些常用的工具函数、工具类和单例模式的工具变量，方便开发者进行日志管理、配置管理等操作。

### 系统配置

HuRAG SDK 使用 `hurag.yaml` 配置文件进行配置管理，开发者可以通过 `hurag` 模块中的单例全局变量 `conf` 获取全部配置项。

`conf` 是一个嵌套的 `SimpleNamespace` 对象，成员和结构与 `hurag.yaml` 配置文件中的内容一一对应。例如，可以通过 `conf.milvus.uri` 获取 Milvus 的连接 URI。

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
async def get_text_embedding(esclient, text: str) -> list[float]:
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

`esclient` 参数由装饰器自动传入，开发者无需手动提供。用户也可以使用装饰器参数 `client_arg_name` 来指定不同的注入参数名称。

### Reranker Service 调用

HuRAG 使用 QuestYard Embedding Service 调用 Reranker 模型，通过装饰器 `with_es_client` 即可调用客户端的 `rerank` 函数实现重排序功能。

以对知识对象的重排序为例，`hurag.retrievers` 模块中提供了这一功能的 SDK 函数如下：

```python
@with_es_client
async def rerank_knowledge(
    query: str,
    knowledge_dict: dict[str, Knowledge],
    esclient: AsyncEmbeddingClient,
) -> list[list[Knowledge | float]]:
    """
    Rerank the input knowledge objects based on the query by using embedding-service.

    Args:
        query (str): the user query.
        knowledge_dict: A dict of knowledge objects like {id: Knowledge, ...}

    Returns:
        A list like [[Knowledge, score], ...]
    """
    contents = [k.context for k in knowledge_dict.values()]
    response = await esclient.rerank(query, contents)
    if not response.scores:
        response.scores = [0.0] * len(contents)
    results = sorted(
        zip(knowledge_dict.values(), response.scores),
        key=lambda x: x[1],
        reverse=True,
    )
    return [[k, s] for k, s in results]
```

*注意：`rerank_knowledge(...)` 函数的返回值中，每一个知识对象和它对应的分值采用 list 存储，而非 tuple 类型。*
这是为了方便后续如有需要可以原地修改。例如 HuRAG 的检索结果，在 Rerank 结果的基础上还需要根据知识文档发布的机构层级进行得分衰减调整，若直接返回 tuple 则无法原地修改。

### OpenAI LLM 调用

HuRAG 采用 OpenAI SDK 作为大语言模型（LLM）的调用接口，所有支持 OpenAI 接口的模型均可调用。HuRAG SDK 在 `hurag.llm` 模块中封装了对 OpenAI SDK 的调用，提供了简化的接口，方便开发者在应用中集成 LLM 能力。

关于 LLM 的配置，请参考: [配置文件说明](../README.md#generate-configuration-file)

#### 基础调用

`hurag.llm` 模块提供了 `chat_completion(...)`, `chat_stream(...)` 两个函数，分别用于以非流式和流式两种返回模式调用 LLM 模型。

**函数签名**

```python
async def chat_completion(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    temperature: float = 0.0,
) -> ChatCompletion:
    ...

async def chat_stream(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    *,
    system_prompt: str | None = None,
    history_messages: list[dict[str, str]] | None = None,
    temperature: float = 0.0,
) -> AsyncStream:
    ...
```

**参数说明**

- `client`: `AsyncOpenAI` 客户端实例。
- `model`: 模型名称。
- `prompt`: 用户输入的提示词。
- `system_prompt`: 可选的系统提示词。
- `history_messages`: 可选的历史对话记录，格式为 `[{"role": "user", "content": "..."}, ...]`。
- `temperature`: 采样温度，默认为 0.0。

*函数退出不会关闭客户端连接，客户端的生命周期由调用方管理。*

*v0.1.0 版本提供的 `chat(...)`, `chat_with_retries(...)` 两个函数已经弃用，后续版本将予以删除。*

#### 结果提取

`hurag.llm` 模块提供了一个工具函数，用于从 LLM 返回的结果中提取内容：

`extract_from_chat(response: ChatCompletion | ChatCompletionChunk) -> dict[str, str]`

此函数在提取内容时，会检查 `role` 值，以确保返回值符合 `openai.types.chat.ChatCompletionMessageParam` 的格式规范。

*v0.1.0 版本提供的 `extract_response(...)`, `extract_chunk(...)` 两个函数已经弃用，后续版本将予以删除。*

#### 使用示例

**非流式调用示例**

```python
import asyncio
from hurag.llm import chat_completion, exract_from_chat

# 此处需提供一个已经创建的客户端对象 my_client，客户端创建、获取、关闭等生命周期管理见下节说明
async def main():
    response = await chat_completion(
        client=my_client,
        model="model-name",
        prompt="hello world",
    )
    message = extract_from_chat(response)
    print(message["content"])

if __name__ == "__main__":
    asyncio.run(main())
```

**流式调用示例**

```python
import asyncio
from hurag.llm import chat_stream, exract_from_chat

async def main():
    stream = await chat_stream(
        client=my_client,
        model="model-name",
        prompt="tell me something about AI",
    )
    
    print("Response:")
    async for chunk in stream:
        delta = extract_from_chat(chunk)
        print(delta["content"], end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
```

#### 客户端装饰器

`hurag.llm` 模块还提供了 `with_oa_client` 装饰器，用于自动创建和管理 `AsyncOpenAI` 客户端实例，并将其注入到被装饰的异步函数中。这在需要频繁创建客户端或希望简化客户端生命周期管理的场景下非常有用。

**函数签名**

```python
def with_oa_client(
    func=None,
    *,
    base_url=None,
    api_key=None,
    client_name=None,
    timeout=180.0,
    multimodal=False,
    client_arg_name="oaclient",
) -> Callable[..., Any]:
```

**参数说明**

- `base_url`: OpenAI API 的基础 URL。
- `api_key`: OpenAI API 的密钥。
- `client_name`: 可复用的 AsyncOpenAI 客户端的标签名。如果提供，则会获取或创建一个可复用的客户端，否则创建一个临时客户端，此时必须提供有效的 `base_url` 和 `api_key` 两个参数，且该临时客户端在被装饰函数退出后立即被关闭和清理，今后不能复用。如果提供的标签名为保留的 `extraction` 或者 `generation`，则不需要提供 `base_url` 和 `api_key`，这两个参数会从配置信息中读取；如果提供了其他标签名，除非能够确定对应的可复用客户端已经创建过，否则也应当提供 `base_url` 和 `api_key`。
- `timeout`: 请求超时时间（秒），用于设置 `read` 超时，默认为 180.0。
- `multimodal`: 是否用于多模态模型，若是则会在创建客户端时采用较长的超时设置，默认为 `False`。
- `client_arg_name`: 注入到被装饰函数中的参数名称，默认为 `"oaclient"`。

**使用示例**

```python
import asyncio
from hurag.llm import with_oa_client, chat_completion, extract_from_chat

# 使用装饰器自动注入 client，本例中注入临时客户端，退出时会关闭。如指定 client_name
# 以注入可复用的客户端，则退出时不会关闭。
# 注意：被装饰的函数需要接收 client_arg_name 指定的参数
@with_oa_client(
    base_url="https://api.openai.com/v1", 
    api_key="your-api-key", 
    client_arg_name="client" # 将客户端注入到名为 'client' 的参数中
)
async def custom_chat_task(prompt: str, client: AsyncOpenAI):
    # 直接使用注入的 client 调用 chat 函数
    response = await chat_completion(
        client=client 
        model="gpt-3.5-turbo",
        prompt=prompt,
    )
    return extract_from_chat(response)

async def main():
    result = await custom_chat_task("简单介绍一下 Python 装饰器")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

#### OpenAI 客户端生命周期

HuRAG 提供了可复用 OpenAI 客户端机制，用户可以通过签名 `client_name` 来创建和复用不会被自动关闭和销毁的客户端，其中保留了两个标签名 `"generation"` 和 `"extraction"` 专用于根据配置信息创建文本生成和信息提取的客户端，这两个标签名不能用于创建其他客户端。

可复用的客户端一旦创建后，项目不会自动关闭，必须在应用生命周期结束时手动关闭并销毁。

和 VDB/RDB 的生命周期管理类似，项目在 `hurag.llm` 模块中提供了 `close_oa_client()` 函数用于关闭和销毁客户端，可以使用和 VDB/RDB 一样的方法来管理 OpenAI 客户端的生命周期。

CLI 中调用 LLM，可以使用 `cli.async_cmd` 装饰器，该装饰器同时加载了 RDB、VDB、OpenAI 三者的生命周期管理，可以确保在 CLI 命令结束时关闭清理资源，而实现 CLI 功能的代码只需要调用资源完成业务逻辑即可。也可以采用创建临时客户端的方式调用 `llm.chat()` 函数，即传递参数 `base_url` 和 `api_key`，而不传递 `client` 参数。

#### FastAPI 依赖注入支持

`hurag.depends` 模块提供了 FastAPI 依赖项，用于将 OpenAI 客户端注入到 API 处理函数中。

- **HuragGenerationClient**: 注入 generation 客户端
- **HuragExtractionClient**: 注入 extraction 客户端
- **HuragMultiModalClient**: 注入 multimodal 客户端
- **`openai_client`**: 函数依赖，用于注入自定义配置的客户端。

**使用示例：**

使用 `HuragGenerationClient` 注入用于文本生成的客户端：

```python
from hurag.depends import HuragGenerationClient

@app.get("/openai_client")
async def _oa_client(client: HuragGenerationClient):
    ...
```

使用 `openai_client` 注入其他自定义的客户端：

```python
from hurag.depends import openai_client
from fastapi import Depends
from typing import Annotated

params = {
    "base_url": "https://base_url.com",
    "api_key": "the-token",
    "timeout": 120.0,
    "multimodal": False,
    "client_name": "other_client",    # 此参数值不能为 "extraction", "generation" 或 "multimodal"
}

@app.get("/openai_client")
async def _oa_client(pool: Annotated["openai.AsyncOpenAI", Depends(openai_client(**params))]):
    ...
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

## 知识检索

Knowledge Retrieval (知识检索) 是 HuRAG SDK 的核心功能模块，提供了对知识库和知识图谱的检索功能。知识检索模块封装在 `hurag.retrievers` 模块中，方便开发者进行知识检索相关的操作。

HuRAG 支持多种检索模式，包括基于向量的相似度检索和基于图谱的相关性检索。开发者可以根据应用需求，选择合适的检索模式。

- **naive**: （弃用）语义检索，直接基于向量相似度进行检索，内部使用密集-稀疏双向量检索机制，通过密集向量与稀疏向量的结合提升检索效果。
- **graph**: （弃用）图谱检索，在知识图谱中进行 n-hop 的 BPS 检索，对检索到的关联实体为进行进一步的语义匹配和排序，得到最终检索结果。
- **mix**: 语义-图谱混合检索，结合向量检索和图谱检索的优势，二者的结果归并后进行重排序得到最终结果。此为目前推荐的检索模式。
- **community**: 知识社区检索，基于知识社区，先在知识社区中选取语义相关社区，再在社区内进行关联性检索，得到最终结果，适用于大规模知识库。
- **global**: 全局检索，直接在整个知识库中进行全图关联性检索，适用于小规模知识库。

上述五种检索模式，目前性能最佳的为 `mix` 模式，在提问语义明确的情况下推荐优先使用，其次为 `community` 模式，适用于大规模知识库和复杂查询场景。`global` 模式适用于小规模知识库。`naive` 和 `graph` 模式已被弃用，为保持向前兼容，仍然支持 API 调用，但内部将统一采用 `mix` 模式实现。

### 知识检索 SDK

HuRAG SDK 在 `hurag.retrievers` 模块中封装了知识检索功能，提供了简化的接口，方便开发者进行知识检索操作。

Retrieval 阶段的 SDK 主要包括两个函数：

#### `prepare_for_searching` 函数

用于对用户查询进行预处理，包括关键词提取、时间点要素提取和查询向量生成。

预处理的结果以一个 `QueryInfo` 对象返回，这是一个 dataclass 类，包含一下属性：

```python
@dataclass
class QueryInfo:
    """
    keywords: high level and low level keywords extracted from the query.
    timings: time points extracted from the query, today if no time info in the query.
    embeddings: vector representations of the query, the high level keywords and the
        low level keywords, in order.
    """

    keywords: dict[str, list[str]] = field(default_factory=dict)
    timings: list[datetime] = field(default_factory=list)
    embeddings: dict[str, Any] = field(default_factory=dict)
```

其中 `embeddings` 属性包含密集和稀疏两种向量，键名分别为 `dense_vecs` 和 `sparse_vecs`，内部向量的排序依次对应查询、关键词的高层次表示和低层次表示。

**函数签名**

```python
@with_oa_client(
    base_url=os.getenv(f"{conf.llm.extraction}_BASE_URL"),
    api_key=os.getenv(f"{conf.llm.extraction}_API_KEY"),
)
async def prepare_for_searching(
    query: str,
    history: list[str] | None = None,
    oaclient: AsyncOpenAI | None = None,
) -> QueryInfo:
    """
    Extract keywords, timings from the query and embed the query.

    Arguments:
        query: The user query
        history: History queries. History responses are not needed

    Return:
        A QueryInfo object contains keywords, timings and embeddings.
    """
    ...
```

该函数是相对比较耗时的操作，如果同一 query 会被多次检索，建议对 `QueryInfo` 进行缓存，在后续检索阶段作为参数传递给 `retrieve` 函数，避免重复计算。

#### `retrieve` 函数

用于执行知识检索操作，支持多种检索模式。

**函数签名**

```python
async def retrieve(
    query: str,
    *,
    history: list[str] | None = None,
    mode: RetrieveMode = "mix",
    query_info: QueryInfo | None = None,
    user_path: str | None = None,
    top_k: int | None = None,
    top_a: int | None = None,
    top_k_naive: int | None = None,
    rrf_k_naive: float | None = None,
    top_k_graph: int | None = None,
    num_hops: int | None = None,
    max_communities: int | None = None,
    max_nodes: int | None = None,
) -> list[tuple[Knowledge, float]]:
    """
    Arguments:
        query: current user query.
        history: history queries, history responses are not needed.
        mode:
            "mix" (default): naive + graph;
            "naive": (deprecated) only naive;
            "graph": (deprecated) only graph search with top_k_graph segments;
            "global": nodes and edges in the whole graph;
            "community": nodes and edges inside communities.
            "agentic": retrieve knowledge via some agentic skill.
        query_info: returned values of prepare_for_searching.
        user_path: the organization path of current user.
        top_k: number of knowledges in final results in K-RAG search,
        top_a: number of knowledges in final results of associations search.
        top_k_naive: number of chunks in naive search results,
        rrf_k_naive: rrf_k for hybrid search,
        top_k_graph: number of chunks in graph search results,
        num_hops: (BPS) number of hops,
        max_communities: (BPS) maximum number of communities,
        max_nodes: (BPS) maximum number of nodes.

    Returns:
        A list like [(Knowledge, score), ...], descending ordered by scores.
    """
    ...
```

*v0.1.0 版本支持的 `naive`, `graph` 两种检索模式已经弃用，为确保 API/SDK 的前后兼容，在 `RetrieveMode` 类型中仍然保持其二者存在，但检索时将统一采用 `mix` 模式替代。*

*`agentic` 为 HuRAG 下一个大版本时计划实现的 AI Agent 模式的检索模式，目前仅为一个占位的模式名，功能尚未支持。*

该函数根据指定的检索模式，结合 `QueryInfo` 对象中的预处理结果，执行相应的检索操作，并返回排序后的知识对象列表。

若 `query_info` 参数为 `None`，则函数内部会调用 `prepare_for_searching` 函数对查询进行预处理。

若 `user_path` 参数为 `None`，则使用 `hurag.yaml` 中配置的 `org_path` 作为默认的用户组织路径。

其他检索相关的参数均可在 `hurag.yaml` 配置文件中进行配置，函数调用时可根据需要进行覆盖：

- `top_k`: 最终返回的知识对象数量，默认值为配置文件中的 `retriever.top_k`。
- `top_a`: 关联性检索返回的知识对象数量，默认值为配置文件中的 `retriever.top_a`。
- `top_k_naive`: 语义检索返回的文本块数量，默认值为配置文件中的 `retriever.top_s`。
- `rrf_k_naive`: 语义检索的 RRF 参数，默认值为配置文件中的 `retriever.rrf_k`。
- `top_k_graph`: 图谱检索返回的文本块数量，默认值为配置文件中的 `retriever.top_g`。
- `num_hops`: 图谱检索的跳数，默认值为配置文件中的 `retriever.max_depth`。
- `max_communities`: 图谱检索的最大社区数量，默认值为配置文件中的 `retriever.max_comms`。
- `max_nodes`: 图谱检索的最大节点数量，默认值为配置文件中的 `retriever.max_nodes`。
