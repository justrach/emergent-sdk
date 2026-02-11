---
name: emdb-delete
description: Delete vectors from EmergentDB by ID. Use when the user wants to remove vectors, clean up data, or delete entries from the database.
allowed-tools: Bash, Read, Write, Edit
---

# Delete Vectors from EmergentDB

Help the user delete vectors from EmergentDB using the official SDKs.

## TypeScript SDK

```typescript
import { EmergentDB } from "emergentdb";

const db = new EmergentDB("emdb_your_api_key");

// Delete from default namespace
const result = await db.delete(42);
// result: { deleted: true, id: 42, namespace: "default" }

// Delete from a specific namespace
const result2 = await db.delete(7, "production");
// result2: { deleted: true, id: 7, namespace: "production" }

// Delete multiple vectors
for (const id of [1, 2, 3, 4, 5]) {
  await db.delete(id, "my-namespace");
}
```

## Python SDK

```python
from emergentdb import EmergentDB

db = EmergentDB("emdb_your_api_key")

# Delete from default namespace
result = db.delete(42)
# result.deleted == True, result.id == 42, result.namespace == "default"

# Delete from a specific namespace
result = db.delete(7, namespace="production")

# Delete multiple vectors
for id in range(1, 6):
    db.delete(id, namespace="my-namespace")
```

## Response Structure

```json
{
  "deleted": true,
  "id": 42,
  "namespace": "default"
}
```

## Key Details

- **Namespace scoping**: Deletes only affect the specified namespace. Deleting ID 1 from "production" does not affect ID 1 in "default".
- **Idempotent**: Deleting a non-existent ID does not raise an error.
- **Immediate**: Vectors are removed instantly and will no longer appear in search results.

When helping the user, confirm which namespace they want to delete from to avoid accidental data loss.
