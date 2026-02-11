/**
 * Test: dhi schemas are compatible with Zod workflows
 *
 * Users who use Zod in their app should be able to:
 * 1. Import our schemas and use z.infer<> for types
 * 2. Use .parse() and .safeParse() on API responses
 * 3. Compose our schemas with their own Zod schemas (z.extend, z.merge, z.pick, z.omit)
 * 4. Use .shape to access individual fields
 * 5. Use .partial() and .required()
 */

import { z } from "dhi";

// ── Re-define SDK schemas inline (same as src/index.ts) ──

const InsertResultSchema = z.object({
  success: z.boolean(),
  id: z.number().int(),
  namespace: z.string(),
  upserted: z.boolean(),
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

console.log("\n=== dhi <> Zod Compatibility Tests (TypeScript SDK) ===\n");

// ── 1. .parse() works on valid data ──
test("parse() accepts valid InsertResult", () => {
  const result = InsertResultSchema.parse({
    success: true,
    id: 42,
    namespace: "default",
    upserted: false,
  });
  assert(result.success === true);
  assert(result.id === 42);
  assert(result.namespace === "default");
});

// ── 2. .parse() rejects invalid data ──
test("parse() rejects invalid InsertResult", () => {
  let threw = false;
  try {
    InsertResultSchema.parse({ success: "yes", id: "abc" });
  } catch (e) {
    threw = true;
    assert(e.constructor.name === "ZodError", `Expected ZodError, got ${e.constructor.name}`);
  }
  assert(threw, "Should have thrown");
});

// ── 3. .safeParse() returns success/error ──
test("safeParse() returns success on valid data", () => {
  const result = InsertResultSchema.safeParse({
    success: true,
    id: 1,
    namespace: "prod",
    upserted: true,
  });
  assert(result.success === true);
  assert(result.data.id === 1);
});

test("safeParse() returns error on invalid data", () => {
  const result = InsertResultSchema.safeParse({ success: 123 });
  assert(result.success === false);
  assert(result.error !== undefined);
});

// ── 4. Nested schema parsing (SearchResponse with nested SearchResult[]) ──
test("parse() handles nested schemas", () => {
  const resp = SearchResponseSchema.parse({
    results: [
      { id: 1, score: 0.95, metadata: { title: "hello" } },
      { id: 2, score: 0.87 },
    ],
    count: 2,
    namespace: "default",
  });
  assert(resp.results.length === 2);
  assert(resp.results[0].score === 0.95);
  assert(resp.results[0].metadata.title === "hello");
  assert(resp.results[1].metadata === undefined);
});

// ── 5. .shape access ──
test(".shape gives access to individual field schemas", () => {
  const idSchema = InsertResultSchema.shape.id;
  assert(idSchema !== undefined, ".shape.id should exist");
  const parsed = idSchema.parse(42);
  assert(parsed === 42);
});

// ── 6. Schema composition: .extend() ──
test(".extend() adds fields to schema", () => {
  const ExtendedResult = InsertResultSchema.extend({
    latencyMs: z.number(),
  });
  const result = ExtendedResult.parse({
    success: true,
    id: 1,
    namespace: "default",
    upserted: false,
    latencyMs: 12.5,
  });
  assert(result.latencyMs === 12.5);
});

// ── 7. Schema composition: .pick() ──
test(".pick() selects specific fields", () => {
  const IdOnly = InsertResultSchema.pick({ id: true, namespace: true });
  const result = IdOnly.parse({ id: 99, namespace: "test" });
  assert(result.id === 99);
  assert(result.namespace === "test");
  // Extra fields should be stripped
  assert(result.success === undefined);
});

// ── 8. Schema composition: .omit() ──
test(".omit() removes specific fields", () => {
  const NoUpsert = InsertResultSchema.omit({ upserted: true });
  const result = NoUpsert.parse({ success: true, id: 1, namespace: "default" });
  assert(result.success === true);
  assert(result.upserted === undefined);
});

// ── 9. .partial() makes all fields optional ──
test(".partial() makes fields optional", () => {
  const PartialResult = InsertResultSchema.partial();
  const result = PartialResult.parse({ id: 5 });
  assert(result.id === 5);
  assert(result.success === undefined);
});

// ── 10. .merge() combines two schemas ──
test(".merge() combines schemas", () => {
  const Extra = z.object({ source: z.string() });
  const Merged = InsertResultSchema.merge(Extra);
  const result = Merged.parse({
    success: true,
    id: 1,
    namespace: "default",
    upserted: false,
    source: "api",
  });
  assert(result.source === "api");
  assert(result.success === true);
});

// ── 11. Positive int constraint on VectorEntry ──
test("VectorEntry rejects non-positive id", () => {
  let threw = false;
  try {
    VectorEntrySchema.parse({ id: -1, vector: [0.1] });
  } catch {
    threw = true;
  }
  assert(threw, "Should reject negative id");
});

test("VectorEntry accepts valid entry", () => {
  const entry = VectorEntrySchema.parse({
    id: 1,
    vector: [0.1, 0.2, 0.3],
    metadata: { title: "test" },
  });
  assert(entry.id === 1);
  assert(entry.vector.length === 3);
});

// ── 12. Array of SearchResults ──
test("z.array(SearchResultSchema) parses array", () => {
  const arr = z.array(SearchResultSchema).parse([
    { id: 1, score: 0.9 },
    { id: 2, score: 0.8, metadata: { a: 1 } },
  ]);
  assert(arr.length === 2);
});

// ── Summary ──
console.log(`\n  Results: ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
