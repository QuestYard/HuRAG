# HuRAG

## Project Introduction

HuRAG是一个专注于法律法规解释的RAG应用，它能基于文档的时序和层次构建知识图谱并应用于检索增强（TH-GraphRAG），通过对文档发布时间和组织结构的理解，HuRAG能够更准确地检索和生成符合用户需求的答案。

HuRAG的设计面向组织型用户，不仅仅用于个人用途。它可以应用于具有复杂分支结构的大型组织中。

### Concepts

- **组织机构树（Organization Tree）**: HuRAG使用组织机构树来表示用户所属的组织结构。每个用户在组织机构树中有一个位置，这个位置决定了用户可以访问和检索哪些文档。参考：[组织机构树说明](docs/organization_tree_design.md)

- **知识文档（Documents）**: HuRAG中的知识文档包含文本内容和元数据属性，如发布时间、发布机构等。知识文档在入库前需要进行格式转换、格式化、标注、加载等处理。参考：[知识文档说明](docs/document_attributes_design.md)

### Key Features

- 支持4种检索模式，包括朴素搜索、混合搜索、图搜索和社区图搜索。
- 根据用户在组织机构树中的位置检索文档。
- 从用户查询中解析时间信息，并在检索时用于选择正确版本的文档。
- 使用Microsoft MarkItDown读取PDF、Word、Excel、PowerPoint、CSV、HTML、JSON、XML文档并转换为markdown格式。
- 自动分割和索引TXT、Markdown以及8种表格布局的CSV文件。
- 为法律、法规和其他类似法规的文档定义了良好的文本格式。

## News and Changelog

- [x] 2026-01-13: API Server 重构完毕，与测试阶段的 HuRAG WebUI 前段适配完成。第一阶段开发结束，将启动新版 WebUI 重构。
- [x] 2026-01-12: Python SDK (Indexing, Retrieval) 部分全部构建完毕，基础功能完成。
- [x] 2025-12-01: 仓库创建，HuRAG即将到来！

## Quick Start

HuRAG支持通过源代码安装部署。在部署之前，请确保您的环境中已安装以下依赖环境：

