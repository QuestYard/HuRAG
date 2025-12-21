# HuRAG SDK Documentation

HuRAG 提供了 Python SDK，方便开发者在自己的应用中集成 HuRAG 的 RAG 检索和 LLM 调用能力。通过 HuRAG SDK，可以快速构建面向法律法规解释的智能问答系统、文档检索系统等应用。

HuRAG SDK 包括多个模块，涵盖了知识库管理、文档管理、用户管理、RAG 检索和 LLM 调用等功能。开发者可以根据自己的需求，灵活调用 SDK 提供的接口，实现各种应用场景。

## Common Utilities

HuRAG SDK 提供了一些常用的工具函数、工具类和单例模式的工具变量，方便开发者进行日志管理、配置管理等操作。

### Configurations

HuRAG SDK 使用 `hurag.yaml` 配置文件进行配置管理，开发者可以通过 `hurag` 模块中的单例全局变量 `conf` 获取全部配置项。

`conf` 是一个嵌套的 `namespace` 对象，成员和结构与 `hurag.yaml` 配置文件中的内容一一对应。例如，可以通过 `conf.milvus.uri` 获取 Milvus 的连接 URI。

```python
from hurag import conf
# 获取 Milvus 连接 URI
milvus_uri = conf.milvus.uri
# 获取 MariaDB 数据库名称
mariadb_database = conf.mariadb.database
```

### Logging

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

## DataStorage Services

HuRAG 使用 Milvus 作为向量数据存储，使用 MariaDB/MySQL 作为关系型数据存储，并通过二者自行构建了一套图数据存储，实现简洁高效的知识图谱能力。HuRAG SDK 提供了对这些数据存储服务的封装，方便开发者进行数据存储和管理操作。

数据存储服务集中在 `hurag.dss` 模块下，包含以下子模块：
- `hurag.dss.vss`: 向量数据存储服务，封装了对 Milvus 的操作。
- `hurag.dss.rss`: 关系型数据存储服务，封装了对 MariaDB/MySQL 的操作。
- `hurag.dss.gss`: 图数据存储服务，基于 Milvus 和 MariaDB/MySQL 实现。

### Common DSS Utilities

HuRAG SDK 提供了一些数据存储服务的通用工具，方便开发者进行数据存储相关的操作。

#### Decorators

TODO: Add more details about decorators usage.

#### DSS Initializer

TODO: Add more details about DSS Initializer usage.

### Vector DataStorage Service

HuRAG SDK 使用 `hurag.dss.vss` 模块封装了对 Milvus 向量数据库的操作，提供了对向量数据的存储、检索和管理功能。开发者可以通过该模块中的接口函数方便地进行向量数据的操作。

TODO: Add more details about VSS usage.

### Relational DataStorage Service

HuRAG SDK 使用 `hurag.dss.rss` 模块封装了对 MariaDB/MySQL 数据库的操作，提供了对用户、角色、权限等关系型数据的管理功能。开发者可以通过该模块中的接口函数方便地进行数据库操作。

TODO: Add more details about RSS usage.

### Graph DataStorage Service

HuRAG SDK 使用 `hurag.dss.gss` 模块封装了对图数据的存储和管理功能，基于 Milvus 和 MariaDB/MySQL 实现。开发者可以通过该模块中的接口函数方便地进行图数据的操作。

TODO: Add more details about GSS usage.

## Knowledge Base Management

TODO: Add more details about Knowledge Base Management usage.

## Corpus Management

TODO: Add more details about Corpus Management usage.
