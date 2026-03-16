from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime


class CommunitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="知识图谱社区的唯一ID")
    summary: str = Field(
        description="知识图谱社区内容摘要说明", examples=["本社区主要包含以下内容……"]
    )


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
