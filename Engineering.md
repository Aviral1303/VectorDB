# Engineering Plan: Vector DB Backend (FastAPI + Pydantic)

## 1) Purpose and Scope
- Build a REST API that lets users:
  - Create/read/update/delete (CRUD) libraries.
  - CRUD documents and chunks within a library.
  - Index the contents of a library with multiple index algorithms.
  - Perform k-Nearest Neighbors (kNN) vector search over a selected library.
- Containerize the service with Docker.
- Keep code clean, typed, SOLID, testable, and documented.

## 2) Non-Goals (for baseline)
- No document processing/ingestion pipeline (OCR/chunking). We will provide manual chunks.
- No external vector DBs or search libs (FAISS/Chroma/Pinecone). We implement indexes ourselves.
- Advanced distributed features (leader-follower) optional extra.

## 3) Constraints & Tech
- Python 3.11+
- FastAPI for API, Pydantic for models & validation
- Uvicorn for ASGI server
- Numpy allowed for trig/math but not required for baseline
- No external ANN libraries
- Use Cohere Embeddings API for demo data generation (keys provided)

## 4) Glossary
- Chunk: atomic text + embedding + metadata unit.
- Document: collection of chunks + document-level metadata.
- Library: collection of documents (and thus chunks) + library-level metadata.
- Index: data structure to accelerate kNN queries.

## 5) High-Level Architecture
- API (FastAPI Routers): HTTP endpoints only; no business logic.
- Services (Domain Logic): LibraryService, DocumentService, ChunkService, IndexService, QueryService, EmbeddingService, PersistenceService.
- Repositories (Storage): In-memory repositories (with optional JSON persistence extension). Thread-safe.
- Indexes (Pluggable): BruteForceIndex, KDTreeIndex, RandomHyperplaneLSHIndex.
- Concurrency Control: Reader-Writer locks per library; background index builds with versioning.
- Config: Pydantic BaseSettings (env-driven). Dependency injection via provider functions.

## 6) Data Modeling (Pydantic)
Fixed schemas to simplify validation and CRUD. All IDs are UUIDv4 strings.

- Common fields
  - `id: str` (UUID)
  - `created_at: datetime`
  - `updated_at: datetime`

- Chunk
  - `id`, `library_id`, `document_id`
  - `text: str` (raw text)
  - `embedding: list[float]` (same dimension within a library)
  - `metadata: ChunkMetadata`

- ChunkMetadata
  - `source: str | None`
  - `tags: list[str] = []`
  - `author: str | None`
  - `created_by: str | None`

- Document
  - `id`, `library_id`
  - `title: str`
  - `description: str | None`
  - `metadata: DocumentMetadata`

- DocumentMetadata
  - `source: str | None`
  - `tags: list[str] = []`
  - `author: str | None`

- Library
  - `id`
  - `name: str`
  - `description: str | None`
  - `embedding_dimension: int`
  - `default_index_type: IndexType = brute_force | kd_tree | lsh`
  - `metadata: LibraryMetadata`

- LibraryMetadata
  - `owner: str | None`
  - `tags: list[str] = []`

- Request/Response DTOs
  - Create/Update models separate from read models to control which fields are client-provided.
  - Response models avoid internal fields where appropriate.

Validation rules
- Chunk embedding length must match `library.embedding_dimension`.
- All IDs must exist and be associated correctly (chunk.library_id matches path library).
- Names non-empty; tags limited to reasonable length; strings length-checked.

## 7) Repositories (In-Memory, Optional Persistence)
- `LibraryRepository`
  - Store: `dict[str, Library]`
  - Methods: `create`, `get`, `list`, `update`, `delete`
- `DocumentRepository`
  - Store: `dict[str, Document]` and index by `library_id`
  - Methods: `create`, `get`, `list_by_library`, `update`, `delete`, `list_ids_by_library`
- `ChunkRepository`
  - Store: `dict[str, Chunk]`, secondary: `dict[str, set[str]]` mapping library_id -> chunk_ids
  - Methods: `create`, `get`, `list_by_library`, `list_by_document`, `update`, `delete`, `bulk_get`

Thread-safety
- Use a global registry for libraries and per-library locks.
- Global lock only for library-level operations (create/delete libraries). Per-library read/write locks protect documents/chunks/indexes.

Optional Persistence (Extra)
- JSON snapshot per library: `data/` directory:
  - `libraries.json`
  - `libraries/{library_id}/documents.json`
  - `libraries/{library_id}/chunks.json`
  - `libraries/{library_id}/index_{type}.bin` (if needed)
- Atomic writes: write to temp file then `os.replace`.
- Startup: load snapshots; missing files => start empty.

