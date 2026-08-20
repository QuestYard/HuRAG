from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime


class CommunitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="知识图谱社区的唯一ID")
    summary: str = Field(
        description="知识图谱社区内容摘要说明", examples=["本社区主要包含以下内容……"]
    )


class CategorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="文档类目唯一ID", examples=["UUID7-ID"])
    path: str = Field(description="类目全路径名称", examples=["行业规章/综合管理"])
    description: str | None = Field(default=None, description="类目简介")


class AttachmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="附件文档唯一ID", examples=["UUID7-ID"])
    title: str = Field(description="附件标题", examples=["附件1_XX表模板"])
    document_id: str = Field(description="所属正文文档唯一ID", examples=["UUID7-ID"])


class DocumentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="文档唯一ID", examples=["UUID7-ID"])
    title: str = Field(description="文档标题", examples=["《民法典》"])
    sn: str | None = Field(default=None, description="法令号或文号，可为 None")
    date: datetime = Field(description="发布日期")
    pub_path: str = Field(description="发布路径，详见 HuRAG 说明文档")
    valid_from: datetime = Field(description="生效日期")
    valid_to: datetime | None = Field(description="废止日期，未废止则为 None")
    replaces: str | None = Field(description="上一版本文档标题，若无则为 None")
    localizes: str | None = Field(description="上位版本文档标题，若无则为 None")
    authors: str | None = Field(description="作者，若无则为 None")
    is_multimodal: bool = Field(description="是否为多模态文档")
    attachments: list[AttachmentSchema] = Field(
        default_factory=list, description="附件列表"
    )

    @field_validator("title", "replaces", "localizes", mode="before")
    @classmethod
    def clean_multimodal_prefix(cls, value: str | None) -> str | None:
        if value is not None:
            return value.lstrip("*")

        return value


class FileContentSchema(BaseModel):
    id: str = Field(description="文档唯一ID", examples=["UUID7-ID"])
    title: str = Field(
        description = "标题，附件文档包含正文标题",
        examples = ["《民法典》", "《XX管理制度》附件1_XX表模板"],
    )
    content: str = Field(description="文档内容", examples=["文档内容"])


class ListDocumentsRequest(BaseModel):
    user_org_path: str = Field(
        description="用户所在组织机构路径", examples=["/总部/大区/某市公司"]
    )
    category_ids: list[str] = Field(
        default_factory=list, description="文档类目ID列表，不提供表示全部类目"
    )
    title_keywords: list[str] = Field(
        default_factory=list,
        description="文档标题关键字，用于模糊匹配，不提供则不做关键字匹配",
        examples=[["竞争", "垄断"]],
    )


class VectorSearchRequest(BaseModel):
    query: str = Field(examples=["政府采购行为的定义是什么？"])
    user_org_path: str | None = Field(
        default = None,
        description = "用户所在组织机构路径，不提供则使用服务端组织机构",
        examples = ["/总部/大区/某市公司"],
    )
    document_ids: list[str] = Field(
        default_factory=list, description="搜索的文档范围，不提供则全库搜索"
    )
    rerank: bool = Field(default=False, description="检索结果是否重排序")
    top_k: int | None = Field(
        default=None, description="返回的最大知识段落数，不提供则使用服务端配置", gt=0
    )
    rrf_k: float | None = Field(
        default=None, description="混合向量搜索RRF参数，不提供则使用服务端配置", gt=0
    )


class GraphSearchRequest(BaseModel):
    query: str = Field(examples=["政府采购行为的定义是什么？"])
    user_org_path: str | None = Field(
        default=None,
        description="用户所在组织机构路径，不提供则使用服务端组织机构",
        examples=["/总部/大区/某市公司"],
    )
    rerank: bool = Field(default=False, description="检索结果是否重排序")
    top_k_entities: int | None = Field(
        default=None, description="返回的最大知识实体数，不提供则使用服务端配置", gt=0
    )
    top_k_relations: int | None = Field(
        default=None, description="返回的最大知识关系数，不提供则使用服务配置", gt=0
    )
    top_k_segments: int | None = Field(
        default=None, description="返回的最大知识段落数，不提供则使用服务端配置", gt=0
    )
