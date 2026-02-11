/**
 * EmergentDB + Gemini Embeddings Example
 * ========================================
 *
 * Semantic search using Google's gemini-embedding-001 (1536-dim)
 * with EmergentDB as the vector store.
 *
 * Gemini supports task types for optimized embeddings:
 *   - RETRIEVAL_DOCUMENT: for documents to be indexed
 *   - RETRIEVAL_QUERY: for search queries
 *   - SEMANTIC_SIMILARITY: for comparing text similarity
 *   - CLASSIFICATION, CLUSTERING, etc.
 *
 * Gemini also supports output_dimensionality (768, 1536, 3072)
 * via Matryoshka Representation Learning (MRL).
 *
 * Requirements:
 *   npm install @google/genai emergentdb
 *
 * Environment variables:
 *   GEMINI_API_KEY   - Your Gemini API key
 *   EMERGENTDB_KEY   - Your EmergentDB API key
 *
 * Usage:
 *   node gemini-embeddings.mjs
 */

import { GoogleGenAI } from "@google/genai";
import { EmergentDB } from "../dist/index.mjs";

// ── Config ───────────────────────────────────────────────────────
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const EMERGENTDB_KEY = process.env.EMERGENTDB_KEY;

if (!GEMINI_API_KEY) { console.error("Set GEMINI_API_KEY environment variable"); process.exit(1); }
if (!EMERGENTDB_KEY) { console.error("Set EMERGENTDB_KEY environment variable"); process.exit(1); }

const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
const db = new EmergentDB(EMERGENTDB_KEY);

const NAMESPACE = "gemini-example";
const DIM = 1536; // Matches Bolt's configured dimensionality

// ── Helper: normalize + generate embeddings with Gemini ─────────

function normalize(vec) {
  /** L2-normalize a vector. Required for Gemini embeddings at non-3072 dims. */
  let norm = 0;
  for (let i = 0; i < vec.length; i++) norm += vec[i] * vec[i];
  norm = Math.sqrt(norm);
  if (norm === 0) return vec;
  return vec.map(v => v / norm);
}

async function embedDocuments(texts) {
  /** Embed documents using RETRIEVAL_DOCUMENT task type at 1536-dim. */
  const response = await ai.models.embedContent({
    model: "gemini-embedding-001",
    contents: texts,
    config: {
      taskType: "RETRIEVAL_DOCUMENT",
      outputDimensionality: DIM,
    },
  });
  // Gemini 1536-dim embeddings are NOT pre-normalized (only 3072 are).
  // Normalize so inner_product == cosine similarity.
  return response.embeddings.map(e => normalize(e.values));
}

async function embedQuery(text) {
  /** Embed a search query using RETRIEVAL_QUERY task type at 1536-dim. */
  const response = await ai.models.embedContent({
    model: "gemini-embedding-001",
    contents: text,
    config: {
      taskType: "RETRIEVAL_QUERY",
      outputDimensionality: DIM,
    },
  });
  return normalize(response.embeddings[0].values);
}

// ── Cosine similarity helper ────────────────────────────────────
function cosineSim(a, b) {
  let dot = 0, magA = 0, magB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    magA += a[i] * a[i];
    magB += b[i] * b[i];
  }
  return dot / (Math.sqrt(magA) * Math.sqrt(magB));
}