## 8) Index Interface and Implementations
Interface: `VectorIndex`
- `build(vectors: list[list[float]], ids: list[str]) -> None`
- `add(vector: list[float], id: str) -> None`
- `remove(id: str) -> None`
- `update(id: str, new_vector: list[float]) -> None`
- `search(query: list[float], k: int) -> list[tuple[str, float]]` (returns (id, similarity or distance))
- `size() -> int`

Distance/Similarity
- Use cosine similarity by default; allow L2 distance if index requires. Normalize vectors once on insert for cosine optimization.

Implementations
1) BruteForceIndex (Flat)
- Storage: arrays of vectors and parallel list of ids (plus map id->pos)
- Search: linear scan computing cosine similarity
- Time: build O(n); add O(1); search O(n*d)
- Space: O(n*d)
- Pros: simple, accurate, robust; baseline
- Cons: slow for large n

2) KDTreeIndex (Euclidean)
- Balanced KD-Tree built by median split
- Search: best-first with pruning; exact kNN for L2
- Time: build O(n log n); search avg O(log n) for low d (degrades with higher d)
- Space: O(n)
- Limits: works best for d <= ~20–30; we will document that cosine is approximated by L2 on normalized vectors

3) RandomHyperplaneLSHIndex (for Cosine)
- R random hyperplanes (random vectors); H hash tables (bands) or one table with binary codes
- Hash: sign of dot product per hyperplane -> bitstring key
- Bucketed candidates then linear scan in bucket
- Time: build O(n * R); search O(candidates * d)
- Space: O(n + buckets)
- Pros: scalable, sublinear lookup approx
- Cons: approximate, tunable parameters (R, bands)

Index Selection
- Per-library `default_index_type` with configurable params.
- Ability to rebuild index on demand.

## 9) Concurrency & Consistency Design
- Per-library Reader-Writer Lock (RWLock)
  - Reads (list/get/search) acquire read lock.
  - Mutations (create/update/delete chunk/doc, rebuild index) acquire write lock.
- Versioning
  - Library has `data_version` incremented on write.
  - Index stores `built_version`.
  - Queries verify `built_version == data_version`; if not, consult IndexService policy:
    - Either serve from stale index and also return `stale_index=true`, or perform on-the-fly linear scan fallback. Default: serve with stale index if configured; expose endpoint to rebuild.
- Background builds
  - Rebuild index in a background task to avoid blocking writes.
  - Use copy-on-write: build a new index instance, then swap under write lock.

## 10) Services (Business Logic)
- `LibraryService`
  - Create library (validate name, dimension, default index type)
  - Update/delete library (cascade deletes for docs/chunks)
  - Get/list libraries
- `DocumentService`
  - Create/update/delete documents within library
  - Ensure doc->library association
- `ChunkService`
  - Create chunks (validate embedding dim, normalize if cosine)
  - Update text/metadata/embedding; delete chunks
  - Bulk operations (optional)
- `IndexService`
  - Build/rebuild selected index for library
  - Increment version, maintain index registry per library
  - Add/remove/update chunk vectors in index incrementally
- `QueryService`
  - kNN search over selected library index; fallback to brute-force if index missing or stale by policy
  - Optional metadata filtering pre/post candidate selection
- `EmbeddingService`
  - Generate embeddings via Cohere for demo (or pass-through if embedding provided)
  - Rate-limit/backoff/simple cache (in-memory)
- `PersistenceService` (Extra)
  - Snapshot repositories to disk, load on startup, atomic writes

## 11) API Layer (Routers)
Base URL: `/api/v1`

Libraries
- `POST /libraries` create
- `GET /libraries` list
- `GET /libraries/{library_id}` get
- `PATCH /libraries/{library_id}` update
- `DELETE /libraries/{library_id}` delete
- `POST /libraries/{library_id}/index:build` build/rebuild index (body: index type + params)
- `GET /libraries/{library_id}/index:status` show index type, size, built_version vs data_version

Documents
- `POST /libraries/{library_id}/documents` create
- `GET /libraries/{library_id}/documents` list
- `GET /libraries/{library_id}/documents/{document_id}` get
- `PATCH /libraries/{library_id}/documents/{document_id}` update
- `DELETE /libraries/{library_id}/documents/{document_id}` delete

Chunks
- `POST /libraries/{library_id}/documents/{document_id}/chunks` create (embedding optional if `text` + `use_embedding_service=true`)
- `GET /libraries/{library_id}/chunks` list (filters: document_id, tags, author, created_after/before)
- `GET /libraries/{library_id}/chunks/{chunk_id}` get
- `PATCH /libraries/{library_id}/chunks/{chunk_id}` update
- `DELETE /libraries/{library_id}/chunks/{chunk_id}` delete

