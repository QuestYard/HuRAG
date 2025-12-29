# HuRAG Data Storage Schemas

## SQL Storage

HuRAG using MariaDB as the SQL storage backend, and graph data is also stored in the SQL database.

Elements of documents and knowledge graphs, such as documents, segments, chunks, entities, relations, and their associations, are stored in the SQL database.

### Document

Text and tabular documents are stored in the SQL database, including their metadata, segments, chunks, and domain classifications.

#### documents

Table 'documents' stores the metadata of documents.

| Field      | Type         | Key | NUL | Description                                          |
|:----------:|:------------:|:---:|:---:|------------------------------------------------------|
| id         | UUID         | PK  | NO  | Document ID, UUIDv7                                  |
| title      | VARCHAR(100) | UNI | NO  | Document title                                       |
| sn         | VARCHAR(50)  |     | YES | Document serial number                               |
| date       | DATE         |     | NO  | Document publication date                            |
| valid_from | DATE         | IDX | NO  | Document effective date                              |
| valid_to   | DATE         | IDX | YES | Document expiration date, NULL means no expiration   |
| replaces   | VARCHAR(100) |     | YES | title of the previous version, NULL means none       |
| pub_path   | VARCHAR(100) | IDX | NO  | Organization path that published the document        |
| localizes  | VARCHAR(100) |     | YES | title of the parent document, NULL means none        |
| authors    | VARCHAR(100) |     | YES | Original author, NULL means none                     |
| kg_built   | BOOLEAN      |     | NO  | Whether the knowledge graph has been built           |

#### segments

Table 'segments' stores the segments of documents.

| Field       | Type        | Key | NUL | Description                                          |
|:-----------:|:-----------:|:---:|:---:|------------------------------------------------------|
| id          | UUID        | PK  | NO  | Segment ID, UUIDv7                                   |
| document_id | UUID        | FK  | NO  | Document ID, fk to documents(id) , cascade on delete |
| seq_no      | INT         |     | NO  | Segment sequence number, starting from 0             |

#### chunks

Table 'chunks' stores the chunks of segments.

| Field      | Type         | Key | NUL | Description                                          |
|:----------:|:------------:|:---:|:---:|------------------------------------------------------|
| id         | UUID         | PK  | NO  | Chunk ID, UUIDv7                                     |
| segment_id | UUID         | FK  | NO  | Segment ID, fK to segments(id), cascade on delete    |
| seq_no     | INT          |     | NO  | Chunk sequence number, starting from 0               |
| text       | VARCHAR(1000)|     | NO  | Chunk text                                           |

### Knowledge Graph

Knowledge graph data, including entities, relations, and their associations with documents, segments, and chunks, are stored in the SQL database.

#### entities

Table 'entities' stores the entities in the knowledge graph. Entity names are not unique, allowing multiple entities with the same name but different meanings to coexist.

| Field       | Type         | Key | NUL | Description                                      |
|:-----------:|:------------:|:---:|:---:|--------------------------------------------------|
| id          | UUID         | PK  | NO  | Entity ID, UUIDv7                                |
| name        | VARCHAR(100) |     | NO  | Entity name                                      |
| type        | VARCHAR(50)  |     | NO  | Entity type, e.g., Organization, Procedure, etc. |
| description | VARCHAR(500) |     | YES | Entity description, NULL means none              |

#### entity_cite

Each entity can be cited by multiple segments, and each segment can cite multiple entities, forming a many-to-many relationship.

| Field      | Type | Key | NUL | Description                                          |
|:----------:|:----:|:---:|:---:|------------------------------------------------------|
| entity_id  | UUID | FK  | NO  | Entity ID, fk to entities(id), cascade on delete     |
| segment_id | UUID | FK  | NO  | Segment ID, fk to segments(id), cascade on delete    |

#### relations

Table 'relations' stores the relations in the knowledge graph.

- Relations are grouped by (source, target) pairs, allowing multiple relations with different types between the same source and target entities.
- Synonym relations will be merged and their strength summed to keep distinct, valid facts.
- (source, target, type) triplet is unique, each triplet represents a unique relation with a unique ID, description, and strength.

