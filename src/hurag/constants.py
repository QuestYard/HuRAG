from pymilvus import DataType

BLOCKED_NODES_PATTERNS = [
    r"本(?:文|法|规定|条例|细则|办法|制度|要求|规范|标准)",
    (
        r"(?:相关|有关)"
        r"(?:部门|机构|组织|单位|企业|规定|制度|法律|法规|规范|标准|要求)"
    ),
    (
        r"各?(?:上级|下级|直属|所属|下属|本级)?"
        r"各?(?:单位|部门|机构|单位|企业|公司)"
    ),
    (
        r"第\s*(?:[一二三四五六七八九十百千万亿零〇两\d]+)"
        r"\s*(?:分?[编册卷章]|部分|节|条|款|项)"
    ),
    r"(?:附件|附表|表|图)\s*(?:[一二三四五六七八九十百千万亿〇零两\d]+)",
    r"个人|人员|法人|自然人|中华人民共和国",
    r"(?:总|国家|省|区|市|县|分)(?:公司|局)",
    r"全?(?:省|市)?(?:行业|系统)",
    r"[一二三四]级目录编码",
]

NODES_ALIASES_MAPS = [
    ("中华人民共和国招标投标法", "中华人民共和国招标投标法"),
    ("招标投标法", "中华人民共和国招标投标法"),
    ("招投标法", "中华人民共和国招标投标法"),
    ("标法", "中华人民共和国招标投标法"),
    ("中华人民共和国招标投标法实施条例", "中华人民共和国招标投标法实施条例"),
    ("招标投标法实施条例", "中华人民共和国招标投标法实施条例"),
    ("招投标法实施条例", "中华人民共和国招标投标法实施条例"),
    ("标法实施条例", "中华人民共和国招标投标法实施条例"),
    ("工程、物资、服务管理委员会", "工程、物资、服务管理委员会"),
    ("三项工作管理委员会", "工程、物资、服务管理委员会"),
    ("三项工作管委会", "工程、物资、服务管理委员会"),
    ("管委会", "工程、物资、服务管理委员会"),
    ("采购工作领导小组", "采购工作领导小组"),
    ("采购领导小组", "采购工作领导小组"),
    ("采购办", "采购办"),
    ("采购管理办公室", "采购办"),
    ("采购工作领导小组办公室", "采购办"),
    ("投资管理委员会", "投资管理委员会"),
    ("投委会", "投资管理委员会"),
    ("投资管理委员会办公室", "投资管理委员会办公室"),
    ("投资办", "投资管理委员会办公室"),
    ("采购价格咨询服务研究室", "采购价格咨询服务研究室"),
    ("价格研究室", "采购价格咨询服务研究室"),
    ("价研室", "采购价格咨询服务研究室"),
    ("公开招标", "公开招标"),
    ("公招", "公开招标"),
    ("邀请招标", "邀请招标"),
    ("邀标", "邀请招标"),
    ("竞争性谈判", "竞争性谈判"),
    ("竞争谈判", "竞争性谈判"),
    ("竞谈", "竞争性谈判"),
    ("竞争性磋商", "竞争性磋商"),
    ("磋商", "竞争性磋商"),
    ("竞磋", "竞争性磋商"),
    ("直接采购", "直接采购"),
    ("直采", "直接采购"),
    ("质量管理小组", "质量管理小组"),
    ("QC小组", "质量管理小组"),
    ("质量管理小组活动", "质量管理小组活动"),
    ("QC小组活动", "质量管理小组活动"),
    ("QC活动", "质量管理小组活动"),
]

BLOCKED_SEGMENTS_PATTERNS = [
    "附则 本规定中的“以上”含本数，“以下”不含本数",
    "附则 本规定由制定机构负责解释",
    "附则 各下属机构应按照本单位实际参照本规定制定相应的实施细则",
    "附则 本规定自印发之日起执行",
]

INIT_RSS_STATEMENTS = """
DROP TABLE IF EXISTS community_entity;
DROP TABLE IF EXISTS communities;
DROP TABLE IF EXISTS entity_cite;
DROP TABLE IF EXISTS relation_cite;
DROP TABLE IF EXISTS relations;
DROP TABLE IF EXISTS entities;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS segments;
DROP TABLE IF EXISTS doc_domain;
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
CREATE TABLE doc_domain (
    document_id UUID NOT NULL,
    domain VARCHAR(50) NOT NULL,
    PRIMARY KEY (document_id, domain),
    KEY idx_domain (domain),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
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
]