Queries
- `POST /libraries/{library_id}/query` body:
  - `query_embedding` or `query_text` (+ flag to use embedding service)
  - `k: int`
  - `filter: optional` (metadata filters)
  - `use_fallback_if_stale: bool = true`
  - response: list of `{chunk_id, score, text, document_id, metadata}`

Error Handling
- Use FastAPI HTTPException with `fastapi.status` codes
- 400 for validation; 404 for not found; 409 for conflicts; 422 for semantically invalid

## 12) Filtering (Extra Points)
- Filter schema
  - `tags_any: list[str] | None`
  - `tags_all: list[str] | None`
  - `author_in: list[str] | None`
  - `created_at_from: datetime | None`
  - `created_at_to: datetime | None`
  - `text_contains: str | None` (case-insensitive)
- Pre-filter candidate set (for brute-force) or post-filter results after index search
- Combine with AND semantics across fields

## 13) Configuration
- `Settings` via Pydantic BaseSettings
  - `APP_ENV`, `LOG_LEVEL`
  - `EMBEDDING_PROVIDER` (cohere|none)
  - `COHERE_API_KEY`
  - `DEFAULT_INDEX_TYPE`
  - `PERSISTENCE_DIR` (optional)
  - `ALLOW_STALE_INDEX` (bool)

## 14) Directory Structure
```
vector-db/
  app/
    api/
      routers/
        libraries.py
        documents.py
        chunks.py
        query.py
        index.py
      deps.py
    core/
      settings.py
      logging.py
      errors.py
    domain/
      models/
        chunk.py
        document.py
        library.py
        filters.py
        common.py
      services/
        library_service.py
        document_service.py
        chunk_service.py
        index_service.py
        query_service.py
        embedding_service.py
        persistence_service.py
      repositories/
        libraries.py
        documents.py
        chunks.py
      indexes/
        base.py
        brute_force.py
        kd_tree.py
        lsh.py
      concurrency/
        rwlock.py
        versioning.py
    main.py
  tests/
    unit/
    integration/
  requirements.txt
  Dockerfile
  README.md
  Engineering.md
  Makefile (optional)
```

## 15) Index Algorithms: Details & Complexity
- Cosine Similarity
  - Normalize vectors to unit norm: similarity = dot(u, v)
  - For KDTree (L2), if vectors normalized, ordering by L2 is monotonic with cosine

- BruteForceIndex
  - Build: O(n)
  - Add/Remove/Update: O(1) amortized
  - Search: O(n * d)
  - Space: O(n * d)

- KDTreeIndex
  - Build: O(n log n) using median-of-medians or sort per split
  - Search: average O(log n) for low d; worst-case near O(n) in high d
  - Space: O(n)
  - Exact for L2; approximate cosine via normalized vectors

- RandomHyperplaneLSHIndex
  - Parameters: R hyperplanes (e.g., 16–64), optional multi-table for recall
  - Build: O(n * R)
  - Search: O(candidates * d); expected sublinear
  - Space: O(n + buckets), overhead for hash tables

Rationales
- BruteForce ensures correctness baseline.
- KDTree provides exact fast queries in low dimensions.
- LSH adds scalable approximate cosine for higher dimensions.

## 16) Concurrency: RWLock & Background Build
- Implement `RWLock` with `threading` primitives (readers count, condition variable) or `asyncio` equivalents; prefer `threading` since FastAPI may run in threads under Uvicorn workers.
- Per-library lock stored in a registry: `library_id -> RWLock`.
- For index rebuild:
  1. Acquire read lock to snapshot chunk vectors.
  2. Release read lock; build new index off-lock.
  3. Acquire write lock; swap index; update `built_version = data_version`.
  4. Release lock.
- For per-chunk add/update/remove, acquire write lock briefly to update index incrementally.

## 17) Error Handling Strategy
- Consistent error payloads: `{error: {code, message, details?}}`
- Map domain exceptions to HTTP codes in a central exception handler.
- Validate all inputs via Pydantic DTOs; add custom validators for embedding dims.

## 18) Logging & Observability
- Structured logs (JSON optional). Include request_id, library_id, endpoint.
- Log index builds (start, end, duration, counts).
- Timing decorators for search operations.

## 19) Testing Plan
Unit Tests
- Models: validation, embedding dim enforcement
- Repositories: CRUD behavior, thread-safety basic checks
- Indexes: build/add/update/remove/search correctness; LSH recall sanity
- Services: versioning, index swap logic, filter semantics

Integration Tests
- API happy paths for all endpoints
- Error cases (404, 400, 409)
- Concurrency: simulate concurrent reads/writes and index rebuilds

Performance/Smoke
- Benchmark kNN across index types for sample sizes (1k, 10k)

