from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas import Knowledge

RAG_PROMPT_TEMPLATE = """你是一名知识库问答助手，能够根据提供的相关知识引文，准确且简洁地回答用户的问题。

## 任务

现已提供一组与用户问题相关的知识引文，每段引文包含知识内容、文档元数据和相关性分数，相关性分数越高表示与问题越相关。

文档元数据包含该引文的出处文档的标题、发布日期、生效/废止时间、文号、发布机构路径、上一版本、上位版本等信息。

请基于这些知识引文，结合你的语言理解能力，生成对用户问题的回答。

## 回答要求

请遵循以下要求进行回答：
1. **内容依据**：必须基于上述知识引文内容和文档元数据作答，不得编造或引入外部知识。
2. **元数据考量**：回答时务必考虑文档的时效性（生效/废止日期）、版本关系（上位版本、替代版本）和权威性（法令号、发布路径）。
3. **不确定性处理**：若知识不足以回答问题，明确说明"根据提供的资料无法确定"。
4. **版本意识**：若存在多个版本，以最新有效版本为准；若提及被废止文件，需明确标注其已废止。
5. **简洁专业**：回答应准确、简洁、友好，必要时可给出简要背景解释，但不得虚构。

## 知识段

以下是为你检索到的知识引文：

{knowledge_segments}

请基于上述知识回答用户的问题。

## 用户问题

以下是用户提出的问题：

{query}

## 请回答：
"""


def create_rag_prompt(
    query: str,
    knowledge_list: list[tuple[Knowledge, float]],
    kn_limit: int | None = None,
) -> str:
    """
    Create a prompt for RAG based on the user query and knowledge segments.

    Arguments:
        query: The user query.
        knowledge_list: The list of knowledge segments.
        kn_limit: The maximum number of knowledge segments to include.
    Returns:
        The constructed prompt string.
    """
    knowledge_segments = []
    for idx, item in enumerate(
        knowledge_list[:kn_limit] if kn_limit else knowledge_list
    ):
        content = item[0].content.strip() if item[0].content else ""
        score = item[1]
        metadata = item[0].metadata
        _title = metadata.title
        _sn = metadata.sn
        _date = metadata.date
        _valid_from = metadata.valid_from
        _valid_to = f"{metadata.valid_to:%Y-%m-%d}" if metadata.valid_to else "未废止"
        _replaces = metadata.replaces
        _localizes = metadata.localizes
        _pub_path = metadata.pub_path

        knowledge_segments.append(
            f"### 引文 {idx + 1}\n"
            f"- **内容**: {content}\n"
            f"- **相关性分数**: {score:.4f}\n"
            f"- **文档元数据**: \n"
            f"  - **文档标题**: {_title}\n"
            f"  - **法令号/文号**: {_sn if _sn else '无'}\n"
            f"  - **发布日期**: {_date:%Y-%m-%d}\n"
            f"  - **生效日期**: {_valid_from:%Y-%m-%d}\n"
            f"  - **废止日期**: {_valid_to}\n"
            f"  - **上一版本**: {_replaces if _replaces else '无'}\n"
            f"  - **上位版本**: {_localizes if _localizes else '无'}\n"
            f"  - **发布机构路径**: {_pub_path}"
        )

    prompt = RAG_PROMPT_TEMPLATE.format(
        knowledge_segments="\n\n".join(knowledge_segments),
        query=query,
    )
    return prompt
