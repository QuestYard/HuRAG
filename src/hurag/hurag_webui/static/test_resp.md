# HuRAG 2.0

## 概述

> **AI 知识体系 HuRAG 2.0** 在 HuRAG 1.0 基础上改进而来，实现了一种基于垂域、时序和层序进行精准检索约束的 DTH-GraphRAG 模式。
> - 在业务架构上，针对企业管理各类知识文档普遍具有专业领域、时效区间和管辖层级三种约束的情况，提出时序版本管理和管辖层级管理，引入图谱聚类，取代 1.0 版本中的“业务领域”和“应用模式”约束，实现更为自动和高效的知识分层分类管理模式。
> - 在技术架构上，采用更为合理的分包和应用融合架构，安装使用和二次开发更为便捷。
> - 在文档管理上，使用微软的 MarkItDown 应用和 LangChain 的 markdown splitter 扩展文档支持类型，支持 PDF, OFFICE, Markdown, TXT, CSV 等多种主流文档类型。

---

## 新闻

- [x] [2025-11-05] 🎯🎉✨ 2.0 基础库、RESTful API 服务库构建完毕，API 服务上线：[HuRAG 2.0 API](http://10.47.64.218:5002/docs) *HuRAG 1.0 仍然保留*

- [x] [2025-10-06] 🎯🎉✨ 省市两级投资、采购、规划、科技四类34篇文档，共计 2216 知识段落、9873 知识图谱节点和 18420 对知识关系入库完毕。

- [x] [2025-08-22] 🎯🎉✨ 今日正式启动构建啦！

- [x] [2025-08-11] 🎯🎉✨ 2.0 启动，开始前期准备工作。

---

## 模块说明

### 配置管理 (`conf`)

`conf` 函数利用 `@lru_cache(maxsize=1)` 装饰器，确保配置在整个应用生命周期中只加载一次。它首先加载默认配置 (`DEFAULT_CONF`)，然后尝试从工作目录下的 `config.yaml` 文件中加载并合并用户自定义配置，实现配置的深度合并。最终返回一个 `Tree` 结构，方便通过属性访问配置项，例如 `conf().log.log_in_file`。

```python
# hurag.performs.extract_kg_elements

async def extract_kg_elements(
    using_backup_llm_for_gleaning: bool=False,
    num_extracting_workers: int=10,
    num_gleaning_workers: int=10,
)-> dict[str, dict]:
    pass
```

---

### segments

Table 'segments' stores the segments of documents.

| Field       | Type        | Key | NUL | Description                                          |
|:-----------:|:-----------:|:---:|:---:|------------------------------------------------------|
| id          | UUID        | PK  | NO  | Segment ID, UUIDv7                                   |
| document_id | UUID        | FK  | NO  | Document ID, fk to documents(id) , cascade on delete |
| seq_no      | INT         |     | NO  | Segment sequence number, starting from 0             |

---

### Indicators

Let $n$ be the total number of segments in the database, and $m$ be the number of segments that have been processed. The processing progress indicator $P$ is defined as:

$$
P = \frac{m}{n} \times 100\%
$$

---

### 招投标条文示例

> 招标投标制度是社会主义市场经济体制的重要组成部分，……
>
> 为全面贯彻党的十九大和十九届历次全会精神，按照第十九届中央纪委第六次全会、国务院第五次廉政工作会议部署，现就严格执行招标投标法规制度、进一步规范招标投标各方主体行为提出以下意见。

---

### 条文型文档格式

条文型文档支持“编、分编、章、节、条”五级结构，每级的编号中间无空格，级标题中间无空格，编号和标题（或正文）之间留至少一个空格，以《民法典合同编》的开头为例：

```
第三编 合同
第一分编 通则
第一章 一般规定
第四百六十三条 本编调整因合同产生的民事关系。
第四百六十四条 合同是民事主体之间设立、变更、终止民事法律关系的协议。
婚姻、收养、监护等有关身份关系的协议，适用有关该身份关系的法律规定；没有规定的，可以根据其性质参照适用本编规定。
第一节 ……
……
```
