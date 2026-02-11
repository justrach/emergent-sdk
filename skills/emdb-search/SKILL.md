---
name: emdb-search
description: Search for similar vectors in EmergentDB. Use when the user wants to query, find similar documents, or do semantic search against their vector database.
allowed-tools: Bash, Read, Write, Edit
---

# Search Vectors in EmergentDB

Help the user search for similar vectors using the official SDKs.

## TypeScript SDK

```typescript
import { EmergentDB } from "emergentdb";

const db = new EmergentDB("emdb_your_api_key");

// Basic search
const results = await db.search(queryVector, { k: 10 });

// With metadata and namespace
const results = await db.search(queryVector, {
  k: 5,
  includeMetadata: true,
  namespace: "production",
});

// Access results
for (const r of results.results) {
  console.log(`ID: ${r.id}, Score: ${r.score}, Title: ${r.metadata?.title}`);
}
```

## Python SDK

```python
from emergentdb import EmergentDB

db = EmergentDB("emdb_your_api_key")

# Basic search
results = db.search(query_vector, k=10)

# With metadata and namespace
results = db.search(query_vector, k=5, include_metadata=True, namespace="production")

# Access results
for r in results.results:
    print(f"ID: {r.id}, Score: {r.score}, Title: {r.metadata.get('title')}")
```

## Search Response Structure

```json
{
  "results": [
    { "id": 42, "score": 0.05, "metadata": { "title": "Best match" } },
    { "id": 17, "score": 0.12 }
  ],
  "count": 2,
  "namespace": "production"
}
```

## Key Details

- **Score**: Distance (lower = more similar). NOT a similarity percentage.
- **k**: Max results, 1-100, default 10.
- **include_metadata**: Must be `true` to get metadata back (default `false`).
- **Namespace scoping**: Searches only return vectors from the specified namespace.
- **Fan-out**: Search runs across all shards in parallel and merges results.
- **Real-time**: Vectors are searchable immediately after insertion.

## Common Pattern: Semantic Search

```python
import openai
from emergentdb import EmergentDB

client = openai.OpenAI()
db = EmergentDB("emdb_your_key")

# Embed the user's query
query = "How do neural networks learn?"
resp = client.embeddings.create(model="text-embedding-3-small", input=query)

# Search for similar documents
results = db.search(resp.data[0].embedding, k=5, include_metadata=True)
for r in results.results:
    print(f"{r.score:.4f} - {r.metadata.get('title', 'untitled')}")
```

When helping the user, make sure their query vector uses the same embedding model and dimensions as their stored vectors.
