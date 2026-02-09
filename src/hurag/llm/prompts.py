import json
from datetime import datetime

RERANK_PROMPT = "找出与查询最相关的文档，请同时结合原文标题、发布机构、生效范围等元数据与正文内容综合判断，生效时间、机构、范围等采用就近就低原则。"

PROMPTS = {}

PROMPTS["TUPLE_DELIMITER"] = "<|>"

PROMPTS["ENTITY_TYPES"] = [
    "组织",
    "角色",
    "概念",
    "类别",
    "任务",
    "事件",
    "活动",
    "流程",
    "步骤",
    "数据",
    "资料",
    "制度",
    "规则",
]

PROMPTS["entity_extraction"] = """你是一个专业的信息提取助手，专门从事以下工作：

## 目标

给定一段中文文本和一组实体类型，从文本中精确识别所有属于这些类型的实体，并识别出这些实体之间的所有关系。
使用中文作为输出语言。

## 步骤和要求

1. 识别所有实体。为每一个识别到的实体，提取以下信息:

- entity_name: 实体的名称，应该为一些较短的概括性的中文名词性短语。
- entity_type: 下列类型之一: [{entity_types}]
- entity_description: **在文本中**实体的属性和活动的完整描述。

### 实体识别要点

- 实体必须具有明确的业务含义或指向一个具体的对象或事物。
- **绝对不要**提取以下类型的无意义实体：
   - **指代词**：例如“本规定”、“本制度”、“本办法”、“有关法律法规”、“有关规定”等。
   - **文档结构**：例如“第一章”、“第二节”、“第三条”、“第4项”、“附件五”、“表6”、“图7”等。
   - **泛化词**：例如“有关部门”、“相关单位”、“管理机构”、“上级组织”、“下属单位”、“相关人员”等。

将每一个实体按此格式记录: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. 在通过步骤1所识别得到的所有实体中，识别所有彼此明确相关的 (source_entity, target_entity) 对，为每一个相关实体对，提取以下信息:

- source_entity: 源实体的名称，与步骤1所识别的实体名称一致。
- target_entity: 目标实体的名称，与步骤1所识别的实体名称一致。
- relation_description: 解释为什么你认为源实体与目标实体是相关的。
- relation_type: 一个高层次关键词，用以总结二者间关系的总体性质，应侧重于概念或主题，而非具体细节。
- strength: 一个数值评分，用以表示源实体与目标实体之间关系的强度。请使用0到1之间的浮点数，**0表示完全不相关，1表示强相关**。

将每一对关系按此格式记录: ("relation"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relation_description>{tuple_delimiter}<relation_type>{tuple_delimiter}<strength>)

3. 使用中文返回输出，步骤1和步骤2识别到的实体和关系每项一条记录，每条记录一行。

4. 你必须：
- 完全遵守用户提供的输出格式要求。
- 若文本中找不到符合所给类型且有明确意义的实体，直接返回空，不要编造。
- 当不确定实体或实体间关系时保持谨慎，尽可能确保识别精准。

## 示例

### 示例

实体类型: ["组织", "角色", "任务", "事件", "类别", "流程", "制度", "概念", "活动", "规则"]
文本:
```
第三编 合同 第一分编 通则 第二章 合同的订立 第四百九十七条 有下列情形之一的，该格式条款无效：
（一）具有本法第一编第六章第三节和本法第五百零六条规定的无效情形；
（二）提供格式条款一方不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利；
（三）提供格式条款一方排除对方主要权利。
```

输出:
("entity"{tuple_delimiter}合同{tuple_delimiter}概念{tuple_delimiter}法律规定的双方或多方之间设立、变更、终止民事权利义务关系的协议。)
("entity"{tuple_delimiter}格式条款{tuple_delimiter}制度{tuple_delimiter}由一方预先拟定，另一方只能选择接受或拒绝的合同条款。)
("entity"{tuple_delimiter}无效情形{tuple_delimiter}规则{tuple_delimiter}法律规定的导致格式条款无效的具体情况。)
("relation"{tuple_delimiter}合同{tuple_delimiter}格式条款{tuple_delimiter}格式条款是合同中的一种特殊条款类型。{tuple_delimiter}包含关系{tuple_delimiter}0.7)
("relation"{tuple_delimiter}格式条款{tuple_delimiter}无效情形{tuple_delimiter}格式条款在特定情况下会被法律认定为无效。{tuple_delimiter}条件关系{tuple_delimiter}0.9)

## 实际数据

实体类型: [{entity_types}]
文本:
{input_text}

输出:
"""

