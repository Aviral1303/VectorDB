# End-to-End Video Script (Read-Aloud)

Scene 1 — Opening (10–15s)
Say: “Hi, I’m going to demo a clean, typed Vector Database API I built with Python, FastAPI, and Pydantic. It indexes and queries text chunks represented as vector embeddings. The data model is simple: a Library contains Documents, and Documents contain Chunks. A Library fixes the embedding dimension and default index type. The API supports k-nearest neighbors search with three custom indexes I implemented from scratch: Brute Force for exact correctness, KD-Tree for exact efficiency in low dimensions, and Random Hyperplane LSH for scalable approximate cosine similarity. The architecture emphasizes separation of concerns, thread-safety with reader–writer locks, correctness via versioning and index rebuilds, and ease of deployment with Docker, plus leader–follower replication and JSON persistence.”

Scene 2 — Architecture Overview (30–40s)
Say: “The codebase separates HTTP from business logic and storage. FastAPI routers are thin. Services implement logic for libraries, documents, chunks, indexing, queries, embeddings, persistence, and replication. Repositories are thread-safe in-memory stores with RLocks. Concurrency is handled by per-library reader–writer locks and a VersionManager that tracks data versus index versions. Writes increment the data version; the index service rebuilds in the background and swaps atomically under a short write lock. The query service can serve quickly from an index or fall back to brute-force when filters are present or when stale indexes are not allowed.”

Scene 3 — Algorithms (45–60s)
Say: “Brute Force uses cosine similarity on normalized vectors. Cosine is just a dot product after normalization, so it’s exact and simple: build time is linear, and search is O(n times d). KD-Tree builds a balanced tree by splitting dimensions at medians and searches best-first; it’s exact for L2 distance and efficient in lower dimensions. Because we normalize vectors, L2 distance order aligns with cosine similarity using the relation similarity equals one minus squared distance over two. Random Hyperplane LSH generates random hyperplanes, hashes vectors to bitstrings by the sign of dot products, and searches within matching buckets; it’s approximate but sublinear in practice and falls back to a scan if the bucket is empty.”

Scene 4 — Single-Node Demo Setup (10s)
Say: “I’ll start a single-node server and run a quick end-to-end flow.”
Run:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
This starts the FastAPI server locally on port 8000.

Say: “The OpenAPI docs are at http://localhost:8000/docs.”

Scene 5 — Create Library, Document, and Chunks (40–50s)
Say: “I’ll create a library with embedding dimension three, add a document, then add two chunks: one with a provided embedding, the other using the embedding service. The embedding service uses Cohere if configured or a deterministic local fallback otherwise.”
Run:
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo","embedding_dimension":3,"default_index_type":"brute_force"}' | jq .

