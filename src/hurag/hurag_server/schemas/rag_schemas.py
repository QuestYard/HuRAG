from pydantic import BaseModel, Field
from typing import Any

from datetime import datetime

class QueryRequest(BaseModel):
    query: str = Field(..., example="What is an LLM?")
    history: list[str] = Field(
        default_factory=list,
        example=[
            "What is artificial intelligence?",
            "What is machine learning?",
        ],
    )
    domains: list[str] = Field(default_factory=list, example=[])
    modes: list[str] = Field(default_factory=list, example=[])
    graph_search: bool | str = Field(default="mix")
    rerank: bool = Field(default=True)
    user_path: str | None = Field(default=None, example="总部/大区/某市公司")

class KnowledgeRequest(BaseModel):
    ids: list[str] = Field(..., example=["001", "002"])
    user_path: str | None = Field(default=None, example="总部/大区/某市公司")

class KnowledgeMetadataSchema(BaseModel):
    id: str = Field(..., description="文档唯一标识符")
    title: str = Field(..., description="文档标题") 
    sn: str | None = Field(..., description="法令号或文号，若无则为 None")
    date: datetime = Field(..., description="发布日期")
    pub_path: str = Field(..., description="发布路径，详见 HuRAG 说明文档")
    valid_from: datetime = Field(..., description="生效日期")
    valid_to: datetime | None = Field(..., description="废止日期，未废止则为 None")
    replaces: str | None = Field(..., description="上一版本文档标题，若无则为 None")
    localizes: str | None = Field(..., description="上位版本文档标题，若无则为 None")
    authors: str | None = Field(..., description="作者，若无则为 None")

class KnowledgeSchema(BaseModel):
    segment_id: str = Field(..., description="知识段唯一标识符")
    content: str = Field(..., description="文本内容，表示检索到的知识片段正文")
    metadata: KnowledgeMetadataSchema = Field(..., description="段落所属文档的元信息")
    score: float = Field(..., description="检索返回的匹配得分（越高表示越相关）")
