# Vector DB API (FastAPI)

A clean, typed REST API to organize text chunks with vector embeddings and perform k-Nearest Neighbors (kNN) search. It is containerized and includes custom index implementations, concurrency controls, optional persistence, and a minimal Python SDK.

### Objective
- CRUD for Libraries → Documents → Chunks
- Build/rebuild a per-library vector index (brute_force | kd_tree | lsh)
- kNN vector search by embedding or text (embedding generated)
- Containerized service with Docker

### Technical Choices (Why this design)
- **FastAPI + Pydantic**: clear request/response typing, validation, and excellent dev UX.
- **Domain layering**: Routers (HTTP) → Services (business logic) → Repositories (storage). Keeps responsibilities separated and testable.
- **Indexes implemented in-house**: Brute Force, KD-Tree, Random Hyperplane LSH to demonstrate algorithmic understanding without external ANN libs.
- **Concurrency**: Per-library Reader-Writer lock and a simple version manager. Index builds run off-lock and swap atomically to avoid long write holds.
- **Staleness policy**: If index is stale, optionally serve from stale index or fall back to brute-force while triggering async rebuild.
- **Optional persistence**: Simple JSON snapshots for portability and easy local demos.
- **Leader–Follower (optional)**: Follower polls leader snapshot for read scaling; simple and explicit over complex consensus for this scope.

---

## How to Run

### Local (Python)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env  # edit if needed
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open docs: http://localhost:8000/docs

### Docker
```bash
docker build -t vector-db:latest .
docker run -p 8000:8000 --env-file .env vector-db:latest
```

### Docker Compose
```bash
docker compose up -d --build
```
- Service: `http://localhost:8000`
- Health: `GET /health`

---

## Quick Demo (curl)
```bash
# 1) Create a library (dim=3)
curl -s -X POST http://localhost:8000/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo","embedding_dimension":3,"default_index_type":"brute_force"}'

# 2) Get library id
LIB=$(curl -s http://localhost:8000/api/v1/libraries | python -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')

# 3) Create a document
doc=$(curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents \
  -H 'Content-Type: application/json' -d '{"title":"Doc1"}')
DOC=$(echo "$doc" | python - <<'PY'
import sys,json;print(json.loads(sys.stdin.read())["id"]) 
PY
)

# 4) Add chunks
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents/$DOC/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello world","embedding":[1,0,0]}'

curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents/$DOC/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"bonjour","use_embedding_service":true}'

# 5) Build index (choose: brute_force | kd_tree | lsh)
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/index:build \
  -H 'Content-Type: application/json' -d '{"index_type":"kd_tree"}'

# 6) Query by embedding
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[1,0,0],"k":2}'

# 7) Query by text (embedding generated)
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"hello","use_embedding_service":true,"k":2}'
```

---

## Architecture Overview
- **Routers (FastAPI)**: thin HTTP layer under `app/api/routers/`.
- **Services (business logic)**: indexing, querying, embedding, persistence, replication under `app/domain/services/`.
- **Repositories (storage)**: in-memory, thread-safe maps under `app/domain/repositories/`.
- **Indexes**: pluggable implementations under `app/domain/indexes/`.
- **Concurrency**: per-library `RWLock` (`app/domain/concurrency/`), version tracking for index freshness.

### Index Implementations (summary)
- **BruteForceIndex**
  - Build: O(n), Search: O(n·d), Space: O(n·d)
  - Accurate baseline; used for fallbacks and filtered search
- **KDTreeIndex** (L2 on normalized vectors)
  - Build: O(n log n), Search: avg O(log n) for low d, worst O(n), Space: O(n)
  - Exact for L2; suitable for low dimensions
- **RandomHyperplaneLSHIndex** (cosine)
  - Build: O(n·R), Search: O(candidates·d), Space: O(n + buckets)
  - Approximate; scalable recall/latency trade-off

### Concurrency & Consistency
- Per-library **Reader–Writer lock** allows concurrent reads; writes and index swaps are exclusive.
- **Versioning**: library data_version vs index_version; stale detection triggers async rebuild.
- **Staleness policy**: configurable via env (`VECTORDB_ALLOW_STALE_INDEX`). If disabled, queries do brute-force until fresh.

### Persistence (optional)
- JSON snapshots to `VECTORDB_PERSISTENCE_DIR`.
- Load on startup; save on shutdown when `VECTORDB_PERSISTENCE_ENABLED=true`.

### Leader–Follower (optional)
- Leader exposes `/api/v1/replication/snapshot`.
- Follower polls leader (`VECTORDB_NODE_ROLE=follower`, `VECTORDB_LEADER_URL=...`), replaces local repos, and rebuilds indexes.

---

## Configuration
Copy `env.example` to `.env` and adjust:
- **App/Server**: `VECTORDB_APP_NAME`, `VECTORDB_ENVIRONMENT`, `VECTORDB_HOST`, `VECTORDB_PORT`, `VECTORDB_DEBUG`
- **Logging**: `VECTORDB_LOG_LEVEL`, `VECTORDB_LOG_FORMAT`
- **Vector DB**: `VECTORDB_DEFAULT_INDEX_TYPE`, `VECTORDB_ALLOW_STALE_INDEX`, `VECTORDB_MAX_EMBEDDING_DIMENSION`
- **Embeddings**: `VECTORDB_EMBEDDING_PROVIDER` (cohere|none), `VECTORDB_COHERE_API_KEY`, `VECTORDB_COHERE_MODEL`
- **Persistence**: `VECTORDB_PERSISTENCE_ENABLED`, `VECTORDB_PERSISTENCE_DIR`
- **Cluster**: `VECTORDB_NODE_ROLE` (leader|follower), `VECTORDB_LEADER_URL`, `VECTORDB_REPLICATION_INTERVAL_SECONDS`

---

## Testing
```bash
pytest -q
```

---

## Python SDK (optional)
```python
from sdk.client import VectorDBClient

client = VectorDBClient("http://localhost:8000")
lib = client.create_library(name="demo", embedding_dimension=3)
doc = client.create_document(lib["id"], title="Doc1")
client.create_chunk(lib["id"], doc["id"], text="hello world", embedding=[1,0,0])
client.build_index(lib["id"], index_type="kd_tree")
print(client.query(lib["id"], k=1, query_embedding=[1,0,0]))
client.close()
```

---

## Limitations & Future Work
- JSON persistence is simple; a DB-backed store could be added behind repository interfaces.
- KDTree degrades with high dimensions; LSH or brute-force recommended there.
- Replication is polling-based; production systems would add durability/consensus.
