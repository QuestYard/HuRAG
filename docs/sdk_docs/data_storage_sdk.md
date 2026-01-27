# HuRAG Data Storage Service Documentation

## 数据库结构

HuRAG 使用的数据库结构包括关系型数据和向量数据两部分，包括了普通 RAG 所需的数据结构，以及知识图谱所需的数据结构。

详细的数据结构设计请参考 [HuRAG 数据库结构设计文档](./data_storage_schema.md)。

## 数据存储服务工具函数

HuRAG SDK 提供了一些数据存储服务的通用工具，方便开发者进行数据存储相关的操作。

`hurag.dss` 模块提供了两个装饰器 `with_rdb` 和 `with_vdb`，用于简化数据库连接和客户端的生命周期管理。

### 多数据库支持

HuRAG SDK 支持连接多个不同数据库，包括 MySQL/MariaDB 关系型数据库和 Milvus 向量数据库。

项目自身使用的数据库在 `hurag.yaml` 中配置，其使用的 `aiomysql.Pool` 和 `AsyncMilvusClient` 使用标识名 `"default"`，不需要显式调用创建连接池或客户端，直接使用默认参数调用 SDK 即可自动创建连接。

同时也支持其他依赖 `hurag` 库的项目复用 SDK，为此，可以在代码中显式调用 `rss.get_pool()` 或 `vss.get_client()` 函数，传入数据库连接参数和一个不同的标识名来创建连接池或客户端，在调用 SDK 时将该标识名传递给命名参数 `pool_name` 或 `client_name`，即可利用项目提供的数据存储服务 SDK 来访问其他数据库。

### with_rdb 装饰器

`with_rdb` 装饰器用于自动注入关系型数据库（MariaDB/MySQL）的连接和游标对象。它会自动处理连接池的获取和释放。

**参数说明：**

- `connection_arg_name` (str, optional): 注入到被装饰函数中的连接对象参数名，默认为 `"connection"`。
- `cursor_arg_name` (str, optional): 注入到被装饰函数中的游标对象参数名，默认为 `"cursor"`。
- `dict_cursor` (bool, optional): 是否使用字典游标（返回结果为字典），默认为 `False`。
- `ss_cursor` (bool, optional): 是否使用服务端游标（用于处理大量数据），默认为 `False`。
- `pool_name` (str, optional): 连接池的标识名，默认为 `"default"`。

**使用示例：**

```python
from hurag.dss import with_rdb

@with_rdb(connection_name="conn", cursor_name="cur", dict_cursor=True)
async def get_user_by_id(user_id: int, conn=None, cur=None):
    await cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return await cur.fetchone()

# 调用时无需传递 conn 和 cur 参数
user = await get_user_by_id(1)
```

### with_vdb 装饰器

`with_vdb` 装饰器用于自动注入向量数据库（Milvus）的客户端对象。它会自动处理客户端的连接和关闭。

**参数说明：**

- `client_arg_name` (str, optional): 注入到被装饰函数中的客户端对象参数名，默认为 `"client"`。
- `client_name` (str, optional): 注入到被装饰函数中的客户端标识名，默认为 `"default"`。

**使用示例：**

```python
from hurag.dss import with_vdb

@with_vdb(client_name="milvus_client")
async def search_vectors(vectors: list, milvus_client=None):
    res = await milvus_client.search(
        collection_name="my_collection",
        data=vectors,
        limit=10
    )
    return res

results = await search_vectors([[0.1, 0.2, ...]])
```

### RDB 生命周期

本项目采用 `aiomysql` 作为 MariaDB/MySQL 的异步客户端，使用连接池管理数据库连接。在应用关闭时必须关闭并销毁。

对于 API 服务，可以为 FastAPI app 对象指定一个 `AsyncContextManager` 类型的 `lifespan` 属性，用于管理连接池的生命周期。例如：

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    ... # 此处可添加其他启动任务
    
    yield

    ... # 此处可添加其他关闭任务
    from hurag.dss.rss import close_pool
    await close_pool()

app = FastAPI(lifespan=lifespan)
```

对于 CLI 命令等短生命周期应用，可以在主函数中手动调用 `rss.close_pool()` 来关闭连接池。也可以使用 `hurag.cli` 模块内置的 `async_cmd` 装饰器，使用方式如下：

```python
# 装饰器使用示例
from hurag.cli import async_cmd

@app.command("info")
@async_cmd
async def info():
    ... # CLI 命令函数逻辑，可安全使用数据库，异步调用无需 asyncio.run
