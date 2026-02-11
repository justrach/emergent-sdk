/**
 * EmergentDB TypeScript/JavaScript SDK
 *
 * @example
 * ```ts
 * import { EmergentDB } from "emergentdb";
 *
 * const db = new EmergentDB("emdb_your_api_key");
 *
 * // Insert
 * await db.insert(1, [0.1, 0.2, ...], { title: "Hello" });
 *
 * // Search
 * const results = await db.search([0.1, 0.2, ...], { k: 5 });
 *
 * // Namespaces
 * await db.insert(1, [0.1, ...], { title: "Prod doc" }, "production");
 * const prodResults = await db.search([0.1, ...], { namespace: "production" });
 * ```
 */

import { z } from "dhi";

// ── Response Schemas ──────────────────────────────────────────────

export const InsertResultSchema = z.object({
  success: z.boolean(),
  id: z.number().int(),
  namespace: z.string(),
  upserted: z.boolean(),
});
export type InsertResult = z.infer<typeof InsertResultSchema>;

export const BatchInsertResultSchema = z.object({
  success: z.boolean(),
  ids: z.array(z.number().int()),
  count: z.number().int(),
  namespace: z.string(),
  new_count: z.number().int(),
  upserted_count: z.number().int(),
});
export type BatchInsertResult = z.infer<typeof BatchInsertResultSchema>;

export const SearchResultSchema = z.object({
  id: z.number().int(),
  score: z.number(),
  metadata: z.record(z.string(), z.any()).optional(),
});
export type SearchResult = z.infer<typeof SearchResultSchema>;

export const SearchResponseSchema = z.object({
  results: z.array(SearchResultSchema),
  count: z.number().int(),
  namespace: z.string().default("default"),
});
export type SearchResponse = z.infer<typeof SearchResponseSchema>;

export const DeleteResultSchema = z.object({
  deleted: z.boolean(),
  id: z.number().int(),
  namespace: z.string(),
});
export type DeleteResult = z.infer<typeof DeleteResultSchema>;

export const NamespacesResponseSchema = z.object({
  namespaces: z.array(z.string()),
});
export type NamespacesResponse = z.infer<typeof NamespacesResponseSchema>;

// ── Analytics Response Schemas ───────────────────────────────────

export const EndpointStatsSchema = z.object({
  endpoint: z.string(),
  requestCount: z.union([z.string(), z.number()]),
  totalBytes: z.union([z.string(), z.number()]),
  avgLatencyMs: z.union([z.string(), z.number()]),
  p95LatencyMs: z.union([z.string(), z.number()]),
  errorCount: z.union([z.string(), z.number()]),
});
export type EndpointStats = z.infer<typeof EndpointStatsSchema>;

export const EndpointsResponseSchema = z.object({
  endpoints: z.array(EndpointStatsSchema),
});

export const NamespaceStatsSchema = z.object({
  namespace: z.string().nullable(),
  requestCount: z.union([z.string(), z.number()]),
  totalVectors: z.union([z.string(), z.number()]),
  avgLatencyMs: z.union([z.string(), z.number()]),
});
export type NamespaceStats = z.infer<typeof NamespaceStatsSchema>;

export const NamespaceAnalyticsResponseSchema = z.object({
  namespaces: z.array(NamespaceStatsSchema),
});

export const LatencyEntrySchema = z.object({
  date: z.string(),
  p50: z.union([z.string(), z.number()]),
  p95: z.union([z.string(), z.number()]),
  p99: z.union([z.string(), z.number()]),
  requestCount: z.union([z.string(), z.number()]),
});
export type LatencyEntry = z.infer<typeof LatencyEntrySchema>;

export const LatencyResponseSchema = z.object({
  latency: z.array(LatencyEntrySchema),
});

export const ErrorEntrySchema = z.object({
  date: z.string(),
  totalRequests: z.union([z.string(), z.number()]),
  errorCount: z.union([z.string(), z.number()]),
  error4xx: z.union([z.string(), z.number()]),
  error5xx: z.union([z.string(), z.number()]),
});
export type ErrorEntry = z.infer<typeof ErrorEntrySchema>;

