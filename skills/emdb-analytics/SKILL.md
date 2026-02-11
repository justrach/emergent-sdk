---
name: emdb-analytics
description: View EmergentDB analytics and usage stats. Use when the user wants to check API usage, latency, errors, growth, or per-key stats.
allowed-tools: Bash, Read, Write, Edit
---

# EmergentDB Analytics

Help the user retrieve analytics and usage data from their EmergentDB account.

## TypeScript SDK

```typescript
import { EmergentDB } from "emergentdb";

const db = new EmergentDB("emdb_your_api_key");

// Request stats by endpoint (last 30 days)
const endpoints = await db.analyticsEndpoints();
// [{ endpoint, requestCount, totalBytes, avgLatencyMs, p95LatencyMs, errorCount }]

// Usage by namespace (last 30 days)
const namespaces = await db.analyticsNamespaces();
// [{ namespace, requestCount, totalVectors, avgLatencyMs }]

// Latency percentiles by day (last 30 days)
const latency = await db.analyticsLatency();
// [{ date, p50, p95, p99, requestCount }]

// Error rates by day (last 30 days)
const errors = await db.analyticsErrors();
// [{ date, totalRequests, errorCount, error4xx, error5xx }]

// Per-API-key usage (last 30 days)
const keys = await db.analyticsKeys();
// [{ apiKeyId, keyName, keyPrefix, requestCount, totalBytes, avgLatencyMs, lastUsed }]

// Vector count growth (daily snapshots, last 90 days)
const growth = await db.analyticsGrowth();
// [{ date, vectorCount }]
```

## Python SDK

```python
from emergentdb import EmergentDB

db = EmergentDB("emdb_your_api_key")

# Request stats by endpoint (last 30 days)
endpoints = db.analytics_endpoints()
# [EndpointStats(endpoint, requestCount, totalBytes, avgLatencyMs, p95LatencyMs, errorCount)]

# Usage by namespace (last 30 days)
namespaces = db.analytics_namespaces()
# [NamespaceStats(namespace, requestCount, totalVectors, avgLatencyMs)]

# Latency percentiles by day (last 30 days)
latency = db.analytics_latency()
# [LatencyEntry(date, p50, p95, p99, requestCount)]

# Error rates by day (last 30 days)
errors = db.analytics_errors()
# [ErrorEntry(date, totalRequests, errorCount, error4xx, error5xx)]

# Per-API-key usage (last 30 days)
keys = db.analytics_keys()
# [KeyStats(apiKeyId, keyName, keyPrefix, requestCount, totalBytes, avgLatencyMs, lastUsed)]

# Vector count growth (daily snapshots, last 90 days)
growth = db.analytics_growth()
# [GrowthEntry(date, vectorCount)]
```

## Available Analytics

| Method | Data | Window |
|---|---|---|
| `analyticsEndpoints` / `analytics_endpoints` | Requests, bytes, latency per endpoint | 30 days |
| `analyticsNamespaces` / `analytics_namespaces` | Requests, vectors, latency per namespace | 30 days |
| `analyticsLatency` / `analytics_latency` | p50, p95, p99 latency by day | 30 days |
| `analyticsErrors` / `analytics_errors` | Error counts (4xx, 5xx) by day | 30 days |
| `analyticsKeys` / `analytics_keys` | Usage stats per API key | 30 days |
| `analyticsGrowth` / `analytics_growth` | Total vector count by day | 90 days |

When helping the user, suggest the right analytics method based on what they want to understand (performance, errors, growth, etc.).