```

### VDB 生命周期

本项目采用 `pymilvus` 的 `AsyncMilvusClient` 异步客户端连接和访问向量数据库。连接的客户端在应用关闭时必须关闭并销毁。

和 RDB 的生命周期管理类似，项目在 `hurag.dss.vss` 模块中提供了 `close_client()` 函数用于关闭和销毁客户端，可以使用和 RDB 一样的方法来管理 VDB 生命周期。

`hurag.cli` 模块的 `async_cmd` 装饰器同时支持向量数据库客户端的生命周期管理。

### 初始化数据存储

`hurag.dss` 模块提供了 `init_ds()` 函数，用于初始化数据存储服务。该函数会根据配置文件中的设置，初始化 Milvus 和 MariaDB 后台数据库。

*警告：该函数会删除所有现有数据，包括所有文档和知识图谱，仅在首次部署或重置数据存储时使用。*

`hurag.dss` 模块的 `clear_graph()` 函数可以清除知识图谱相关的数据，包括 MariaDB 中的实体和关系数据，以及 Milvus 中的向量数据。

*以上两个初始化函数仅对 HuRAG 自身的数据存储进行初始化，即配置在 `hurag.yaml` 中的数据库。*

### FastAPI 依赖注入支持

`hurag.depends` 模块提供了 FastAPI 依赖项，用于将数据库连接和客户端注入到 API 处理函数中。

#### RDB 连接池 (`Pool`)

用于获取 `aiomysql.Pool` 连接池对象。

- **`HuragRdbPoolDep`**: 注入默认连接池（对应 `hurag.yaml` 配置）。
- **`rdb_pool`**: 函数依赖，用于注入自定义配置的连接池。

**使用示例：**

使用 `HuragRdbPoolDep` 注入默认数据库连接池：

```python
from hurag.depends import HuragRdbPoolDep

@app.get("/db1")
async def _db1(pool: HuragRdbPoolDep):
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM documents")
        ret = await cur.fetchall()
        return { "number_of_documents": ret[0][0] }
```

使用 `rdb_pool` 注入其他自定义的数据库连接池：

```python
from hurag.depends import rdb_pool
from fastapi import Depends
from typing import Annotated

db2_params = {
    "host": "localhost",
    "port": 3306,
    "user": "username",
    "password": "password",
    "db": "another_db",
    "pool_name": "another_pool",    # 此参数值不能为 "default"
}

@app.get("/db2")
async def _db2(pool: Annotated["aiomysql.Pool", Depends(rdb_pool(**db2_params))]):
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM documents")
        ret = await cur.fetchall()
        return { "number_of_documents": ret[0][0] }
```

#### RDB 连接 (`Connection`)

用于获取 `aiomysql.Connection` 连接对象。相比连接池，直接注入连接通常更简单且推荐使用。

- **`HuragRdbConnectionDep`**: 注入默认数据库连接。
- **`rdb_connection`**: 函数依赖，用于注入自定义配置的数据库连接。

**使用示例：**

```python
from hurag.depends import HuragRdbConnectionDep

@app.get("/db1")
async def _db1(conn: HuragRdbConnectionDep):
    async with conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM documents")
        ret = await cur.fetchall()
        return { "number_of_documents": ret[0][0] }
```

自定义数据库连接的依赖用法类似。

#### VDB 客户端 (`AsyncMilvusClient`)

用于获取 `pymilvus.AsyncMilvusClient` 异步客户端对象。

- **`HuragVdbClientDep`**: 注入默认 Milvus 客户端。
- **`vdb_client`**: 函数依赖，用于注入自定义配置的 Milvus 客户端。

**使用示例：**

```python
from hurag.depends import HuragVdbClientDep

@app.get("/vdb1")
async def _vdb1(cli: HuragVdbClientDep):
    resp = await cli.list_collections()
    return { "collections": resp }
```

自定义数据库客户端的依赖用法类似。

## 向量存储服务模块

`hurag.dss.vss` 模块封装了对 Milvus 向量数据库的操作，提供了对向量数据的存储、检索和管理功能。开发者可以通过该模块中的接口函数方便地进行向量数据的操作。

### client

`client` 是一个异步上下文管理器，用于获取一个临时的 Milvus 客户端实例。它会自动处理连接的建立和关闭。通常用于需要直接调用 Milvus 客户端底层方法的场景。

**使用示例：**

```python
from hurag.dss.vss import client

async def check_collection():
    async with client() as cli:
        has_collection = await cli.has_collection("my_collection")
        print(f"Collection exists: {has_collection}")
```

### upsert

`upsert` 函数用于向指定的集合中插入或更新数据。如果数据的主键已存在，则更新该条数据；如果不存在，则插入新数据。

**参数说明：**

- `collection` (str): 目标集合名称。
- `data` (list[dict]): 要插入或更新的数据列表，每个元素为一个字典。

**使用示例：**

```python
from hurag.dss.vss import upsert