export const ErrorsResponseSchema = z.object({
  errors: z.array(ErrorEntrySchema),
});

export const KeyStatsSchema = z.object({
  apiKeyId: z.string().nullable(),
  keyName: z.string().nullable(),
  keyPrefix: z.string().nullable(),
  requestCount: z.union([z.string(), z.number()]),
  totalBytes: z.union([z.string(), z.number()]),
  avgLatencyMs: z.union([z.string(), z.number()]),
  lastUsed: z.string().nullable(),
});
export type KeyStats = z.infer<typeof KeyStatsSchema>;

export const KeysResponseSchema = z.object({
  keys: z.array(KeyStatsSchema),
});

export const GrowthEntrySchema = z.object({
  date: z.string(),
  vectorCount: z.union([z.string(), z.number()]),
});
export type GrowthEntry = z.infer<typeof GrowthEntrySchema>;

export const GrowthResponseSchema = z.object({
  growth: z.array(GrowthEntrySchema),
});

// ── Input Schemas ─────────────────────────────────────────────────

export const SearchOptionsSchema = z.object({
  k: z.number().int().positive().lte(100).optional(),
  includeMetadata: z.boolean().optional(),
  namespace: z.string().max(64).optional(),
});
export type SearchOptions = z.infer<typeof SearchOptionsSchema>;

export const EmergentDBOptionsSchema = z.object({
  baseUrl: z.string().url().optional(),
});
export type EmergentDBOptions = z.infer<typeof EmergentDBOptionsSchema>;

export const VectorEntrySchema = z.object({
  id: z.number().int().positive(),
  vector: z.array(z.number()),
  metadata: z.record(z.string(), z.any()).optional(),
});
export type VectorEntry = z.infer<typeof VectorEntrySchema>;

// ── Error ─────────────────────────────────────────────────────────

export class EmergentDBError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: any,
  ) {
    super(message);
    this.name = "EmergentDBError";
  }
}

// ── Client ────────────────────────────────────────────────────────

export class EmergentDB {
  private apiKey: string;
  private baseUrl: string;

  constructor(apiKey: string, options?: EmergentDBOptions) {
    if (!apiKey || !apiKey.startsWith("emdb_")) {
      throw new Error('API key must start with "emdb_"');
    }
    this.apiKey = apiKey;
    this.baseUrl = options?.baseUrl ?? "https://api.emergentdb.com";
  }

  private async request<T>(
    method: string,
    path: string,
    schema: z.ZodType<T>,
    body?: any,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
      "Content-Type": "application/json",
      "User-Agent": "emergentdb-js/0.1.0",
    };

    const resp = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = (await resp.json()) as any;

    if (!resp.ok) {
      throw new EmergentDBError(
        data.error || `HTTP ${resp.status}`,
        resp.status,
        data,
      );
    }