| Field       | Type         | Key | NUL | Description                                             |
|:-----------:|:------------:|:---:|:---:|---------------------------------------------------------|
| id          | UUID         | PK  | NO  | Relation ID, UUIDv7                                     |
| source_id   | UUID         | FK  | NO  | Source Entity ID, fk to entities(id), cascade on delete |
| target_id   | UUID         | FK  | NO  | Target Entity ID, fk to entities(id), cascade on delete |
| type        | VARCHAR(50)  |     | NO  | Relation type, e.g., "regulated_by", "obeys", etc.      |
| description | VARCHAR(500) |     | YES | Relation description, NULL means none                   |
| strength    | FLOAT        |     | NO  | Relation strength, non-negative                         |

Additional Indexes:

- Unique index on (source_id, target_id, type)

#### relation_cite

Each relation can be cited by multiple segments, and each segment can cite multiple relations, forming a many-to-many relationship.

| Field      | Type | Key | NUL | Description                                          |
|:----------:|:----:|:---:|:---:|------------------------------------------------------|
| relation_id| UUID | FK  | NO  | Relation ID, fk to relations(id), cascade on delete  |
| segment_id | UUID | FK  | NO  | Segment ID, fk to segments(id), cascade on delete    |

#### communities

Table 'communities' stores the community assignments of entities, used for graph visualization and analysis.

| Field    | Type          | Key | NUL | Description       |
|:--------:|:-------------:|:---:|:---:|-------------------|
| id       | INT           | PK  | NO  | Community ID      |
| summary  | VARCHAR(1000) |     | NO  | Community summary |

#### community_entity

Each community can contain multiple entities, each entity can belong to just one community, forming a one-to-many relationship.

| Field        | Type | Key | NUL | Description                                             |
|:------------:|:----:|:---:|:---:|---------------------------------------------------------|
| community_id | INT  | FK  | NO  | Community ID, fk to communities(id), cascade on delete  |
| entity_id    | UUID | FK  | NO  | Entity ID, fk to entities(id), cascade on delete        |

## Vector Storage

HuRAG uses Milvus as the vector storage backend, storing the vector representations of chunks, entities and relations.

### Chunks

Collection 'chunks' stores the vector representations of chunks, with each chunk represented as a 1024-dimensional vector and a lexical sparse vector.

| Field       | Type               | Key | NUL | Description                                    |
|:-----------:|:------------------:|:---:|:---:|------------------------------------------------|
| id          | VARCHAR(36)        | PK  | NO  | Chunk ID, UUIDv7                               |
| dense_vec   | FLOAT_VECTOR       | VEC | NO  | Chunk vector representation, 1024-dimensional  |
| sparse_vec  | SPARSE_FLOAT_VECTOR| VEC | NO  | Chunk sparse vector representation             |
| doc_id      | VARCHAR(36)        |     | NO  | Document ID, UUIDv7                            |

### Nodes

Collection 'nodes' stores the vector representations of entities, with each entity represented as a 1024-dimensional vector and a lexical sparse vector.

The vectors are generated by combining the entity name, type, and description.

| Field       | Type               | Key | NUL | Description                                    |
|:-----------:|:------------------:|:---:|:---:|------------------------------------------------|
| id          | VARCHAR(36)        | PK  | NO  | Entity ID, UUIDv7                              |
| dense_vec   | FLOAT_VECTOR       | VEC | NO  | Entity vector representation, 1024-dimensional |
| sparse_vec  | SPARSE_FLOAT_VECTOR| VEC | NO  | Entity sparse vector representation            |

### Edges

Collection 'edges' stores the vector representations of relations, with each relation represented as a 1024-dimensional vector and a lexical sparse vector.

The vectors are generated by combining the source entity name, target entity name, relation type, and description.

| Field       | Type               | Key | NUL | Description                                     |
|:-----------:|:------------------:|:---:|:---:|-------------------------------------------------|
| id          | VARCHAR(36)        | PK  | NO  | Relation ID, UUIDv7                             |
| dense_vec   | FLOAT_VECTOR       | VEC | NO  | Relation vector representation, 1024-dimensional|
| sparse_vec  | SPARSE_FLOAT_VECTOR| VEC | NO  | Relation sparse vector representation           |