data = [
    {"id": 1, "vector": [0.1, 0.2], "text": "doc1"},
    {"id": 2, "vector": [0.3, 0.4], "text": "doc2"}
]
await upsert("my_collection", data)
```

### insert

`insert` 函数用于向指定的集合中插入数据。与 `upsert` 不同，如果主键冲突可能会导致错误（取决于 Milvus 的配置）。

**参数说明：**

- `collection` (str): 目标集合名称。
- `data` (list[dict]): 要插入的数据列表。

**使用示例：**

```python
from hurag.dss.vss import insert

data = [{"id": 3, "vector": [0.5, 0.6], "text": "doc3"}]
await insert("my_collection", data)
```

### query

`query` 函数用于根据过滤条件查询集合中的数据。

**参数说明：**

- `collection_name` (str): 目标集合名称。
- `filter` (str, optional): 过滤表达式，默认为空字符串（查询所有）。
- `output_fields` (list[str] | None, optional): 指定返回的字段列表，默认为 `None`（返回所有字段）。
- `**kwargs`: 传递给 Milvus `query` 方法的其他参数。

**使用示例：**

```python
from hurag.dss.vss import query

# 查询 id 为 1 的文档，只返回 text 字段
results = await query(
    collection_name="my_collection",
    filter="id == 1",
    output_fields=["text"]
)
```

### search

`search` 函数用于在集合中执行混合检索（Hybrid Search），结合了稠密向量（Dense Vector）和稀疏向量（Sparse Vector）的检索结果，并使用 RRF（Reciprocal Rank Fusion）进行重排序。

**参数说明：**

- `collection_name` (str): 目标集合名称。该集合必须包含 `dense_vec` 和 `sparse_vec` 两个向量字段。
- `vecs` (dict): 查询向量字典，格式为 `{"dense": dense_vector, "sparse": sparse_vector}`。
- `scope` (list | None, optional): 限定搜索范围的 ID 列表。如果为 `None`，则在全集合中搜索。
- `top_k` (int, optional): 返回的最相似结果数量，默认为 50。
- `rrf_k` (float, optional): RRF 算法中的参数 k，默认为 100。

**返回值：**

- `dict[str, float]`: 返回一个字典，键为文档 ID，值为相似度得分（距离）。

**使用示例：**

```python
from hurag.dss.vss import search

query_vectors = {
    "dense": [[0.1, 0.2, ...]],  # 稠密向量列表
    "sparse": [{"indices": [1, 10], "values": [0.5, 0.8]}] # 稀疏向量列表
}

# 在指定 ID 范围内进行混合检索
results = await search(
    collection_name="my_collection",
    vecs=query_vectors,
    scope=[1, 2, 3, 4, 5],
    top_k=10
)
```

## 关系型数据存储服务模块

`hurag.dss.rss` 模块封装了对 MariaDB/MySQL 数据库的操作，提供了对用户、角色、权限等关系型数据的管理功能。开发者可以通过该模块中的接口函数方便地进行数据库操作。

### get_pool

`get_pool` 函数用于获取或创建全局的数据库连接池。如果连接池尚未创建，它会根据配置自动创建一个新的连接池。通常情况下，开发者不需要直接调用此函数，而是通过 `with_rdb` 装饰器或 `query`、`dml` 等高级函数来隐式使用连接池。

**返回值：**

- `aiomysql.Pool`: 数据库连接池对象。

### close_pool

`close_pool` 函数用于关闭全局数据库连接池。通常在应用关闭时调用，例如在 FastAPI 的 `lifespan` 中。

**使用示例：**

```python
from hurag.dss.rss import close_pool

# 在应用关闭时调用
await close_pool()
```

### query

`query` 函数用于执行 SQL 查询语句（SELECT），并返回所有结果。它会自动从连接池获取连接，执行查询，然后释放连接。

**参数说明：**

- `statement` (str): 要执行的 SQL 查询语句。
- `data` (tuple, optional): 查询语句中的参数，默认为空元组。

**返回值：**

- `list[tuple]`: 查询结果列表，每一行是一个元组。

**使用示例：**

```python
from hurag.dss.rss import query

# 查询所有用户
users = await query("SELECT * FROM users")

# 带参数查询
user = await query("SELECT * FROM users WHERE id = %s", (1,))
```

### dml

`dml` 函数用于执行数据操作语句（INSERT, UPDATE, DELETE）。它会自动处理事务提交和回滚。

**参数说明：**

- `statement` (str): 要执行的 DML 语句。
- `data` (tuple | list[tuple] | None, optional): 语句中的参数。如果提供的是元组列表，则会使用 `executemany` 批量执行。

**返回值：**

- `int`: 受影响的行数。

**使用示例：**

```python
from hurag.dss.rss import dml

# 插入单条数据
count = await dml("INSERT INTO users (name) VALUES (%s)", ("Alice",))