LIB=$(curl -s http://localhost:8000/api/v1/libraries | python -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')

curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents \
  -H 'Content-Type: application/json' \
  -d '{"title":"Doc1"}' | jq .
DOC=$(curl -s http://localhost:8000/api/v1/libraries/$LIB/documents | python -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')

curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents/$DOC/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello world","embedding":[1,0,0]}' | jq .

curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents/$DOC/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"bonjour","use_embedding_service":true}' | jq .
```
- Creates a new library named “demo” with 3-dim embeddings and brute-force index.
- Stores the created library id in LIB for reuse.
- Creates a document titled “Doc1” inside the library.
- Stores the created document id in DOC for reuse.
- Adds a chunk with a provided embedding [1,0,0].
- Adds a chunk whose embedding is generated from text via the embedding service.

Scene 6 — Build Index and Query (40–50s)
Say: “I’ll build a KD-Tree index and query by embedding and by text. The index status shows the type, size, and whether the index is stale compared to the data version.”
Run:
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/index:build \
  -H 'Content-Type: application/json' \
  -d '{"index_type":"kd_tree"}' | jq .

curl -s http://localhost:8000/api/v1/libraries/$LIB/index:status | jq .

curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[1,0,0],"k":2}' | jq .

curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"hello","use_embedding_service":true,"k":2}' | jq .
```
- Builds a KD-Tree index for the current library in the background.
- Shows the index status including type, size, and staleness.
- Queries the top-2 nearest chunks using an explicit embedding [1,0,0].
- Queries the top-2 nearest chunks using text “hello” with on-the-fly embedding.

Say: “Filtered queries use a correctness-first brute-force pass. Here I filter on text contains.”
Run:
```bash
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[1,0,0],"k":2,"filter":{"text_contains":"hello"}}' | jq .
```
This queries the top-2 matches but only among chunks whose text contains “hello”.

Scene 7 — Stale Detection and Rebuild (20–30s)
Say: “Updates bump the data version. If the index becomes stale, a query triggers a background rebuild or falls back to brute-force if configured.”
Run:
```bash
CHUNK=$(curl -s http://localhost:8000/api/v1/libraries/$LIB/chunks | python -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')

curl -s -X PATCH http://localhost:8000/api/v1/libraries/$LIB/chunks/$CHUNK \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello again"}' | jq .

curl -s http://localhost:8000/api/v1/libraries/$LIB/index:status | jq .
```
- Captures a chunk id from the library for updating.
- Updates the chunk’s text, which may mark the index stale depending on policy.
- Shows the index status to verify versions and staleness.

Scene 8 — Leader–Follower Replication (60–80s)
Say: “Now I’ll show leader–follower. The leader accepts writes and exposes a snapshot; the follower polls and applies the snapshot, then rebuilds indexes. All write endpoints on the follower return 403.”
Run leader in Terminal A:
```bash
export VECTORDB_NODE_ROLE=leader
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```
- Sets the node role to leader and starts the API on port 8001.
Run follower in Terminal B:
```bash
export VECTORDB_NODE_ROLE=follower
export VECTORDB_LEADER_URL=http://localhost:8001
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```
- Sets the node role to follower, points to the leader URL, and starts the API on port 8002.
Run verification in Terminal C:
```bash
curl -s -X POST http://localhost:8001/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"cluster-demo","embedding_dimension":8,"default_index_type":"brute_force"}' | jq .

sleep 3
curl -s http://localhost:8002/api/v1/libraries | jq .

curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8002/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"x","embedding_dimension":8,"default_index_type":"brute_force"}'
```
- Creates a library on the leader.
- Waits briefly and lists libraries on the follower to confirm replication.
- Attempts a write on the follower, which correctly returns 403.

Say: “We see the follower has the new library and rejects writes with a 403, as intended.”

Scene 9 — Error Handling and Tests (20–30s)
Say: “Domain errors are mapped to HTTP exceptions: not found returns 404, conflicts return 409, and validation errors return 400 with concise messages. Unit and integration tests cover models, repositories, concurrency, indexes, and services, and we successfully ran a stress sequence to validate stability under load.”
Run:
```bash
pytest -q
```
This runs the entire unit and integration test suite and reports concise results.

Scene 10 — Docker (15–20s)
Say: “There’s a Dockerfile for easy deployment. The image is based on python:3.11-slim and includes a healthcheck hitting the /health endpoint.”
Run:
```bash
docker build -t vector-db:latest .
docker run -p 8000:8000 --env-file .env vector-db:latest
```
- Builds the Docker image.
- Runs the container exposing port 8000 and loading environment from .env.

Scene 11 — Closing (15–20s)
Say: “In summary, I delivered a clean REST API with custom vector indexes, proper thread-safety, versioning and rebuilds, optional JSON persistence, and leader–follower replication. The design is extensible and well-tested, with a small SDK for convenience. This is ready for real usage and easy to build upon.”

Appendix — Technical Notes (for reference)
Say: “Cosine similarity on normalized vectors equals the dot product. KD-Tree is efficient for low dimensions and exact; it converts L2 distances to cosine-like scores on unit vectors. Random Hyperplane LSH hashes vectors by signs of dot products with random hyperplanes; it is fast and approximate, and falls back to a scan if buckets are empty.”