- Python 3.12 或更高版本
- uv 3.0 或更高版本
- Git 2.0 或更高版本
- 可通过网络访问的 MariaDB 或 MySQL 数据库
- 可通过网络访问的 Milvus 向量数据库
- QuestYard/embedding-service for HuRAG 服务：[embedding-service for HuRAG](https://github.com/QuestYard/embedding-service)

### Deployment

HuRAG 的部署包括下载安装、创建数据库、生成配置文件和启动 API Server，请按照以下步骤进行操作。

#### Install from source code

```bash
git clone https://github.com/QuestYard/HuRAG.git
cd HuRAG
uv sync --no-dev
```

目前HuRAG仅支持通过源代码安装部署，未来可能会提供更多的安装方式。

#### Create Database

使用 `root` 用户登录 MariaDB/MySQL 数据库，并执行以下 SQL 语句以创建 HuRAG 所需的数据库和用户：

```sql
CREATE DATABASE <your_db_name> CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER '<your_db_user>'@'%' IDENTIFIED BY '<your_db_password>';
GRANT ALL PRIVILEGES ON <your_db_name>.* TO '<your_db_user>'@'%';
FLUSH PRIVILEGES;
```

在 Milvus 中创建用于存储 HuRAG 的向量数据和用户，可以使用多种方法，以使用 python 脚本为例：

```python
from pymilvus import MilvusClient

# 创建客户端，使用身份验证建立连接
client = MilvusClient(uri="<your_milvus_uri>", token="root:Milvus")
# 创建数据库
client.create_database(db_name="<your_milvus_db_name>")
# 创建用户
client.create_user(
    user_name="<your_milvus_user>",
    password="<your_milvus_password>",
)
# 创建角色
client.create_role(role_name="<your_milvus_role>")
# 给用户赋予角色
client.grant_role(
    user_name="<your_milvus_user>",
    role_name="<your_milvus_role>",
)
# 给角色赋予权限
client.grant_privilege_v2(
                    role_name="<your_milvus_role>",
                    privilege="CollectionAdmin",
                    collection_name="*",
                    db_name="<your_milvus_db_name>",
                )
# 使用新用户重新连接客户端
client = MilvusClient(
                uri="<your_milvus_uri>",
                token="<your_milvus_user>:<your_milvus_password>",
            )
```

#### Generate Configuration File

在工作目录下创建 `hurag.yaml` 配置文件，内容参照项目提供的示例 [hurag.yaml.sample](hurag.yaml.sample) 并根据实际情况修改配置项。

示例配置文件中注释为必配的配置项必须填写，其他配置项若无不同可以不提供。其中 `milvus` 和 `mariadb` 两部分中的必配项根据上一步骤中创建的数据库和用户信息进行填写。

配置文件中的 `llm.generation` 和 `llm.extraction` 部分用于配置 HuRAG 使用的语言模型，分别用于生成式问答和信息抽取。二者均采用字符串形式指定模型，配置的模型名称必须和环境变量配置文件 `.env` 中的模型参数变量名保持对应。

例如，若在 `hurag.yaml` 中配置 `llm.generation.model` 为 `"GLM"`，则在 `.env` 文件中需要配置以下三个环境变量：`GLM_BASE_URL`、`GLM_API_KEY` 和 `GLM_MODEL`。其中 `GLM_MODEL` 用于指定具体的模型名称，如 `"glm-4-flash-250414"`。

注意，环境变量名均为大写且下划线分隔。由于真正的模型名称在 `.env` 文件中配置，因此在 `hurag.yaml` 中的模型名称仅作为引用标识符使用，可以使用简称，只需要在环境变量名中保持对应即可。

#### Start API Server

HuRAG 提供基于 FastAPI 的 API Server，可以通过以下命令启动测试环境：

```bash
cd /path/to/HuRAG
source .venv/bin/activate  # 激活虚拟环境
cd /path/to/your-working-directory  # 切换到工作目录
hurag-server # 启动 HuRAG API Server 测试环境
```

测试环境会在代码发生改变时自动重加载，适用于开发和调试。若要启动生产环境，请使用 gunicorn 并在服务器（Linux）环境下配置为 systemctl 服务。

gunicorn 服务启动脚本模板见 [HuRAG-Server gunicorn 启动服务脚本模板](hurag_svr.service.1)

HuRAG API Server 默认监听 5002 端口，提供以下 API 接口：

- `/docs` : HuRAG API 文档页面，基于 OpenAPI 规范生成，提供接口说明和在线测试功能。
- `/health` : (GET) 健康检查接口，用于检查服务状态。
- `/v1/info` : (GET) 基本信息接口，提供 HuRAG 基本信息。
- `/v1/info/version` : (GET) 版本信息接口，提供 HuRAG 版本信息。
- `/v1/info/organization` : (GET) 组织机构接口，提供部署应用的组织机构信息。
- `/v1/llm/chat` : (POST) 聊天接口，提供基于 RAG 的聊天问答功能，支持 SSE 流式响应。
- `/v1/hurag/retrieve` : (POST) 检索接口，提供基于 RAG 的文档检索功能。
- `/v1/hurag/knowledge` : 知识查询接口，提供根据 ID 查询知识段的功能。

服务启动后，即可通过 `http://<server_host>:5002/docs` 访问 HuRAG API 文档页面。

## Usages

HuRAG 提供命令行工具和 SDK 调用两种使用方式，命令行工具用于系统后台管理和维护，SDK 提供 RAG 索引和检索功能的 Python 函数调用，用于构建其他应用。基于 HuRAG API，可以快速构建面向法律法规解释的智能问答系统、文档检索系统等应用。

另外，HuRAG 提供的 RestFul API Server 可直接用于构建 RAG 类 Web 应用，使得应用端的构建可以不依赖于本地安装的 HuRAG 库。QuestYard 的 [QuestYard Chat](https://github.com/QuestYard/hurag-webui) 就是一个基于 HuRAG 构建的智能问答系统。

API 的调用方法请参考 HuRAG API 的 Swagger 文档页面。

### Command Line Tool

HuRAG 提供的命令行工具包括知识库管理、文档管理和用户管理等功能，具体命令和用法请参考 [HuRAG CLI Documentation](docs/cli_documentation.md)。

### Python SDK Usage

HuRAG Python SDK 调用文档请参考 [HuRAG SDK Documentation](docs/sdk_documentation.md)。
