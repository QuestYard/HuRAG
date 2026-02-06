from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from ...types import RetrieveMode

class QueryRequest(BaseModel):
    query: str = Field(examples=["What is an LLM?"])
    history: list[str] = Field(
        default_factory=list,
        examples=[
            ["What is artificial intelligence?", "What is machine learning?"],
        ],
        description="只需提供用户历史查询，无需大模型的历史答复。"
    )
    graph_search: bool | RetrieveMode = Field(default="mix")
    user_path: str | None = Field(default=None, examples=["总部/大区/某市公司"])

class KnowledgeRequest(BaseModel):
    ids: list[str] = Field(examples=[["001", "002"]])
    user_path: str | None = Field(default=None, examples=["总部/大区/某市公司"])

class KnowledgeMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="文档唯一标识符")
    title: str = Field(description="文档标题") 
    sn: str | None = Field(description="法令号或文号，若无则为 None")
    date: datetime = Field(description="发布日期")
    pub_path: str = Field(description="发布路径，详见 HuRAG 说明文档")
    valid_from: datetime = Field(description="生效日期")
    valid_to: datetime | None = Field(description="废止日期，未废止则为 None")
    replaces: str | None = Field(description="上一版本文档标题，若无则为 None")
    localizes: str | None = Field(description="上位版本文档标题，若无则为 None")
    authors: str | None = Field(description="作者，若无则为 None")

class KnowledgeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment_id: str = Field(description="知识段唯一标识符")
    content: str = Field(description="文本内容，表示检索到的知识片段正文")
    metadata: KnowledgeMetadataSchema = Field(description="段落所属文档的元信息")
    score: float = Field(default=0.0, description="检索返回的相关度匹配得分")
