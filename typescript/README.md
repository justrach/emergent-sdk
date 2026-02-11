# EmergentDB TypeScript SDK

Official TypeScript/JavaScript SDK for [EmergentDB](https://emergentdb.com) — a managed vector database for embeddings.

## Install

```bash
npm install emergentdb
```

## Quick Start

```typescript
import { EmergentDB } from "emergentdb";

const db = new EmergentDB("emdb_your_api_key");

// Insert a vector
await db.insert(1, [0.1, 0.2, ...], { title: "My document" });

// Search
const results = await db.search([0.1, 0.2, ...], {
  k: 5,
  includeMetadata: true,
});

// Delete
await db.delete(1);
```

## API

### `new EmergentDB(apiKey, options?)`

Create a client. API key must start with `emdb_`.

| Option    | Type   | Default                        |
|-----------|--------|--------------------------------|
| `baseUrl` | string | `https://api.emergentdb.com`   |

### `db.insert(id, vector, metadata?, namespace?)`

Insert a single vector. Re-inserting the same ID in the same namespace upserts it.

```typescript
const result = await db.insert(1, embedding, { title: "Doc" }, "production");
// { success: true, id: 1, namespace: "production", upserted: false }
```

### `db.batchInsert(vectors, namespace?)`

Insert up to 1,000 vectors in one call.

```typescript
const result = await db.batchInsert([
  { id: 1, vector: [...], metadata: { title: "Doc 1" } },
  { id: 2, vector: [...], metadata: { title: "Doc 2" } },
], "production");
// { success: true, ids: [1, 2], count: 2, new_count: 2, upserted_count: 0 }
```

### `db.batchInsertAll(vectors, namespace?)`

Insert any number of vectors — auto-chunks into batches of 1,000.

```typescript
const result = await db.batchInsertAll(largeVectorArray, "production");
```

### `db.search(vector, options?)`

Search for similar vectors.

| Option            | Type    | Default     |
|-------------------|---------|-------------|
| `k`               | number  | 10          |
| `includeMetadata`  | boolean | false       |
| `namespace`        | string  | `"default"` |

```typescript
const { results, count, namespace } = await db.search(queryVector, {
  k: 10,
  includeMetadata: true,
  namespace: "production",
});

for (const r of results) {
  console.log(`${r.id}: ${r.score} — ${r.metadata?.title}`);
}
```

Scores are distances — **lower = more similar**.

### `db.delete(id, namespace?)`

Delete a vector by ID.

```typescript
const result = await db.delete(1, "production");
// { deleted: true, id: 1, namespace: "production" }
```

### `db.listNamespaces()`

List all namespaces that have vectors.

```typescript
const namespaces = await db.listNamespaces();
// ["default", "production", "staging"]
```

## Namespaces

Namespaces partition your vectors into isolated groups. They're created automatically on first insert — no setup needed.

```typescript
// Insert into different namespaces
await db.insert(1, vec, { title: "Prod doc" }, "production");
await db.insert(1, vec, { title: "Dev doc" }, "development");

// Search is scoped to one namespace
const prod = await db.search(q, { namespace: "production" });
const dev = await db.search(q, { namespace: "development" });
```

Vector IDs are unique per namespace — ID 1 in `"production"` and ID 1 in `"development"` are completely separate vectors.

## With OpenAI Embeddings

```typescript
import OpenAI from "openai";
import { EmergentDB } from "emergentdb";

const openai = new OpenAI();
const db = new EmergentDB("emdb_your_key");

// Generate embedding
const resp = await openai.embeddings.create({
  model: "text-embedding-3-small",
  input: "How do neural networks learn?",
});

// Store it
await db.insert(1, resp.data[0].embedding, {
  title: "Neural Networks 101",
  tags: ["ml", "neural-networks"],
});

// Search later
const queryResp = await openai.embeddings.create({
  model: "text-embedding-3-small",
  input: "What is backpropagation?",
});
const results = await db.search(queryResp.data[0].embedding, {
  k: 5,
  includeMetadata: true,
});
```

## Error Handling

```typescript
import { EmergentDB, EmergentDBError } from "emergentdb";

try {
  await db.insert(1, vector);
} catch (err) {
  if (err instanceof EmergentDBError) {
    console.log(err.status);  // 401, 402, 400, etc.
    console.log(err.body);    // Full error response
  }
}
```

| Status | Meaning                  |
|--------|--------------------------|
| 400    | Invalid request          |
| 401    | Bad or missing API key   |
| 402    | Vector capacity exceeded |
| 404    | Vector not found         |
| 500    | Server error             |

## Type Exports

All response types and schemas are exported:

```typescript
import {
  InsertResult, InsertResultSchema,
  BatchInsertResult, BatchInsertResultSchema,
  SearchResult, SearchResultSchema,
  SearchResponse, SearchResponseSchema,
  DeleteResult, DeleteResultSchema,
  SearchOptions, SearchOptionsSchema,
  VectorEntry, VectorEntrySchema,
} from "emergentdb";
```

Schemas use [dhi](https://github.com/nicholasgasior/dhi) (Zod-compatible), so you can compose them into your own validation pipelines.

## License

MIT