// ── Sample documents ─────────────────────────────────────────────
const documents = [
  { id: 5001, title: "Python basics", text: "Python is a high-level programming language known for its readability and simplicity. It supports multiple paradigms including procedural, object-oriented, and functional programming." },
  { id: 5002, title: "JavaScript overview", text: "JavaScript is the language of the web. It runs in browsers and on servers via Node.js. It is essential for building interactive web applications and APIs." },
  { id: 5003, title: "Machine learning intro", text: "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. Common approaches include supervised, unsupervised, and reinforcement learning." },
  { id: 5004, title: "Database fundamentals", text: "Databases store and organize data for efficient retrieval. SQL databases use structured tables while NoSQL databases offer flexible schemas for unstructured data." },
  { id: 5005, title: "Vector search explained", text: "Vector search finds similar items by comparing high-dimensional embeddings. It powers semantic search, recommendation systems, and RAG pipelines by matching meaning rather than keywords." },
  { id: 5006, title: "REST API design", text: "REST APIs use HTTP methods like GET, POST, PUT, and DELETE to perform CRUD operations. Good API design includes versioning, pagination, and proper error handling." },
  { id: 5007, title: "Cloud computing", text: "Cloud computing provides on-demand access to computing resources like servers, storage, and databases over the internet. Major providers include AWS, Google Cloud, and Azure." },
  { id: 5008, title: "Neural networks", text: "Neural networks are computing systems inspired by biological brains. They consist of layers of interconnected nodes that process information using weighted connections and activation functions." },
];

// ── Step 1: Embed and insert all documents ───────────────────────
console.log("\n=== EmergentDB + Gemini gemini-embedding-001 (1536-dim) ===\n");

console.log("1. Generating embeddings for documents...");
console.log("   Using taskType=RETRIEVAL_DOCUMENT, outputDimensionality=1536");
const texts = documents.map(d => d.text);
const embeddings = await embedDocuments(texts);
console.log(`   Generated ${embeddings.length} embeddings, each ${embeddings[0].length}-dim`);

console.log("2. Inserting vectors into EmergentDB...");
for (let i = 0; i < documents.length; i++) {
  await db.insert(
    documents[i].id,
    embeddings[i],
    { title: documents[i].title, text: documents[i].text },
    NAMESPACE,
  );
}
console.log(`   Inserted ${documents.length} vectors into '${NAMESPACE}' namespace`);

// ── Step 2: Semantic search using RETRIEVAL_QUERY ────────────────
const queries = [
  "How do I build a web app?",
  "What is AI and how does it learn?",
  "How to store and query data efficiently?",
];

console.log("\n3. Running semantic searches...");
console.log("   Using taskType=RETRIEVAL_QUERY for queries\n");
for (const query of queries) {
  const queryEmbedding = await embedQuery(query);
  const results = await db.search(queryEmbedding, { k: 3, includeMetadata: true, namespace: NAMESPACE });

  console.log(`   Query: "${query}"`);
  results.results.forEach((r, i) => {
    const title = r.metadata?.title ?? "?";
    console.log(`     ${i + 1}. [${r.score.toFixed(4)}] ${title}`);
  });
  console.log();
}

// ── Step 3: Semantic similarity (bonus) ──────────────────────────
console.log("4. Semantic similarity demo...");
console.log("   Using taskType=SEMANTIC_SIMILARITY\n");

const similarityTexts = [
  "What is the meaning of life?",
  "What is the purpose of existence?",
  "How do I bake a cake?",
];

const simResponse = await ai.models.embedContent({
  model: "gemini-embedding-001",
  contents: similarityTexts,
  config: {
    taskType: "SEMANTIC_SIMILARITY",
    outputDimensionality: DIM,
  },
});
const simEmbeddings = simResponse.embeddings.map(e => e.values);

for (let i = 0; i < similarityTexts.length; i++) {
  for (let j = i + 1; j < similarityTexts.length; j++) {
    const sim = cosineSim(simEmbeddings[i], simEmbeddings[j]);
    console.log(`   "${similarityTexts[i]}" <-> "${similarityTexts[j]}"`);
    console.log(`     Cosine similarity: ${sim.toFixed(4)}\n`);
  }
}

// ── Step 4: Cleanup ──────────────────────────────────────────────
console.log("5. Cleaning up...");
for (const doc of documents) {
  await db.delete(doc.id, NAMESPACE);
}
console.log(`   Deleted ${documents.length} vectors from '${NAMESPACE}'`);

console.log("\nDone!");
