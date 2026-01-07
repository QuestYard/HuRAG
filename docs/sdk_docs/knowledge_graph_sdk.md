# Knowledge Graph SDK Documentation

`hurag.knowledge_graph` 模块和 `hurag.schemas.graph` 模块提供了构建和管理知识图谱的核心功能。

## Graph Schema (`hurag.schemas.graph`)

该模块定义了知识图谱的基本数据结构，包括实体 (`Entity`)、关系 (`Relation`) 和图 (`Graph`)。

### Entity 类

`Entity` 类表示知识图谱中的节点（实体）。

**属性：**

- `id` (str | None): 实体的唯一标识符。
- `name` (str | None): 实体名称。
- `type` (str | None): 实体类型。
- `description` (str | None): 实体描述。
- `seg_ids` (str | None): 来源片段 ID，多个 ID 用分隔符连接。

**主要方法：**

- `create(fields, segment_id, alias)`: 从 LLM 提取的字符串记录解析并创建实体对象。
- `__add__` / `__iadd__`: 支持实体合并操作，将两个同名实体的属性（类型、描述、来源片段）进行拼接。

### Relation 类

`Relation` 类表示知识图谱中的边（关系）。

**属性：**

- `id` (str | None): 关系的唯一标识符。
- `source` (str | None): 源实体名称。
- `target` (str | None): 目标实体名称。
- `type` (str | None): 关系类型。
- `description` (str | None): 关系描述。
- `strength` (float): 关系强度（权重）。
- `seg_ids` (str | None): 来源片段 ID。

**主要方法：**

- `create(fields, segment_id, alias)`: 从 LLM 提取的字符串记录解析并创建关系对象。
- `__add__` / `__iadd__`: 支持关系合并操作，将两个同源同目标关系的属性进行拼接，并累加强度。

### Graph 类

`Graph` 类表示一个完整的知识图谱，包含节点和边。

**属性：**

- `nodes` (list[Entity]): 实体列表。
- `edges` (list[Relation]): 关系列表。

**主要方法：**

- `parse_and_dedupe(response, segment_id, alias)`: 解析 LLM 响应字符串，提取实体和关系并添加到图中（自动去重）。
- `resolve(blacklist)`: 异步方法，对图谱进行解析和清洗：
    1.  根据黑名单过滤实体。
    2.  移除孤立的关系（源或目标实体不存在）。
    3.  合并同名实体和相同关系。
    4.  与数据库中已存在的图谱数据进行合并。
- `remove_orphans()`: 移除没有边连接的孤立节点和没有端点的悬空边。
- `clear()`: 清空图谱中的所有节点和边。
- `from_responses(responses, alias)`: 类方法，从 LLM 的提取结果列表创建 Graph 对象。
- `from_db(ids, titles)`: 类方法，从数据库加载由 `ids` 和 `titles` 共同指定的文档构建而成的知识图谱。

## Knowledge Graph Management (`hurag.knowledge_graph`)

该模块提供了利用 LLM 进行知识图谱构建的高级功能。

### extract_kg_elements

`extract_kg_elements` 函数用于从文档片段中提取知识图谱元素（实体和关系）。

```python
async def extract_kg_elements(
    document_ids: str | list[str] | None = None,
    num_extracting_workers: int = 10,
    num_gleaning_workers: int = 10,
    limit: int | None = None,
    oaclient = None,
) -> dict[str, dict[str, str]]
```

**功能描述：**

该函数会扫描数据库中尚未构建图谱的文档 (`kg_built == False`)，并使用 LLM 对其文本片段进行处理。处理过程包含两个阶段：
1.  **Extraction (提取)**: 初步提取文本中的实体和关系。
2.  **Gleaning (拾遗)**: 基于初步提取的结果和原始文本，再次检查是否有遗漏的实体和关系。

**参数说明：**

- `document_ids`: 指定要处理的文档 ID 或 ID 列表。如果为 `None`，则处理所有未构建图谱的文档。
- `num_extracting_workers`: 提取阶段的并发工作协程数。
- `num_gleaning_workers`: 拾遗阶段的并发工作协程数。
- `limit`: 限制处理的片段数量（用于测试）。

**返回值：**

返回一个包含提取结果的字典列表，每个字典包含文档 ID、片段 ID、原始文本以及 LLM 的提取和拾遗响应。

### normalize_kg_elements

`normalize_kg_elements` 函数用于对提取出的知识图谱进行标准化处理。

```python
async def normalize_kg_elements(
    g: Graph,
    num_workers: int = 20,
    oaclient = None,
) -> Graph
```

**功能描述：**

该函数对 `Graph` 对象中的实体和关系进行以下标准化操作：
1.  **Type Voting (类型投票)**: 对于合并后的实体或关系，统计其所有出现的类型，选择出现频率最高的作为最终类型。
2.  **Description Rewriting (描述重写)**: 对于合并后的实体或关系，如果存在多个描述，使用 LLM 将它们汇总重写为一个精炼的描述。

**参数说明：**

- `g`: 待标准化的 `Graph` 对象。
- `num_workers`: 标准化处理的并发工作协程数。

**返回值：**

返回标准化后的 `Graph` 对象。

### community_leiden

`community_leiden` 函数用于根据知识图谱中的实体和关系创建无向图，并使用 Leiden 算法进行社区发现。

```python
async def community_leiden(
    resolution: float = 0.5
) -> tuple[ig.Graph, ig.clustering.VertexClustering, dict[str, tuple[str, str]]]
```

**功能描述：**

该函数从数据库中读取实体和关系，构建 `igraph.Graph` 对象（无向图），然后应用 Leiden 算法对图节点进行聚类，从而发现社区结构。

**参数说明：**

- `resolution`: `float` 类型，Leiden 算法的分辨率参数，默认值为 0.5。不建议大于 1。

**返回值：**

返回一个元组，包含以下三个元素：
1. `g`: `igraph.Graph` 对象，表示构建的无向图。
2. `partitions`: `igraph.clustering.VertexClustering` 对象，Leiden 算法生成的社区划分结果。
3. `nodes`: 一个字典，将实体 ID 映射到其名称和描述 `(name, description)`。

### summarize_communities

`summarize_communities` 函数利用 LLM 对发现的每个社区进行摘要生成。

```python
async def summarize_communities(
    graph: ig.Graph,
    partitions: ig.clustering.VertexClustering,
    nodes: dict[str, tuple[str, str]],
    batch_size: int = 90,
    min_size: int = 10,
    num_workers: int = 20,
    oaclient = None,
) -> dict[int, list[str]]
```

**功能描述：**

该函数遍历每个社区，利用社区内的节点信息（名称和描述），使用 LLM 生成社区摘要。对于较大的社区，会进行分批处理，并在最后进行汇总。

**参数说明：**

- `graph`: `igraph.Graph` 对象，知识图谱。
- `partitions`: `igraph.clustering.VertexClustering` 对象，社区划分结果。
- `nodes`: 包含实体信息的字典 `{ id: (name, description), ... }`。
- `batch_size`: 每批处理的节点数量，默认为 90。
- `min_size`: 社区的最小节点数，小于此值的社区将被跳过，默认为 10。
- `num_workers`: 摘要生成的并发工作协程数，默认为 20。

**返回值：**

返回一个字典，键为社区编号，值为该社区的摘要列表 `[summary, ...]`（可能包含多级摘要，最后一项为最终汇总摘要）。