# 批量插入数据
data = [("Bob",), ("Charlie",)]
count = await dml("INSERT INTO users (name) VALUES (%s)", data)
```

### transact

`transact` 函数用于在一个事务中执行多条 DML 语句。如果任何一条语句执行失败，整个事务将回滚。

**参数说明：**

- `statements` (list[str]): 要执行的 DML 语句列表。
- `data` (list[tuple | list[tuple] | None] | None, optional): 对应每条语句的参数列表。如果为 `None`，则所有语句都不带参数。

**返回值：**

- `int`: 所有语句受影响的总行数。

**使用示例：**

```python
from hurag.dss.rss import transact

stmts = [
    "INSERT INTO users (name) VALUES (%s)",
    "UPDATE stats SET user_count = user_count + 1"
]
data = [
    ("David",),
    None  # 第二条语句没有参数
]

# 在一个事务中执行插入和更新
total_affected = await transact(stmts, data)
```

## Graph DataStorage Service

`hurag.dss.gss` 模块封装了对图数据的存储和管理功能，基于 Milvus 和 MariaDB/MySQL 实现。开发者可以通过该模块中的接口函数方便地进行图数据的操作。

### upsert_graph

`upsert_graph` 函数用于将知识图谱（节点和边）及其向量表示存储到关系型数据库（RDB）和向量数据库（VDB）中。

**参数说明：**

- `g` (Graph): 知识图谱对象，包含节点和边。
- `embeddings` (list[dict]): 图谱中节点和边的向量表示列表。列表中的每个元素应包含 `dense_vecs` 和 `sparse_vecs`。
- `doc_ids` (list[str]): 贡献该图谱的文档 ID 列表。

**功能描述：**

1.  **向量存储**：将节点和边的向量表示存入向量数据库（VDB）。
2.  **关系存储**：将节点（实体）、边（关系）及其引用信息存入关系型数据库（RDB）。
3.  **状态更新**：更新文档表，标记这些文档的知识图谱已构建。
4.  **字段截断**：在存入 RDB 时，会自动对以下字段进行截断以符合数据库限制：
    - 节点名称 (`name`): 最大 100 字符
    - 节点描述 (`description`): 最大 500 字符
    - 边描述 (`description`): 最大 500 字符

**使用示例：**

```python
from hurag.dss.gss import upsert_graph

# 假设已有 graph 对象 g, embeddings 列表, 和 doc_ids
await upsert_graph(g, embeddings, doc_ids)
```

### save_communities

`save_communities` 方法用于将生成的社区（Community）信息及其摘要向量保存到 RDB 和 VDB 中。

> **注意**：该方法在保存新社区之前，会清空现有的所有社区数据（包括 RDB 中的 `communities`、`community_entity` 表以及 VDB 中的 `communities` 集合）。

```python
async def save_communities(
    graph: ig.Graph,
    partitions: ig.clustering.VertexClustering,
    communities: list[dict[str, Any]],
) -> tuple[int, int]
```

**功能描述：**

1.  **清理旧数据**：删除 RDB 和 VDB 中已有的社区相关数据。
2.  **保存社区信息 (RDB)**：将社区 ID 和生成的摘要保存到 `communities` 表。
3.  **保存社区-实体关联 (RDB)**：根据 `partitions` 结果，建立社区与实体的关联，保存到 `community_entity` 表。
4.  **保存向量数据 (VDB)**：将社区摘要的稠密向量 (`dense_vec`) 和稀疏向量 (`sparse_vec`) 保存到 VDB 的 `communities` 集合中。

**参数说明：**

- `graph`: `igraph.Graph` 对象，表示知识图谱。
- `partitions`: `igraph.clustering.VertexClustering` 对象，Leiden 算法生成的社区划分结果。
- `communities`: 包含社区摘要及向量信息的字典列表。每个字典应包含：
    - `c_no`: 社区编号 (ID)
    - `summary`: 社区摘要文本
    - `dense_vec`: 摘要的稠密向量
    - `sparse_vec`: 摘要的稀疏向量

**返回值：**

返回一个元组 `(int, int)`，包含：
1.  保存的社区数量。
2.  保存的社区-实体关联数量。

**使用示例：**

```python
from hurag.dss.gss import save_communities

# 假设已有 graph, partitions 和 communities 列表
num_comms, num_assocs = await save_communities(graph, partitions, communities)
print(f"Saved {num_comms} communities and {num_assocs} associations.")
```

`graph` 和 `partitions` 来自于社区发现和摘要生成的过程，具体可参考: [knowledge_graph_sdk.md](./knowledge_graph_sdk.md) 中的 `community_leiden` 和 `summarize_communities` 函数。
`communities` 则是摘要生成后得到的社区信息及其向量表示，通过调用 `hurag.llm.embed_community_summaries` 函数可直接获取。