PROMPTS["entity_gleaning"] = """上一次识别的实体和关系可能有遗漏，请尽量补充完整。

**记住以下步骤和要求**：

## 步骤和要求

1. 识别所有实体。为每一个识别到的实体，提取以下信息:

- entity_name: 实体的名称，应该为一些较短的概括性的中文名词性短语。
- entity_type: 下列类型之一: [{entity_types}]
- entity_description: **在文本中**实体的属性和活动的完整描述。

### 实体识别要点

- 实体必须具有明确的业务含义或指向一个具体的对象或事物。
- **绝对不要**提取以下类型的无意义实体：
   - **指代词**：例如“本规定”、“本制度”、“本办法”、“有关法律法规”、“有关规定”等。
   - **文档结构**：例如“第一章”、“第二节”、“第三条”、“第4项”、“附件五”、“表6”、“图7”等。
   - **泛化词**：例如“有关部门”、“相关单位”、“管理机构”、“上级组织”、“下属单位”、“相关人员”等。

将每一个实体按此格式记录: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. 在通过步骤1所识别得到的所有实体中，识别所有彼此明确相关的 (source_entity, target_entity) 对，为每一个相关实体对，提取以下信息:

- source_entity: 源实体的名称，与步骤1所识别的实体名称一致。
- target_entity: 目标实体的名称，与步骤1所识别的实体名称一致。
- relation_description: 解释为什么你认为源实体与目标实体是相关的。
- relation_type: 一个高层次关键词，用以总结二者间关系的总体性质，应侧重于概念或主题，而非具体细节。
- strength: 一个数值评分，用以表示源实体与目标实体之间关系的强度。请使用0到1之间的浮点数，**0表示完全不相关，1表示强相关**。

将每一对关系按此格式记录: ("relation"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relation_description>{tuple_delimiter}<relation_type>{tuple_delimiter}<strength>)

3. 使用中文返回输出，步骤1和步骤2识别到的实体和关系每项一条记录，每条记录一行。

4. 你**必须**：
- 完全遵守用户提供的输出格式要求。
- 若文本中找不到符合所给类型且有明确意义的实体，直接返回空，不要编造。
- 当不确定实体或实体间关系时保持谨慎，尽可能确保识别精准。

5. **上一次已经识别的实体和关系不要再次输出，请严格按照完全相同的格式要求进行补充**。

---

输出:
"""

PROMPTS[
    "summarize_descriptions"
] = """你是一名专业的知识处理专家，你的职责是对下面所提供的数据生成一段全面、综合的缩写。
给定一个或两个实体，以及一系列与该实体或实体组相关的描述，请将所有这些描述串联起来，缩写成一单段全面的、综合性的描述，确保涵盖从所提供的全部描述中收集到的所有信息。
如果所提供的描述中存在矛盾，请分析解决该矛盾，提供一致的、条理清晰的缩写。
请确保采用第三人称进行缩写，不分段，完全使用中文并严格控制在200字以内。

#######
---数据---
实体: {entity_name}
描述列表: {description_list}
#######
输出:
"""

PROMPTS["community_summarize"] = """
你是一名中文的知识图谱摘要撰写专家，擅长把若干实体（名称 + 描述）概括为结构化的子摘要，语言严谨、术语统一、避免冗词。

## 任务
根据提供的实体集合，对由其构成的知识图谱社区生成一段**社区摘要**，其中每个节点都有“名称”和“描述”，请生成一个简洁、精准且全面的摘要，用于概括整个社区的主题。

## 要求：
- 简明扼要（最多1-2句话）
- 突出节点的主要主题和共同特征
- 避免逐一列出节点名称
- 不改写原有的专用名词，不引入新事实
- 语言清晰、专业
- 强调节点集合整体代表的意义
- 总长度不超过500个中文字符

## 输入格式：
[
  {{
    "name": "节点1",
    "description": "节点1的描述"
  }},
  {{
    "name": "节点2",
    "description": "节点2的描述"
  }},
  ...
]

## 输出格式：
一段文字，总结整个社区的整体含义。

## 实际输入:
{input_text}

## 输出：
"""

PROMPTS["community_summary_aggregate"] = """
你是一名中文的知识图谱摘要撰写专家，擅长把若干图谱社区子集的子摘要合成为一份整个社区的最终总体摘要，语言严谨、术语统一、避免冗词。

## 任务
根据提供的若干子摘要进行综合汇总，生成最终的总体摘要。所有子摘要均为一个大规模知识图谱社区中的多个划分子集的摘要，所有这些子集之间无交集，共同构成该大社区。

## 要求
- 简明扼要（最多1-2句话）
- 突出整个社区的主要主题和共同特征
- 覆盖所有子摘要中的关键信息
- 不改写原有的专用名词，不引入新事实
- 语言清晰、专业
- 强调社区整体代表的意义
- 总长度不超过500个中文字符

## 输入格式：
[
  "子摘要1",
  "子摘要2",
  ...
]

## 输出格式：
一段文字，总结整个社区的整体含义。

## 实际输入:
{input_text}

## 输出：
"""