    return schema.parse(data);
  }

  /**
   * Insert a single vector.
   *
   * @param id - Positive integer ID (unique per namespace)
   * @param vector - Embedding array
   * @param metadata - Optional metadata object
   * @param namespace - Optional namespace (default: "default")
   */
  async insert(
    id: number,
    vector: number[],
    metadata?: Record<string, any>,
    namespace?: string,
  ): Promise<InsertResult> {
    return this.request("POST", "/vectors/insert", InsertResultSchema, {
      id,
      vector,
      metadata,
      ...(namespace && namespace !== "default" ? { namespace } : {}),
    });
  }

  /**
   * Batch insert up to 1000 vectors.
   *
   * @param vectors - Array of {id, vector, metadata?} objects
   * @param namespace - Optional namespace for all vectors (default: "default")
   */
  async batchInsert(
    vectors: VectorEntry[],
    namespace?: string,
  ): Promise<BatchInsertResult> {
    if (vectors.length > 1000) {
      throw new Error("Batch insert supports max 1000 vectors per request");
    }

    return this.request(
      "POST",
      "/vectors/batch_insert",
      BatchInsertResultSchema,
      {
        vectors,
        ...(namespace && namespace !== "default" ? { namespace } : {}),
      },
    );
  }

  /**
   * Batch insert any number of vectors (auto-chunks into 1000-vector batches).
   *
   * @param vectors - Array of {id, vector, metadata?} objects (no limit)
   * @param namespace - Optional namespace for all vectors (default: "default")
   * @returns Combined results from all batches
   */
  async batchInsertAll(
    vectors: VectorEntry[],
    namespace?: string,
  ): Promise<{
    ids: number[];
    count: number;
    new_count: number;
    upserted_count: number;
  }> {
    const BATCH_SIZE = 1000;
    const allIds: number[] = [];
    let totalNew = 0;
    let totalUpserted = 0;

    for (let i = 0; i < vectors.length; i += BATCH_SIZE) {
      const chunk = vectors.slice(i, i + BATCH_SIZE);
      const result = await this.batchInsert(chunk, namespace);
      allIds.push(...result.ids);
      totalNew += result.new_count;
      totalUpserted += result.upserted_count;
    }

    return {
      ids: allIds,
      count: allIds.length,
      new_count: totalNew,
      upserted_count: totalUpserted,
    };
  }

  /**
   * Search for similar vectors.
   *
   * @param vector - Query embedding
   * @param options - Search options (k, includeMetadata, namespace)
   */
  async search(
    vector: number[],
    options?: SearchOptions,
  ): Promise<SearchResponse> {
    return this.request("POST", "/vectors/search", SearchResponseSchema, {
      vector,
      k: options?.k ?? 10,
      include_metadata: options?.includeMetadata ?? false,
      ...(options?.namespace && options.namespace !== "default"
        ? { namespace: options.namespace }
        : {}),
    });
  }

  /**
   * Delete a vector by ID.
   *
   * @param id - Vector ID to delete
   * @param namespace - Optional namespace (default: "default")
   */
  async delete(id: number, namespace?: string): Promise<DeleteResult> {
    return this.request("POST", "/vectors/delete", DeleteResultSchema, {
      id,
      ...(namespace && namespace !== "default" ? { namespace } : {}),
    });
  }

  /**
   * List all namespaces for the authenticated tenant.
   */
  async listNamespaces(): Promise<string[]> {
    const resp = await this.request(
      "GET",
      "/vectors/namespaces",
      NamespacesResponseSchema,
    );
    return resp.namespaces;
  }

  // ── Analytics Methods ────────────────────────────────────────────

  /**
   * Get request breakdown by endpoint (last 30 days).
   */
  async analyticsEndpoints(): Promise<EndpointStats[]> {
    const resp = await this.request(
      "GET",
      "/api/dashboard/analytics/endpoints",
      EndpointsResponseSchema,
    );
    return resp.endpoints;
  }

  /**
   * Get usage breakdown by namespace (last 30 days).
   */
  async analyticsNamespaces(): Promise<NamespaceStats[]> {
    const resp = await this.request(
      "GET",
      "/api/dashboard/analytics/namespaces",
      NamespaceAnalyticsResponseSchema,
    );
    return resp.namespaces;
  }

  /**
   * Get latency percentiles by day (last 30 days).
   */
  async analyticsLatency(): Promise<LatencyEntry[]> {
    const resp = await this.request(
      "GET",
      "/api/dashboard/analytics/latency",
      LatencyResponseSchema,
    );
    return resp.latency;
  }

  /**
   * Get error rate breakdown by day (last 30 days).
   */
  async analyticsErrors(): Promise<ErrorEntry[]> {
    const resp = await this.request(
      "GET",
      "/api/dashboard/analytics/errors",
      ErrorsResponseSchema,
    );
    return resp.errors;
  }

  /**
   * Get per-API-key usage stats (last 30 days).
   */
  async analyticsKeys(): Promise<KeyStats[]> {
    const resp = await this.request(
      "GET",
      "/api/dashboard/analytics/keys",
      KeysResponseSchema,
    );
    return resp.keys;
  }

  /**
   * Get vector count growth over time (daily snapshots, last 90 days).
   */
  async analyticsGrowth(): Promise<GrowthEntry[]> {
    const resp = await this.request(
      "GET",
      "/api/dashboard/analytics/growth",
      GrowthResponseSchema,
    );
    return resp.growth;
  }
}

export default EmergentDB;
