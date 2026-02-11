/**
 * Test: Can a user who uses Zod in their own app work with our SDK outputs?
 *
 * Simulates a real user workflow:
 * - They have their OWN Zod schemas in their app
 * - They call our SDK methods and get back typed results
 * - They want to feed our results into their own schemas, functions, pipelines
 * - They want to compose our schemas with theirs
 */

import { z } from "dhi";

// ── Define SDK schemas inline (mirrors src/index.ts) ──
// In real usage: import { InsertResultSchema, ... } from "emergentdb"

const InsertResultSchema = z.object({
  success: z.boolean(),
  id: z.number().int(),
  namespace: z.string(),
  upserted: z.boolean(),
});

const BatchInsertResultSchema = z.object({
  success: z.boolean(),
  ids: z.array(z.number().int()),
  count: z.number().int(),
  namespace: z.string(),
  new_count: z.number().int(),
  upserted_count: z.number().int(),
});

const SearchResultSchema = z.object({
  id: z.number().int(),
  score: z.number(),
  metadata: z.record(z.string(), z.any()).optional(),
});

const SearchResponseSchema = z.object({
  results: z.array(SearchResultSchema),
  count: z.number().int(),
  namespace: z.string(),
});

const VectorEntrySchema = z.object({
  id: z.number().int().positive(),
  vector: z.array(z.number()),
  metadata: z.record(z.string(), z.any()).optional(),
});

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  PASS  ${name}`);
  } catch (e) {
    failed++;
    console.log(`  FAIL  ${name}: ${e.message}`);
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assertion failed");
}

// ── Simulate API responses (what the SDK methods would return after parse) ──
const mockInsertResponse = InsertResultSchema.parse({
  success: true,
  id: 42,
  namespace: "production",
  upserted: false,
});

const mockSearchResponse = SearchResponseSchema.parse({
  results: [
    { id: 1, score: 0.95, metadata: { title: "Doc A", category: "science" } },
    { id: 2, score: 0.87, metadata: { title: "Doc B", category: "math" } },
    { id: 3, score: 0.72 },
  ],
  count: 3,
  namespace: "production",
});

const mockBatchResponse = BatchInsertResultSchema.parse({
  success: true,
  ids: [1, 2, 3, 4, 5],
  count: 5,
  namespace: "default",
  new_count: 3,
  upserted_count: 2,
});

console.log("\n=== User Workflow Tests: dhi SDK outputs in Zod pipelines ===\n");

// ── 1. User has their own app schema and wants to combine with SDK result ──
test("User extends SDK result with their own fields", () => {
  // User's app has a logging schema
  const AppLogEntry = z.object({
    timestamp: z.string(),
    action: z.string(),
    vectorId: z.number(),
    namespace: z.string(),
    success: z.boolean(),
  });

  // User creates a log entry from our SDK insert result
  const logEntry = AppLogEntry.parse({
    timestamp: new Date().toISOString(),
    action: "insert",
    vectorId: mockInsertResponse.id,
    namespace: mockInsertResponse.namespace,
    success: mockInsertResponse.success,
  });

  assert(logEntry.vectorId === 42);
  assert(logEntry.namespace === "production");
  assert(logEntry.success === true);
});

// ── 2. User filters search results with their own logic ──
test("User processes search results array with .filter/.map", () => {
  const highScoreResults = mockSearchResponse.results
    .filter((r) => r.score > 0.8)
    .map((r) => ({ id: r.id, title: r.metadata?.title ?? "untitled" }));

  assert(highScoreResults.length === 2);
  assert(highScoreResults[0].title === "Doc A");
  assert(highScoreResults[1].title === "Doc B");
});

// ── 3. User has their own Zod schema for metadata and validates SDK metadata ──
test("User validates SDK metadata with their own schema", () => {
  const UserMetadataSchema = z.object({
    title: z.string(),
    category: z.enum(["science", "math", "history"]),
  });

  // User validates the metadata from our search results
  const result = mockSearchResponse.results[0];
  const validatedMeta = UserMetadataSchema.parse(result.metadata);
  assert(validatedMeta.title === "Doc A");
  assert(validatedMeta.category === "science");
});

// ── 4. User spreads SDK result into their own object ──
test("User spreads SDK result into custom object", () => {
  const enriched = {
    ...mockInsertResponse,
    source: "my-app",
    insertedAt: Date.now(),
  };

  assert(enriched.id === 42);
  assert(enriched.namespace === "production");
  assert(enriched.source === "my-app");
  assert(typeof enriched.insertedAt === "number");
});

// ── 5. User destructures SDK result ──
test("User destructures SDK result", () => {
  const { id, namespace, upserted } = mockInsertResponse;
  assert(id === 42);
  assert(namespace === "production");
  assert(upserted === false);
});

// ── 6. User builds a pipeline: SDK search result → their own DB model ──
test("User maps SDK search results into their own DB records", () => {
  const DbRecordSchema = z.object({
    externalId: z.number(),
    relevanceScore: z.number(),
    title: z.string(),
    retrieved: z.boolean(),
  });

  const dbRecords = mockSearchResponse.results
    .filter((r) => r.metadata)
    .map((r) =>
      DbRecordSchema.parse({
        externalId: r.id,
        relevanceScore: r.score,
        title: r.metadata.title,
        retrieved: true,
      })
    );

  assert(dbRecords.length === 2);
  assert(dbRecords[0].externalId === 1);
  assert(dbRecords[0].relevanceScore === 0.95);
  assert(dbRecords[0].title === "Doc A");
});

// ── 7. User serializes SDK result to JSON for logging/storage ──
test("User JSON.stringify SDK result", () => {
  const json = JSON.stringify(mockInsertResponse);
  const parsed = JSON.parse(json);
  assert(parsed.id === 42);
  assert(parsed.namespace === "production");
});

// ── 8. User uses SDK result in a function with typed params ──
test("User passes SDK result to their typed function", () => {
  function processInsert(result) {
    if (result.upserted) {
      return `Updated vector ${result.id}`;
    }
    return `Inserted new vector ${result.id} into ${result.namespace}`;
  }

  const msg = processInsert(mockInsertResponse);
  assert(msg === "Inserted new vector 42 into production");
});

// ── 9. User collects batch IDs for downstream processing ──
test("User uses batch insert IDs for downstream pipeline", () => {
  const { ids, new_count, upserted_count } = mockBatchResponse;

  // User tracks which vectors need embedding refresh
  const needsRefresh = ids.slice(0, new_count);
  assert(needsRefresh.length === 3);
  assert(needsRefresh[0] === 1);

  // User tracks upsert stats
  assert(upserted_count === 2);
});

// ── 10. User creates a VectorEntry to pass TO the SDK ──
test("User creates VectorEntry for SDK input", () => {
  const entry = VectorEntrySchema.parse({
    id: 100,
    vector: [0.1, 0.2, 0.3, 0.4],
    metadata: { title: "My document", source: "upload" },
  });

  assert(entry.id === 100);
  assert(entry.vector.length === 4);
  assert(entry.metadata.title === "My document");
});

// ── 11. User stores results in an array and iterates ──
test("User accumulates SDK results in an array", () => {
  const allResults = [];

  // Simulate multiple inserts
  for (let i = 1; i <= 3; i++) {
    const result = InsertResultSchema.parse({
      success: true,
      id: i,
      namespace: "batch-test",
      upserted: false,
    });
    allResults.push(result);
  }

  assert(allResults.length === 3);
  const allIds = allResults.map((r) => r.id);
  assert(JSON.stringify(allIds) === "[1,2,3]");
});

// ── 12. User wraps SDK response in their own API response ──
test("User wraps SDK search in their own API response schema", () => {
  const ApiResponse = z.object({
    status: z.literal("ok"),
    data: SearchResponseSchema,
    requestId: z.string(),
  });

  const response = ApiResponse.parse({
    status: "ok",
    data: {
      results: [{ id: 1, score: 0.9 }],
      count: 1,
      namespace: "default",
    },
    requestId: "req_abc123",
  });

  assert(response.data.results[0].id === 1);
  assert(response.requestId === "req_abc123");
});

// ── Summary ──
console.log(`\n  Results: ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