## 20) Dockerization
- `Dockerfile` (multi-stage optional)
  - Base: python:3.11-slim
  - Install system deps (if any), install `requirements.txt`
  - Copy app; set `PYTHONUNBUFFERED=1`
  - `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- Expose 8000
- Environment variables for settings

## 21) Configuration & Secrets
- Use env vars; never hardcode keys.
- For local dev, `.env` (not committed) or export in shell.

## 22) Step-by-Step Execution Plan
Milestone 0: Scaffolding (0.5 day)
1. Initialize repo structure, `requirements.txt`, basic `main.py` with health endpoint.
2. Implement `Settings` and logging setup.
3. Add Makefile targets: run, lint (optional), test.

Milestone 1: Domain Models & Repos (0.5 day)
1. Implement Pydantic models: common, library, document, chunk, filters.
2. Implement repositories with in-memory stores and validation hooks.
3. Implement RWLock and registry.
4. Unit tests for models and repos.

Milestone 2: Indexes (1 day)
1. Define `VectorIndex` interface.
2. Implement `BruteForceIndex` with cosine.
3. Implement `KDTreeIndex` (L2) with normalized vectors.
4. Implement `RandomHyperplaneLSHIndex` for cosine.
5. Unit tests for indexes (correctness & basic performance).

Milestone 3: Services (0.5 day)
1. LibraryService, DocumentService, ChunkService with validation and lock usage.
2. IndexService: build/swap/versioning/incremental updates.
3. QueryService: kNN + filters; stale policy.
4. Unit tests for services.

Milestone 4: API Layer (0.5 day)
1. Implement routers for libraries, documents, chunks, index, query.
2. Dependency injection wiring.
3. Error handlers and response models.
4. Integration tests for endpoints.

Milestone 5: Embeddings & Demo (0.25 day)
1. EmbeddingService with Cohere client and simple retry.
2. Endpoint paths accept `text` or `embedding`.
3. Seed script or demo notebook to populate sample data.

Milestone 6: Docker & Docs (0.25 day)
1. Dockerfile, docker run instructions.
2. README with how-to-run, design summary.
3. Final polishing pass.

Buffer & Extras (as time allows)
- Persistence snapshots to disk.
- Metadata filtering endpoints and service support.
- Optional SDK client (thin httpx wrapper) and examples.

## 23) Acceptance Criteria Checklist
- Libraries CRUD functional with validation.
- Documents and Chunks CRUD functional with validation and associations.
- Indexes: build, status, and search end-to-end working for at least 2 algorithms (Brute, KDTree). LSH optional.
- Concurrency: No data races; background builds do not corrupt state.
- Tests: Unit + integration passing locally.
- Docker image builds and runs; API reachable on 0.0.0.0:8000.
- README explains setup, running, API usage, and design.

## 24) API Schemas (Representative)
- Create Library Request
```json
{
  "name": "my-lib",
  "description": "demo",
  "embedding_dimension": 384,
  "default_index_type": "brute_force",
  "metadata": {"owner": "alice", "tags": ["demo"]}
}
```
- Create Chunk Request
```json
{
  "text": "hello world",
  "embedding": [0.1, 0.2, ...],
  "metadata": {"source": "manual", "tags": ["greeting"]}
}
```
- Query Request
```json
{
  "query_text": "greeting",
  "k": 5,
  "filter": {"tags_any": ["greeting"]},
  "use_fallback_if_stale": true
}
```

## 25) Manual Test Script (Curl)
- Create library
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"test","embedding_dimension":8,"default_index_type":"brute_force"}'
```
- Add document
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries/{lib}/documents \
  -H 'Content-Type: application/json' \
  -d '{"title":"Doc 1"}'
```
- Add chunk (embedding provided)
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries/{lib}/documents/{doc}/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello","embedding":[0.1,0.0,0.0,0.0,0.0,0.0,0.0,0.0]}'
```
- Build index
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries/{lib}/index:build \
  -H 'Content-Type: application/json' \
  -d '{"index_type":"brute_force"}'
```
- Query
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries/{lib}/query \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[0.1,0,0,0,0,0,0,0],"k":3}'
```

## 26) Risks & Mitigations
- High dimensionality hurts KDTree: document limitations; suggest LSH or brute-force.
- Cohere rate limits: cache results, allow client-provided embeddings.
- Concurrency bugs: keep lock scopes minimal; comprehensive tests.
- Persistence consistency: atomic file replace and version markers.

## 27) Future Work (Extras)
- Disk-backed storage (sqlite or parquet) while maintaining repository interface.
- Leader-follower architecture: leader handles writes and index builds; followers serve reads; replication via WAL-like change log.
- Python SDK client using `httpx` with retry and typed models.
- Metrics (Prometheus) and tracing (OpenTelemetry).
