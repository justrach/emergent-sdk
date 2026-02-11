/**
 * Live API test for the EmergentDB TypeScript SDK.
 * Tests all SDK methods against production: insert, search, delete,
 * batch insert, namespaces, upsert, and analytics endpoints.
 * Bolt is configured for 1536-dim vectors.
 *
 * Run: node test-live-api.mjs
 */

import { EmergentDB } from "./dist/index.mjs";

const API_KEY = process.env.EMERGENTDB_API_KEY;
if (!API_KEY) {
  console.error("ERROR: EMERGENTDB_API_KEY environment variable is required");
  process.exit(1);
}
const DIM = 1536;

function randVec(seed = 0) {
  // Simple seeded PRNG for reproducible vectors
  let s = seed;
  return Array.from({ length: DIM }, () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return (s / 0x7fffffff) * 0.2 - 0.1;
  });
}

let passed = 0;
let failed = 0;

async function test(name, fn) {
  try {
    const result = await fn();
    passed++;
    console.log(`  PASS  ${name}`);
    if (result) console.log(`        -> ${result}`);
  } catch (e) {
    failed++;
    console.log(`  FAIL  ${name}: ${e.message}`);
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assertion failed");
}

const db = new EmergentDB(API_KEY);

console.log("\n=== Live API Test with TypeScript SDK (1536-dim) ===\n");

// ── 1. Insert into default namespace ──
await test("Insert vector into default namespace", async () => {
  const result = await db.insert(200, randVec(42), { title: "TS SDK test doc" });
  assert(result.success, `Insert failed: ${JSON.stringify(result)}`);
  assert(result.id === 200, `Expected id=200, got ${result.id}`);
  assert(result.namespace === "default", `Expected ns=default, got ${result.namespace}`);
  return `id=${result.id}, ns=${result.namespace}, upserted=${result.upserted}`;
});

// ── 2. Insert into "ts-sdk-test" namespace ──
await test("Insert vector into ts-sdk-test namespace", async () => {
  const result = await db.insert(1, randVec(1), { title: "NS doc 1" }, "ts-sdk-test");
  assert(result.success);
  assert(result.namespace === "ts-sdk-test", `Expected ns=ts-sdk-test, got ${result.namespace}`);
  return `id=${result.id}, ns=${result.namespace}`;
});

// ── 3. Insert second vector into "ts-sdk-test" ──
await test("Insert second vector into ts-sdk-test namespace", async () => {
  const result = await db.insert(2, randVec(2), { title: "NS doc 2" }, "ts-sdk-test");
  assert(result.success);
  return `id=${result.id}, ns=${result.namespace}`;
});

// ── 4. Search in "ts-sdk-test" namespace ──
await test("Search in ts-sdk-test namespace", async () => {
  const result = await db.search(randVec(1), { k: 5, includeMetadata: true, namespace: "ts-sdk-test" });
  assert(result.namespace === "ts-sdk-test", `Expected ns=ts-sdk-test, got ${result.namespace}`);
  assert(result.count > 0, "Expected results in ts-sdk-test namespace");
  return `${result.count} results: ${JSON.stringify(result.results.map(r => ({ id: r.id, score: Math.round(r.score * 10000) / 10000 })))}`;
});

// ── 5. Search in default namespace — IDOR check ──
await test("Search in default namespace (IDOR check)", async () => {
  const result = await db.search(randVec(1), { k: 5, includeMetadata: true });
  const ids = result.results.map(r => r.id);
  assert(!ids.includes(1), `IDOR: ts-sdk-test vector 1 leaked into default namespace! ids=${ids}`);
  assert(!ids.includes(2), `IDOR: ts-sdk-test vector 2 leaked into default namespace! ids=${ids}`);
  return `${result.count} results, ids=${JSON.stringify(ids)}`;
});

// ── 6. List namespaces ──
await test("List namespaces", async () => {
  const namespaces = await db.listNamespaces();
  assert(Array.isArray(namespaces), "Expected array of namespaces");
  return `namespaces: ${JSON.stringify(namespaces)}`;
});

// ── 7. Upsert — re-insert same ID with new metadata ──
await test("Upsert vector in ts-sdk-test namespace", async () => {
  const result = await db.insert(1, randVec(10), { title: "Updated doc 1" }, "ts-sdk-test");
  assert(result.success);
  assert(result.upserted, `Expected upserted=true, got ${result.upserted}`);
  return `upserted=${result.upserted}`;
});

// ── 8. Verify upserted metadata ──
await test("Verify upserted metadata in search results", async () => {
  const result = await db.search(randVec(10), { k: 5, includeMetadata: true, namespace: "ts-sdk-test" });
  assert(result.count > 0, "Expected at least 1 result");
  const match = result.results.find(r => r.id === 1);
  assert(match, `Expected id=1 in results, got ids=${result.results.map(r => r.id)}`);
  assert(match.metadata?.title === "Updated doc 1", `Expected updated metadata, got ${JSON.stringify(match.metadata)}`);
  return `found id=1 with meta=${JSON.stringify(match.metadata)}`;
});

// ── 9. Batch insert ──
await test("Batch insert 5 vectors into ts-batch-test namespace", async () => {
  const vectors = Array.from({ length: 5 }, (_, i) => ({
    id: i + 1,
    vector: randVec(100 + i),
    metadata: { batch: true, index: i },
  }));
  const result = await db.batchInsert(vectors, "ts-batch-test");
  assert(result.success, `Batch insert failed: ${JSON.stringify(result)}`);
  assert(result.count === 5, `Expected count=5, got ${result.count}`);
  assert(result.ids.length === 5, `Expected 5 ids, got ${result.ids.length}`);
  assert(result.namespace === "ts-batch-test", `Expected ns=ts-batch-test, got ${result.namespace}`);
  return `ids=${JSON.stringify(result.ids)}, new=${result.new_count}, upserted=${result.upserted_count}`;
});

// ── 10. Search in batch namespace ──
await test("Search in ts-batch-test namespace", async () => {
  const result = await db.search(randVec(100), { k: 5, includeMetadata: true, namespace: "ts-batch-test" });
  assert(result.count > 0, "Expected results in ts-batch-test namespace");
  assert(result.namespace === "ts-batch-test");
  return `${result.count} results`;
});

// ── 11. Batch namespace isolation — IDOR check ──
await test("Batch namespace isolation (IDOR check)", async () => {
  const result = await db.search(randVec(100), { k: 10, namespace: "ts-sdk-test" });
  const ids = result.results.map(r => r.id);
  // batch vectors (ids 1-5) should NOT appear in ts-sdk-test with batch metadata
  // (id 1,2 exist in ts-sdk-test but with different vectors/metadata)
  for (const r of result.results) {
    if (r.metadata?.batch === true) {
      throw new Error(`IDOR: batch vector leaked into ts-sdk-test! id=${r.id}`);
    }
  }
  return `${result.count} results, no batch vectors leaked`;
});

// ── 12. Analytics: endpoints ──
await test("Analytics: endpoint stats", async () => {
  const stats = await db.analyticsEndpoints();
  assert(Array.isArray(stats), "Expected array of endpoint stats");
  return `${stats.length} endpoints tracked`;
});

// ── 13. Analytics: namespaces ──
await test("Analytics: namespace stats", async () => {
  const stats = await db.analyticsNamespaces();
  assert(Array.isArray(stats), "Expected array of namespace stats");
  return `${stats.length} namespaces tracked`;
});

// ── 14. Analytics: latency ──
await test("Analytics: latency percentiles", async () => {
  const stats = await db.analyticsLatency();
  assert(Array.isArray(stats), "Expected array of latency entries");
  if (stats.length > 0) {
    assert(stats[0].date, "Expected date field");
  }
  return `${stats.length} days of latency data`;
});

// ── 15. Analytics: errors ──
await test("Analytics: error rates", async () => {
  const stats = await db.analyticsErrors();
  assert(Array.isArray(stats), "Expected array of error entries");
  return `${stats.length} days of error data`;
});

// ── 16. Analytics: keys ──
await test("Analytics: API key stats", async () => {
  const stats = await db.analyticsKeys();
  assert(Array.isArray(stats), "Expected array of key stats");
  return `${stats.length} API keys tracked`;
});

// ── 17. Analytics: growth ──
await test("Analytics: vector growth", async () => {
  const stats = await db.analyticsGrowth();
  assert(Array.isArray(stats), "Expected array of growth entries");
  return `${stats.length} days of growth data`;
});

// ── Cleanup: delete all test vectors ──

// Delete from ts-sdk-test namespace
await test("Cleanup: delete vectors from ts-sdk-test namespace", async () => {
  const r1 = await db.delete(1, "ts-sdk-test");
  assert(r1.deleted, "Failed to delete id=1 from ts-sdk-test");
  const r2 = await db.delete(2, "ts-sdk-test");
  assert(r2.deleted, "Failed to delete id=2 from ts-sdk-test");
  return "deleted ids 1,2 from ts-sdk-test";
});

// Delete from ts-batch-test namespace
await test("Cleanup: delete vectors from ts-batch-test namespace", async () => {
  for (let i = 1; i <= 5; i++) {
    const r = await db.delete(i, "ts-batch-test");
    assert(r.deleted, `Failed to delete id=${i} from ts-batch-test`);
  }
  return "deleted ids 1-5 from ts-batch-test";
});

// Delete from default namespace
await test("Cleanup: delete vector from default namespace", async () => {
  const r = await db.delete(200);
  assert(r.deleted, "Failed to delete id=200 from default");
  return "deleted id 200 from default";
});

// ── Verify cleanup ──
await test("Verify ts-sdk-test namespace is empty after cleanup", async () => {
  const result = await db.search(randVec(1), { k: 5, namespace: "ts-sdk-test" });
  assert(result.count === 0, `Expected 0 results after cleanup, got ${result.count}`);
  return "0 results (correct)";
});

await test("Verify ts-batch-test namespace is empty after cleanup", async () => {
  const result = await db.search(randVec(100), { k: 5, namespace: "ts-batch-test" });
  assert(result.count === 0, `Expected 0 results after cleanup, got ${result.count}`);
  return "0 results (correct)";
});

// ── Summary ──
console.log(`\n  Results: ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
