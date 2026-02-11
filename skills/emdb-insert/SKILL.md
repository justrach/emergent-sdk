---
name: emdb-insert
description: Insert vectors into EmergentDB using the SDK. Use when the user wants to store embeddings, index documents, or batch upload vectors into EmergentDB.
allowed-tools: Bash, Read, Write, Edit
---

# Insert Vectors into EmergentDB

Help the user insert vectors into EmergentDB using the official SDKs.

## Prerequisites

- An EmergentDB API key (starts with `emdb_`)
- Vector embeddings (default dimension: 1536 for OpenAI text-embedding-3-small)

## TypeScript SDK

```typescript
import { EmergentDB } from "emergentdb";

const db = new EmergentDB("emdb_your_api_key");

// Single insert
const result = await db.insert(1, embedding, { title: "My doc" }, "production");
// result: { success: true, id: 1, namespace: "production", upserted: false }

// Batch insert (max 1000 per call)
const batch = await db.batchInsert([
  { id: 1, vector: [...], metadata: { title: "Doc 1" } },
  { id: 2, vector: [...], metadata: { title: "Doc 2" } },
], "production");

// Unlimited batch (auto-chunks into 1000s)
const all = await db.batchInsertAll(vectors, "production");
```

## Python SDK

```python
from emergentdb import EmergentDB

db = EmergentDB("emdb_your_api_key")

# Single insert
result = db.insert(1, embedding, metadata={"title": "My doc"}, namespace="production")

# Batch insert
result = db.batch_insert([
    {"id": 1, "vector": [...], "metadata": {"title": "Doc 1"}},
    {"id": 2, "vector": [...], "metadata": {"title": "Doc 2"}},
], namespace="production")

# Unlimited batch
result = db.batch_insert_all(vectors, namespace="production")
```

## Key Behaviors

- **Upsert**: Re-inserting an existing ID in the same namespace replaces it. Response shows `upserted: true`.
- **Namespaces**: Optional, defaults to `"default"`. Created automatically on first use.
- **Metadata fields**: `title` (str), `content` (str), `source_url` (str), `tags` (str[])
- **Capacity**: Returns HTTP 402 if the tenant's vector quota is exceeded.
- **Dimensions**: Must match the index dimension (1536 by default). Mismatched dimensions cause errors.

## Common Pattern: OpenAI Embeddings

```python
import openai
from emergentdb import EmergentDB

client = openai.OpenAI()
db = EmergentDB("emdb_your_key")

# Generate + store
resp = client.embeddings.create(model="text-embedding-3-small", input="My document text")
db.insert(1, resp.data[0].embedding, metadata={"title": "My document"})
```

When helping the user, determine which SDK they prefer and guide them through the insert flow. If they have raw text, suggest using OpenAI or another embedding model first.
