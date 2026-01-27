from dataclasses import dataclass, field
from typing import Self
from pymilvus import DataType
from pathlib import Path

@dataclass
class KGExtractionCriteria:
    blocked_entities: list[str] = field(default_factory=list)
    blocked_segments: list[str] = field(default_factory=list)
    entity_aliases: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load_criteria(cls, path: str | Path | None = None) -> Self:
        if path is None:
            path = Path.cwd() / "kgraph.toml"

        import tomllib

        data = {}
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            pass

        return cls(**data)

GRAPH_FIELD_SEP = "<SEP>"

# NOTE: 3 members in hurag.OPTIONS["chunk"] moved to here and renamed to constants:

CHK_DELIMITER = "|||||"
SEG_DELIMITER = "====="
TXT_SEPARATORS = [r"\n\n", r"\n", r"(?<=[。！？；])", r" "]

INIT_RSS_STATEMENTS = """
DROP TABLE IF EXISTS community_entity;
DROP TABLE IF EXISTS communities;
DROP TABLE IF EXISTS entity_cite;
DROP TABLE IF EXISTS relation_cite;
DROP TABLE IF EXISTS relations;
DROP TABLE IF EXISTS entities;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS segments;
DROP TABLE IF EXISTS documents;
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title VARCHAR(100) UNIQUE NOT NULL,
    sn VARCHAR(50),
    date DATE NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE,
    replaces VARCHAR(100),
    pub_path VARCHAR(100) NOT NULL,
    localizes VARCHAR(100),
    authors VARCHAR(100),
    kg_built BOOLEAN NOT NULL,
    INDEX idx_valid_from (valid_from),
    INDEX idx_valid_to (valid_to),
    INDEX idx_pub_path (pub_path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE segments (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    seq_no INT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    segment_id UUID NOT NULL,
    seq_no INT NOT NULL,
    text VARCHAR(1000) NOT NULL,
    FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description VARCHAR(500)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE entity_cite (
    entity_id UUID NOT NULL,
    segment_id UUID NOT NULL,
    PRIMARY KEY (entity_id, segment_id),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE relations (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    type VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    strength FLOAT NOT NULL CHECK (strength >= 0),
    UNIQUE KEY uniq_relation (source_id, target_id, type),
    FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE relation_cite (
    relation_id UUID NOT NULL,
    segment_id UUID NOT NULL,
    PRIMARY KEY (relation_id, segment_id),
    FOREIGN KEY (relation_id) REFERENCES relations(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE communities (
    id INT PRIMARY KEY,
    summary VARCHAR(1000) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE community_entity (
    community_id INT NOT NULL,
    entity_id UUID NOT NULL,
    PRIMARY KEY (community_id, entity_id),
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

INIT_VSS_PARAMS = [
    {
        "name": "chunks",
        "fields": [
            {
                "field_name": "id",
                "datatype": DataType.VARCHAR,
                "max_length": 36,
                "is_primary": True,
            },
            {
                "field_name": "dense_vec",
                "datatype": DataType.FLOAT_VECTOR,
                "dim": 1024,
            },
            {
                "field_name": "sparse_vec",
                "datatype": DataType.SPARSE_FLOAT_VECTOR,
            },
            {
                "field_name": "doc_id",
                "datatype": DataType.VARCHAR,
                "max_length": 36,
            },
        ],
        "indice": [
            {
                "field_name": "dense_vec",
                "index_type": "AUTOINDEX",
                "index_name": "dense_idx",
                "metric_type": "COSINE",
            },
            {
                "field_name": "sparse_vec",
                "index_type": "AUTOINDEX",
                "index_name": "sparse_idx",
                "metric_type": "IP",
            },
            {
                "field_name": "doc_id",
                "index_name": "doc_idx",
            },
        ],
    },
    {
        "name": "nodes",
        "fields": [
            {
                "field_name": "id",
                "datatype": DataType.VARCHAR,
                "max_length": 36,
                "is_primary": True,
            },
            {
                "field_name": "dense_vec",
                "datatype": DataType.FLOAT_VECTOR,
                "dim": 1024,
            },
            {
                "field_name": "sparse_vec",
                "datatype": DataType.SPARSE_FLOAT_VECTOR,
            },
        ],
        "indice": [
            {
                "field_name": "dense_vec",
                "index_type": "AUTOINDEX",
                "index_name": "dense_idx",
                "metric_type": "COSINE",
            },
            {
                "field_name": "sparse_vec",
                "index_type": "AUTOINDEX",
                "index_name": "sparse_idx",
                "metric_type": "IP",
            },
        ],
    },
    {
        "name": "edges",
        "fields": [
            {
                "field_name": "id",
                "datatype": DataType.VARCHAR,
                "max_length": 36,
                "is_primary": True,
            },
            {
                "field_name": "dense_vec",
                "datatype": DataType.FLOAT_VECTOR,
                "dim": 1024,
            },
            {
                "field_name": "sparse_vec",
                "datatype": DataType.SPARSE_FLOAT_VECTOR,
            },
        ],
        "indice": [
            {
                "field_name": "dense_vec",
                "index_type": "AUTOINDEX",
                "index_name": "dense_idx",
                "metric_type": "COSINE",
            },
            {
                "field_name": "sparse_vec",
                "index_type": "AUTOINDEX",
                "index_name": "sparse_idx",
                "metric_type": "IP",
            },
        ],
    },
    {
        "name": "communities",
        "fields": [
            {
                "field_name": "id",
                "datatype": DataType.INT64,
                "is_primary": True,
                "auto_id": False,
            },
            {
                "field_name": "dense_vec",
                "datatype": DataType.FLOAT_VECTOR,
                "dim": 1024,
            },
            {
                "field_name": "sparse_vec",
                "datatype": DataType.SPARSE_FLOAT_VECTOR,
            },
        ],
        "indice": [
            {
                "field_name": "dense_vec",
                "index_type": "AUTOINDEX",
                "index_name": "dense_idx",
                "metric_type": "COSINE",
            },
            {
                "field_name": "sparse_vec",
                "index_type": "AUTOINDEX",
                "index_name": "sparse_idx",
                "metric_type": "IP",
            },
        ],
    },
]

