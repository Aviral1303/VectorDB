# Demo Runbook (Commands)

## 1) Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optional Cohere (otherwise local fallback embeddings are used)
export VECTORDB_EMBEDDING_PROVIDER=cohere
export VECTORDB_COHERE_API_KEY=pa6sRhnVAedMVClPAwoCvC1MjHKEwjtcGSTjWRMd
```

## 2) Run (single node)
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open docs: http://localhost:8000/docs

## 3) Basic Demo (curl)
```bash
# Create library (dim=3)
curl -s -X POST http://localhost:8000/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo","embedding_dimension":3,"default_index_type":"brute_force"}'

# Capture library id
LIB=$(curl -s http://localhost:8000/api/v1/libraries | python -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')

# Create a document
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents \
  -H 'Content-Type: application/json' \
  -d '{"title":"Doc1"}'
DOC=$(curl -s http://localhost:8000/api/v1/libraries/$LIB/documents | python -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')

# Add chunks (embedding + text->embedding)
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents/$DOC/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello world","embedding":[1,0,0]}'

curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/documents/$DOC/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"bonjour","use_embedding_service":true}'

# Build index (choose brute_force | kd_tree | lsh)
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/index:build \
  -H 'Content-Type: application/json' \
  -d '{"index_type":"kd_tree"}'

# Check index status
curl -s http://localhost:8000/api/v1/libraries/$LIB/index:status | jq .

# Query by embedding
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[1,0,0],"k":2}' | jq .

# Query by text (embedding generated)
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"hello","use_embedding_service":true,"k":2}' | jq .

# Optional: metadata filter (text_contains)
curl -s -X POST http://localhost:8000/api/v1/libraries/$LIB/query \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[1,0,0],"k":2,"filter":{"text_contains":"hello"}}' | jq .

# Update a chunk (demonstrate staleness detection)
CHUNK=$(curl -s http://localhost:8000/api/v1/libraries/$LIB/chunks | python -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
curl -s -X PATCH http://localhost:8000/api/v1/libraries/$LIB/chunks/$CHUNK \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello again"}' | jq .

# Clean up
curl -s -X DELETE http://localhost:8000/api/v1/libraries/$LIB -o /dev/null -w '%{http_code}\n'
```

## 4) Leader-Follower Demo (two terminals)
Terminal A (Leader):
```bash
export VECTORDB_NODE_ROLE=leader
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```
Terminal B (Follower):
```bash
export VECTORDB_NODE_ROLE=follower
export VECTORDB_LEADER_URL=http://localhost:8001
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```
Verify:
```bash
# Create on leader
curl -s -X POST http://localhost:8001/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"cluster-demo","embedding_dimension":8,"default_index_type":"brute_force"}' | jq .

# Wait a moment, then list on follower
curl -s http://localhost:8002/api/v1/libraries | jq .

# Follower write should be forbidden (403)
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8002/api/v1/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"x","embedding_dimension":8,"default_index_type":"brute_force"}'
```

## 5) SDK (optional)
```bash
python - << 'PY'
from sdk.client import VectorDBClient
c=VectorDBClient('http://localhost:8000')
lib=c.create_library('demo',3)
doc=c.create_document(lib['id'],'Doc1')
c.create_chunk(lib['id'],doc['id'],'hello world',[1,0,0])
c.build_index(lib['id'],'kd_tree')
print(c.query(lib['id'],k=1,query_embedding=[1,0,0]))
c.close()
PY
```

## 6) Tests & Stress
```bash
pytest -q
```

## 7) Docker
```bash
docker build -t vector-db:latest .
docker run -p 8000:8000 --env-file .env vector-db:latest
```