PROMPTS["keywords_extraction"] = """---角色---
你是一名专业的关键词提取专家，擅长为检索增强生成（RAG，Retrieval-Augmented Generation）系统分析用户查询。你的目标是识别用户查询中的高层和低层关键词，以便进行高效的文档检索。

---目标---
给定一个用户查询和相关的查询历史，你需要提取两类关键词：
1. **high_level_keywords**：高层关键词，表示总体概念或主题，用于捕捉用户的核心意图、主题领域或问题类型。
2. **low_level_keywords**：低层关键词，表示具体的实体或细节，用于识别特定实体、专有名词、技术术语、产品名称或具体对象。

---指令与约束---
1. **提取范围**：从用户的当前查询文本中提取关键词，如果当前查询中存在隐含的、或含义不清晰的、或使用指代词代替的关键信息，请尝试根据查询历史来提取对应的明确关键词。
2. **输出语言**：无论用户查询使用何种语言，你的输出都必须使用中文，若用户查询中包含多语言内容，请统一用中文提取并返回。输出仅包含人类可读的内容，不要使用任何Unicode图形字符。
3. **输出格式**：你的输出必须是一个**有效的 JSON 对象**，输出内容将使用JSON解析器进行解析，所以不能包含任何解释性文字、Markdown 代码块标记（如 ```json）或其他多余内容。
4. **来源约束**：所有关键词必须**明确来源于用户查询（包括历史查询）**，高层和低层关键词都必须在查询内容中有所提及。
5. **简洁且有意义**：关键词应为简洁的词语或有意义的短语。若多词短语代表一个完整概念，应优先使用。例如，对于查询 "苹果公司的最新财报"，应提取 "最新财报" 和 "苹果公司"，而不是 "最新"、"财务"、"报告"、"苹果"。
6. **特殊情况处理**：对于过于简单、模糊或无意义的查询（例如 “hello”、“你好”、“asdfghjkl”），你必须返回一个包含空列表的 JSON 对象，格式如下：
{{"high_level_keywords": [], "low_level_keywords": []}}

---示例---
{examples}

---真实数据---
查询历史:
{history}

当前查询:
{query}

---输出---
输出：
"""

PROMPTS["keywords_extraction_examples"] = [
    """
示例 1:

查询历史:


当前查询:
采购方式有哪些？投资项目中涉及的采购是否也必须遵守企业采购相关的制度？

输出:
{"high_level_keywords": ["投资项目采购"], "low_level_keywords": ["采购方式", "投资项目", "采购制度"]}
""",
    """
示例 2:

查询历史:
企业常用的采购方式有哪些？
投资项目中涉及的采购是否也必须遵守企业采购相关的制度？

当前查询:
投资和采购之间在计划层面、项目层面、执行层面都有哪些不同和关联？

输出:
{
  "high_level_keywords": ["投资和采购", "计划层面", "项目层面", "执行层面", "不同和关联"],
  "low_level_keywords": ["企业采购方式", "投资项目采购", "采购制度"]
}
""",
    """
示例 3:

查询历史:
公司有没有对绿色发展提出过具体的工作方案和目标任务？

当前查询:
对企业的影响有哪些？

输出:
{"high_level_keywords": ["绿色发展", "企业影响"], "low_level_keywords": ["工作方案", "目标任务"]}
""",
]

