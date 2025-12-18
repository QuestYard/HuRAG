from .rss import with_rdb
from .vss import with_vdb

_INIT_RSS_STATEMENTS = """
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
);
CREATE TABLE segments (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    seq_no INT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    segment_id UUID NOT NULL,
    seq_no INT NOT NULL,
    text VARCHAR(1000) NOT NULL,
    FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
);
CREATE TABLE doc_domain (
    document_id UUID NOT NULL,
    domain VARCHAR(50) NOT NULL,
    PRIMARY KEY (document_id, domain),
    KEY idx_domain (domain),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description VARCHAR(500)
);
CREATE TABLE entity_cite (
    entity_id UUID NOT NULL,
    segment_id UUID NOT NULL,
    PRIMARY KEY (entity_id, segment_id),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
);
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
);
CREATE TABLE relation_cite (
    relation_id UUID NOT NULL,
    segment_id UUID NOT NULL,
    PRIMARY KEY (relation_id, segment_id),
    FOREIGN KEY (relation_id) REFERENCES relations(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
);"""

@with_vdb(client_name="vdb_client")
@with_rdb(
    connection_name="rdb_connection",
    cursor_name="rdb_cursor",
)
async def init_ds(rdb_connection, rdb_cursor, vdb_client):
    """Initialize the data storage of the HuRAG knowledge base.

    Args:
        rdb_connection: The RDB connection object.
        rdb_cursor: The RDB cursor object.
        vdb_client: The VDB client object.

        All 3 arguments are injected by 'with_rdb' and 'with_vdb'.
    """
    # 1. Initialize rdb
    rdb_stmts = [s.strip() for s in _INIT_RSS_STATEMENTS.split(";")]
    try:
        for stmt in rdb_stmts:
            if not stmt:
                continue
            await rdb_cursor.execute(stmt)
            await rdb_connection.commit()
        logger.info("The rdb is initilized.")
    except Excption as e:
        await rdb_connection.rollback()
        logger.warning(
            f"Error while initializing the rdb, transaction rollbacked: {e}"
        )
        raise e

    # 2. Initialize vdb
    from pymilvus import DataType
    if vdb_client.has_collection("chunks"):
        vdb_client.drop_collection("chunks")
    # create chunks collection
    schema = MilvusClient.create_schema(
        enable_dynamic_field = False,
        description = "dense and sparse vectors of chunks"
    )
    schema.add_field(
        field_name="id",
        datatype=DataType.VARCHAR,
        max_length=36,
        is_primary=True,
    )
    schema.add_field(
        field_name="dense_vec",
        datatype=DataType.FLOAT_VECTOR,
        dim=1024,
    )
    schema.add_field(
        field_name="sparse_vec",
        datatype=DataType.SPARSE_FLOAT_VECTOR,
    )
    schema.add_field(
        field_name="doc_id",
        datatype=DataType.VARCHAR,
        max_length=36,
    )
    index_params = vdb_client.prepare_index_params()
    index_params.add_index(
        field_name="dense_vec",
        index_name="dense_idx",
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )
    index_params.add_index(
        field_name="sparse_vec",
        index_name="sparse_idx",
        index_type="AUTOINDEX",
        metric_type="IP"
    )
    index_params.add_index(
        field_name="doc_id",
        index_name="doc_idx"
    )
    vdb_client.create_collection(
        collection_name="chunks",
        schema=schema,
        index_params=index_params
    )
    # create kg collections
    if vdb_client.has_collection("nodes"):
        vdb_client.drop_collection("nodes")
    if vdb_client.has_collection("edges"):
        vdb_client.drop_collection("edges")
    schema = MilvusClient.create_schema(
        enable_dynamic_field = False,
        description = "dense and sparse vectors of entities"
    )
    schema.add_field(
        field_name="id",
        datatype=DataType.VARCHAR,
        max_length=36,
        is_primary=True,
    )
    schema.add_field(
        field_name="dense_vec",
        datatype=DataType.FLOAT_VECTOR,
        dim=1024,
    )
    schema.add_field(
        field_name="sparse_vec",
        datatype=DataType.SPARSE_FLOAT_VECTOR,
    )
    index_params = vdb_client.prepare_index_params()
    index_params.add_index(
        field_name="dense_vec",
        index_name="dense_idx",
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )
    index_params.add_index(
        field_name="sparse_vec",
        index_name="sparse_idx",
        index_type="AUTOINDEX",
        metric_type="IP"
    )
    vdb_client.create_collection(
        collection_name="nodes",
        schema=schema,
        index_params=index_params
    )
    schema = MilvusClient.create_schema(
        enable_dynamic_field = False,
        description = "dense and sparse vectors of relation"
    )
    schema.add_field(
        field_name="id",
        datatype=DataType.VARCHAR,
        max_length=36,
        is_primary=True,
    )
    schema.add_field(
        field_name="dense_vec",
        datatype=DataType.FLOAT_VECTOR,
        dim=1024,
    )
    schema.add_field(
        field_name="sparse_vec",
        datatype=DataType.SPARSE_FLOAT_VECTOR,
    )
    index_params = vdb_client.prepare_index_params()
    index_params.add_index(
        field_name="dense_vec",
        index_name="dense_idx",
        index_type="AUTOINDEX",
        metric_type="COSINE"
    )
    index_params.add_index(
        field_name="sparse_vec",
        index_name="sparse_idx",
        index_type="AUTOINDEX",
        metric_type="IP"
    )
    vdb_client.create_collection(
        collection_name="edges",
        schema=schema,
        index_params=index_params
    )

    return

__all__ = [
    "with_rdb",
    "with_vdb",
]

