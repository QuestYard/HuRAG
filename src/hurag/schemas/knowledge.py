from dataclasses import dataclass, field
from datetime import datetime

@dataclass(kw_only=True, frozen=True)
class KnowledgeMetadata():
    id: str | None = field(default=None)
    title: str | None = field(default=None)
    sn: str | None = field(default=None)
    pub_path: str | None = field(default=None)
    valid_from: datetime | None = field(default=None)
    valid_to: datetime | None = field(default=None)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })

@dataclass(kw_only=True, frozen=True)
class Knowledge():
    segment_id: str = field(default=None)
    content: str = field(default=None, compare=False, hash=False)
    metadata: KnowledgeMetadata = field(
        default_factory=KnowledgeMetadata,
        compare=False,
        hash=False,
    )

    def __repr__(self):
        return f"Knowledge(segment_id={self.segment_id}, brief={self.brief})"

    @property
    def context(self) -> str:
        """create context for LLM"""
        t = []
        t.append(f"## 原文标题\n{self.metadata.title}")
        if self.metadata.sn:
            t[-1] += f"（{self.metadata.sn}）"
        t[-1] += "\n"
        org_name = self.metadata.pub_path.strip('*').split('/')[-1]
        propagate = (
            not self.metadata.pub_path.startswith("/")
            or self.metadata.pub_path.endswith("*")
        )
        t.append(f"## 发布机构\n{org_name}\n")
        t.append(f"## 生效范围\n{'含下级' if propagate else '仅本级'}\n")
        t.append(f"## 生效日期\n{self.metadata.valid_from:%Y-%m-%d}\n")
        if self.metadata.valid_to:
            t.append(f"## 废止日期\n{self.metadata.valid_to:%Y-%m-%d}\n")
        t.append(f"## 正文内容\n{self.content}\n")

        return "\n".join(t)

    @property
    def brief(self) -> str:
        """create brief for print"""
        return f"{self.metadata.title}: {' '.join(self.content[:40].split('\n'))}"
