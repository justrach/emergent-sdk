# EmergentDB Python SDK

Official Python SDK for [EmergentDB](https://emergentdb.com) — a managed vector database for embeddings.

## Install

```bash
pip install emergentdb
```

## Quick Start

```python
from emergentdb import EmergentDB

db = EmergentDB("emdb_your_api_key")

# Insert a vector
db.insert(1, [0.1, 0.2, ...], metadata={"title": "My document"})

# Search
results = db.search([0.1, 0.2, ...], k=5, include_metadata=True)

# Delete
db.delete(1)
```

## API

### `EmergentDB(api_key, base_url?, timeout?)`

Create a client. API key must start with `emdb_`.

| Param      | Type  | Default                        |
|------------|-------|--------------------------------|
| `base_url` | str   | `https://api.emergentdb.com`   |
| `timeout`  | float | 30.0                           |

Supports context manager:

```python
with EmergentDB("emdb_your_key") as db:
    db.insert(1, vector)
```

### `db.insert(id, vector, metadata?, namespace?)`

Insert a single vector. Re-inserting the same ID in the same namespace upserts it.

```python
result = db.insert(1, embedding, metadata={"title": "Doc"}, namespace="production")
# InsertResult(success=True, id=1, namespace="production", upserted=False)
```

### `db.batch_insert(vectors, namespace?)`

Insert up to 1,000 vectors in one call.

```python
result = db.batch_insert([
    {"id": 1, "vector": [...], "metadata": {"title": "Doc 1"}},
    {"id": 2, "vector": [...], "metadata": {"title": "Doc 2"}},
], namespace="production")
# BatchInsertResult(success=True, ids=[1, 2], count=2, new_count=2, upserted_count=0)
```

### `db.batch_insert_all(vectors, namespace?)`

Insert any number of vectors — auto-chunks into batches of 1,000.

```python
result = db.batch_insert_all(large_vector_list, namespace="production")
```

### `db.search(vector, k?, include_metadata?, namespace?)`

Search for similar vectors.

| Param              | Type  | Default     |
|--------------------|-------|-------------|
| `k`                | int   | 10          |
| `include_metadata` | bool  | False       |
| `namespace`        | str   | `"default"` |

```python
results = db.search(query_vector, k=10, include_metadata=True, namespace="production")

for r in results.results:
    print(f"{r.id}: {r.score} — {r.metadata.get('title')}")
```

Scores are distances — **lower = more similar**.

### `db.delete(id, namespace?)`

Delete a vector by ID.

```python
result = db.delete(1, namespace="production")
# DeleteResult(deleted=True, id=1, namespace="production")
```

### `db.list_namespaces()`

List all namespaces that have vectors.

```python
namespaces = db.list_namespaces()
# ["default", "production", "staging"]
```

## Namespaces

Namespaces partition your vectors into isolated groups. Created automatically on first insert.

```python
# Insert into different namespaces
db.insert(1, vec, metadata={"title": "Prod doc"}, namespace="production")
db.insert(1, vec, metadata={"title": "Dev doc"}, namespace="development")

# Search is scoped to one namespace
prod = db.search(q, namespace="production")
dev = db.search(q, namespace="development")
```

Vector IDs are unique per namespace — ID 1 in `"production"` and ID 1 in `"development"` are completely separate vectors.

## With OpenAI Embeddings

```python
import openai
from emergentdb import EmergentDB

client = openai.OpenAI()
db = EmergentDB("emdb_your_key")

# Generate embedding
resp = client.embeddings.create(
    model="text-embedding-3-small",
    input="How do neural networks learn?"
)

# Store it
db.insert(1, resp.data[0].embedding, metadata={
    "title": "Neural Networks 101",
    "tags": ["ml", "neural-networks"],
})

# Search later
query_resp = client.embeddings.create(
    model="text-embedding-3-small",
    input="What is backpropagation?"
)
results = db.search(query_resp.data[0].embedding, k=5, include_metadata=True)

for r in results.results:
    print(f"{r.score:.4f} — {r.metadata.get('title', 'untitled')}")
```

## Error Handling

```python
from emergentdb import EmergentDB, EmergentDBError

try:
    db.insert(1, vector)
except EmergentDBError as e:
    print(e.status_code)  # 401, 402, 400, etc.
    print(e.body)         # Full error response
```

| Status | Meaning                  |
|--------|--------------------------|
| 400    | Invalid request          |
| 401    | Bad or missing API key   |
| 402    | Vector capacity exceeded |
| 404    | Vector not found         |
| 500    | Server error             |

## Response Models

All response types are [dhi](https://github.com/nicholasgasior/dhi) BaseModel classes (Pydantic v2-compatible):

```python
from emergentdb import (
    InsertResult,
    BatchInsertResult,
    SearchResult,
    SearchResponse,
    DeleteResult,
)

# Use like Pydantic models
result = db.insert(1, vector)
print(result.model_dump())
print(result.model_dump_json())
```

## Requirements

- Python >= 3.8
- `httpx >= 0.24.0`
- `dhi >= 1.1.3`

## QDKV — Metadata Cache

Every EmergentDB account includes **10K QDKV keys free** — same `emdb_` API key, no new signup.

QDKV is a SIMD-accelerated key-value cache (Redis alternative) for session state, feature flags, rate counters, and anything that needs sub-millisecond reads at the edge.

### HTTP API

```bash
# SET
curl -X POST https://api.emergentdb.com/qdkv/set \
  -H "Authorization: Bearer emdb_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "key": "session:abc", "value": "{\"userId\":42}", "ttlMs": 3600000 }'

# GET
curl https://api.emergentdb.com/qdkv/get/session:abc \
  -H "Authorization: Bearer emdb_YOUR_API_KEY"
# → { "value": "{\"userId\":42}", "found": true }

# DEL
curl -X DELETE https://api.emergentdb.com/qdkv/del/session:abc \
  -H "Authorization: Bearer emdb_YOUR_API_KEY"

# MGET (batch)
curl -X POST https://api.emergentdb.com/qdkv/mget \
  -H "Authorization: Bearer emdb_YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "keys": ["session:abc", "session:xyz"] }'
# → { "values": { "session:abc": "{...}", "session:xyz": null } }

# Stats
curl https://api.emergentdb.com/qdkv/stats \
  -H "Authorization: Bearer emdb_YOUR_API_KEY"
# → { "keyCount": 42, "maxKeys": 10000, "plan": "free", "percentUsed": 0 }
```

### In Python (httpx)

```python
import httpx
import json

KEY = "emdb_YOUR_API_KEY"
BASE = "https://api.emergentdb.com"
headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

with httpx.Client() as client:
    # SET
    client.post(f"{BASE}/qdkv/set", headers=headers, json={
        "key": "user:42:prefs",
        "value": json.dumps({"theme": "dark"}),
        "ttlMs": 86400_000,
    })

    # GET
    r = client.get(f"{BASE}/qdkv/get/user:42:prefs", headers=headers).json()
    if r["found"]:
        prefs = json.loads(r["value"])

    # MGET
    r = client.post(f"{BASE}/qdkv/mget", headers=headers,
                    json={"keys": ["user:42:prefs", "user:99:prefs"]}).json()
    # r["values"] → { "user:42:prefs": "{...}", "user:99:prefs": None }

    # DEL
    client.delete(f"{BASE}/qdkv/del/user:42:prefs", headers=headers)
```

### Pricing

| Plan | Max Keys | Price |
|------|----------|-------|
| Free (all accounts) | 10,000 | $0/mo |
| Launch | 1,000,000 | $29/mo |
| Scale | 10,000,000 | $99/mo |

---

## License

MIT