PROMPTS["time_with_effectivity"] = """---角色---
你是一名时间信息分析专家，任务是从用户查询中提取那些**与文档有效性强相关**的时间点。

---任务目标---
给定一段用户查询文本，你需要：
1. 分析查询语义，判断其中出现的时间信息是否用于限定所找文档的**生效时间或有效性**。
2. 仅当时间确实用于限定文档有效性（即用户关注“当时的规定”“当时的制度”“生效版本”等）时，才输出该时间。
3. 若时间仅用于描述事件发生时间、举例、背景或未来计划，而与文档有效性无关，则不要输出该时间。

---判断原则---
1. 若用户问题包含以下语义，应视为**与文档有效性强相关**：
  - “当时的规定 / 当期制度 / 生效版本 / 当年的标准 / 当时政策 / 有效期内的文件”
  - 涉及历史制度、政策变迁、合规性、文件版本、适用性等语义。
2. 若用户问题的时间仅表示事件背景、发生时间、成果时间、计划时间、预测时间等，则不视为强相关。
3. 若时间表述模糊或不确定（如“最近几年”、“过去一段时间”），仅当语义明显涉及制度或版本变化时才保留。
4. 若查询中未提及任何时间信息，或所有时间点均非强相关，则返回空列表。

---时间标准化要求---
1. 若用户仅提到年份或月份，补全为该时间段最后一天：
  – 仅提到“年份” → 使用该年最后一天，例如：`2023` → `2023-12-31`。 
  – 提到“季度” → 使用该季度的最后一天（Q1:03-31，Q2:06-30，Q3:09-30，Q4:12-31），例如：`2023年3季度` → `2023-09-30`。  
  – 提到“月份” → 使用该月的最后一天（闰年2月取02-29，平年02-28），例如：`2023年2月` → `2023-02-28`，若为闰年（如2024年）则为 `2024-02-29`。
2. 若用户使用相对时间（如“今年”“明年”“上个月”“去年底”），请基于上下文按照以下规则进行解析：
  - 以今天日期为参考基准。
  - 相对表达应被解析为对应的绝对日期范围的**最后一天**。
  - 若表达含糊无法准确确定具体时间点，则忽略该项。
  - 所有日期均使用公历。
3. 输出格式：严格 JSON 列表，元素为 "YYYY-MM-DD" 字符串，无额外文字。

---边界保护---
1. 禁止输出任何解释、注释或 Markdown 代码块。
2. 禁止编造文本中不存在的时间。
3. 若日期非法或无法解析，跳过该条目。

---参考信息---
今天是：{today}

---输入---
用户查询：{query}

---输出---
输出：
"""

PROMPTS["time_with_effectivity_examples"] = [
    """
示例 1:

当前查询:2023年的采购项目实施过程是否规范，应当查询当时的采购管理制度，也即2022年9月14日发布的制度。

输出:
["2022-09-14"]
""",
    """
示例 2:

当前查询:2021年3月出台的全省采购管理制度中，一共有7种采购方式，三年后的新版制度中则减少为6种。

输出:
["2021-03-31", "2024-03-31"]
""",
    """
示例 3:

当前查询:2023年9月开展的一次科技创新活动取得的成效非常好，因此我们从明年开始每三年固定组织一次此活动，请问公司有没有关于组织开展集体活动的相关制度规定？

输出:
[]
""",
]


def create_entity_extraction_prompt(text: str) -> str:
    entity_extract_prompt = PROMPTS["entity_extraction"]
    context_base = {
        "tuple_delimiter": PROMPTS["TUPLE_DELIMITER"],
        "entity_types": ", ".join(PROMPTS["ENTITY_TYPES"]),
        "input_text": "\n".join(["```", text, "```"]),
    }
    return entity_extract_prompt.format(**context_base)


def create_entity_gleaning_prompt() -> str:
    entity_gleaning_prompt = PROMPTS["entity_gleaning"]
    context_base = {
        "tuple_delimiter": PROMPTS["TUPLE_DELIMITER"],
        "entity_types": ", ".join(PROMPTS["ENTITY_TYPES"]),
    }
    return entity_gleaning_prompt.format(**context_base)


def create_summarize_descriptions_prompt(
    entity_name: list[str], descriptions: set[str]
) -> str:
    summarize_descriptions_prompt = PROMPTS["summarize_descriptions"]
    context_base = {
        "entity_name": " - ".join(entity_name),
        "description_list": list(descriptions),
    }
    return summarize_descriptions_prompt.format(**context_base)


def create_community_summarize_prompt(entities) -> str:
    return PROMPTS["community_summarize"].format(
        input_text=json.dumps(entities, ensure_ascii=False, indent=2)
    )


def create_community_summary_aggregate_prompt(texts) -> str:
    return PROMPTS["community_summary_aggregate"].format(
        input_text=json.dumps(texts, ensure_ascii=False, indent=2)
    )


def create_keywords_extraction_prompt(
    query: str, history: list[str] = [], ex_num: int = 3
) -> str:
    keywords_extraction_prompt = PROMPTS["keywords_extraction"]
    context_base = {
        "history": history,
        "query": f"'{query}'",
        "examples": "\n".join(PROMPTS["keywords_extraction_examples"][:ex_num]),
    }
    return keywords_extraction_prompt.format(**context_base)


def create_timing_prompt(query: str) -> str:
    td = datetime.strftime(datetime.today(), "%Y-%m-%d")
    return PROMPTS["time_with_effectivity"].format(today=td, query=query)
