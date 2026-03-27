# Copilot Instructions for HuRAG

## Project Overview

HuRAG is a Temporal-Hierarchical GraphRAG (TH-GraphRAG) application designed for legal and regulatory knowledge bases. It supports both structured text documents and multimodal source files, and now covers document ingestion, attachment ingestion, metadata maintenance, vector retrieval, graph retrieval, API serving, and a NiceGUI-based WebUI.

It features a dual-service architecture:
-   **API Server (`hurag-server`):** FastAPI-based backend for retrieval, document/tool APIs, and LLM interaction.
-   **WebUI (`hurag-webui`):** NiceGUI-based frontend for interactive use.

## Build and Run

This project uses `uv` for dependency management and execution.

*   **Install dependencies:**
    ```bash
    uv sync
    ```
*   **Run Services:**
    *   **API Server:** `uv run hurag-server` (Host/Port configured in `hurag.yaml` -> `api`)
    *   **WebUI:** `uv run hurag-webui`
*   **CLI Tools:**
    *   **Knowledge Base Management:** `uv run hurag` (Subcommands: `init`, `info`, `list`, `store`)
    *   **Corpus Preparation:** `uv run corpus` (`convert`, `markup`, `split`)
    *   **Knowledge Graph:** `uv run kgraph`
*   **Linting:**
    *   Run static type checks: `uv run pyright`

### Current ingestion workflow

-   Use `uv run corpus convert` to convert source files to Markdown or normalize text encodings when needed.
-   Use `uv run corpus markup` to generate or refresh `corpus.json`. The markup file now uses a three-part workflow:
    -   `insert`: documents to ingest
    -   `update`: metadata updates for existing documents
    -   `delete`: documents or attachments to remove
-   Use `uv run corpus split` for text-style corpus files (`.regu`, `.text`, `.markdown`) before ingestion.
-   Use `uv run hurag store <corpus_dir>` to execute ingestion and maintenance:
    -   ingest normal text documents into the vector store
    -   ingest multimodal documents by extracting content with the multimodal LLM client
    -   ingest document attachments as stored multimodal content
    -   apply metadata updates and deletions declared in `corpus.json`

## Architecture & Data Access

### Data Support System (DSS)
The `src/hurag/dss` module handles all data access. **Do not access databases directly; use the provided wrappers.**

*   **Relational (`dss.rss`):** Wraps `aiomysql` for MariaDB.
    *   **Injection:** Use the `@with_rdb` decorator to inject `connection` and `cursor`.
    *   **Usage:**
        ```python
        @with_rdb
        async def my_func(conn, cur):
            await cur.execute("SELECT * FROM ...")
        ```
*   **Vector (`dss.vss`):** Wraps `pymilvus` for Milvus.
    *   **Injection:** Use the `@with_vdb` decorator to inject the `client`.
    *   **Usage:**
        ```python
        @with_vdb(client_arg_name="cli")
        async def my_func(cli):
            await cli.search(...)
        ```
*   **Graph (`dss.gss`):** Orchestrates hybrid graph storage (entities/relations in MariaDB, embeddings in Milvus).
*   **File Storage (`dss.fss`):** Persists extracted content for multimodal documents and attachments. Use it for stored file content access rather than ad-hoc filesystem reads.

### Knowledge Base Manager (`kbman`)
High-level logic for managing the knowledge base resides in `src/hurag/kbman`. Use this module for corpus preparation and maintenance operations such as markup generation, document deletion, attachment deletion, metadata updates, or statistics.

### Business Logic Layers
*   **Document Ingestion (`knowledge_base.py`, `indexer.py`):** Handles document loading, indexing, vectorization, and persistence for standard text documents, multimodal documents, and attachments.
*   **Retrieval (`retrievers.py`):** Provides retrieval entry points including `vector_search(...)` and `graph_search(...)`.
*   **Graph Logic (`knowledge_graph.py`):** Contains algorithms for entity extraction, normalization, and community detection (Leiden).
*   **Server Tool APIs (`hurag_server/api/v1/tools.py`):** Exposes list/read/search endpoints for documents, attachments, multimodal content, vector search, and graph search.

### Document model notes

-   A `Document` may be a normal text document or a multimodal document.
-   Multimodal documents are represented in the data model by a title prefixed with `*`; they do not carry split text segments for vector indexing.
-   A document may also have `attachments`, which are treated as stored multimodal file content associated with the parent document.
-   Text documents support segment/chunk indexing, vector retrieval, and graph retrieval.
-   Multimodal documents and attachments support content extraction and direct reading APIs; the server docs explicitly note that multimodal documents are not used for vector paragraph localization or graph search.

## Configuration

*   **`hurag.yaml`:** Main application configuration (DB connections, retrieval parameters, model tags).
*   **`.env`:** Environment variables for secrets and model-specific configs.
    *   **Model Mapping:** `hurag.yaml` defines model *tags* (e.g., `generation: DEEPSEEK`). The code looks up environment variables based on these tags (e.g., `DEEPSEEK_BASE_URL`, `DEEPSEEK_API_KEY`).
    *   **Multimodal LLM:** multimodal extraction uses the `llm.multimodal` model tag and corresponding environment variables for the configured provider.

## API Surface Highlights

The FastAPI server includes the existing info/chat/retrieval routes plus a tool-oriented API set under `/v1/tools` for application and agent integrations. Important current endpoints include:

-   `GET /v1/tools/list_documents`: list visible documents with attachment metadata
-   `GET /v1/tools/read_attachment`: read extracted content of a stored attachment
-   `GET /v1/tools/read_multimodal_document`: read extracted content of a stored multimodal document
-   `POST /v1/tools/vector_search`: run semantic/vector retrieval over indexed text knowledge
-   `POST /v1/tools/graph_search`: run graph-aware retrieval over entities, relations, and linked knowledge

## Coding Conventions

*   **Async/Await:** All Database and IO operations are asynchronous. Ensure new functions utilizing `dss` are `async`.
*   **Type Hinting:** Strict type hinting is required to satisfy `pyright`.
    *   Use `TYPE_CHECKING` blocks for circular imports.
    *   Explicitly handle `None` types.
*   **WebUI Isolation:** NiceGUI events share the same worker. Always check `ui.context.client` in event handlers to ensure data isolation between users.
*   **Logging:** Use the project's logger (`from .. import logger`).
*   **Data access boundaries:** Go through `dss` wrappers and `kbman` helpers instead of reaching into MariaDB, Milvus, or file storage directly.
