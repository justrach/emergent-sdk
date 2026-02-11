---
name: emdb-namespaces
description: List and manage namespaces in EmergentDB. Use when the user wants to see their namespaces, organize vectors into groups, or understand namespace isolation.
allowed-tools: Bash, Read, Write, Edit
---

# Namespaces in EmergentDB

Help the user work with namespaces to organize vectors into isolated groups.

## TypeScript SDK

```typescript
import { EmergentDB } from "emergentdb";

const db = new EmergentDB("emdb_your_api_key");

// List all namespaces
const namespaces = await db.listNamespaces();
// ["default", "production", "staging"]

// Insert into a namespace (creates it automatically)
await db.insert(1, embedding, { title: "Doc" }, "production");

// Search within a namespace
const results = await db.search(queryVec, {
  k: 10,
  includeMetadata: true,
  namespace: "production",
});

// Batch insert into a namespace
await db.batchInsert(vectors, "staging");
```

## Python SDK

```python
from emergentdb import EmergentDB

db = EmergentDB("emdb_your_api_key")

# List all namespaces
namespaces = db.list_namespaces()
# ["default", "production", "staging"]

# Insert into a namespace (creates it automatically)
db.insert(1, embedding, metadata={"title": "Doc"}, namespace="production")

# Search within a namespace
results = db.search(query_vec, k=10, include_metadata=True, namespace="production")

# Batch insert into a namespace
db.batch_insert(vectors, namespace="staging")
```

## Key Details

- **Auto-created**: Namespaces are created automatically on first insert. No setup required.
- **Isolation**: Vectors in one namespace are completely invisible to searches in another.
- **Default namespace**: If no namespace is specified, operations use the `"default"` namespace.
- **Naming**: Namespace names are strings up to 64 characters.
- **Listing**: `listNamespaces()` / `list_namespaces()` returns all namespaces for your account.

## Common Pattern: Multi-Environment Setup

```python
from emergentdb import EmergentDB

db = EmergentDB("emdb_your_api_key")

# Use namespaces to separate environments
for doc in documents:
    db.insert(doc["id"], doc["embedding"], metadata=doc["meta"], namespace="staging")

# Promote to production when ready
for doc in documents:
    db.insert(doc["id"], doc["embedding"], metadata=doc["meta"], namespace="production")
```

When helping the user, suggest namespaces for organizing data by environment, tenant, or data type.
