/**
 * EmergentDB + OpenAI Embeddings Example
 * ========================================
 *
 * Semantic search using OpenAI's text-embedding-3-small (1536-dim)
 * with EmergentDB as the vector store.
 *
 * Requirements:
 *   npm install openai emergentdb
 *
 * Environment variables:
 *   OPENAI_API_KEY   - Your OpenAI API key
 *   EMERGENTDB_KEY   - Your EmergentDB API key
 *
 * Usage:
 *   node openai-embeddings.mjs
 */

import OpenAI from "openai";
import { EmergentDB } from "../dist/index.mjs";

// ── Config ───────────────────────────────────────────────────────
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const EMERGENTDB_KEY = process.env.EMERGENTDB_KEY;

if (!OPENAI_API_KEY) { console.error("Set OPENAI_API_KEY environment variable"); process.exit(1); }
if (!EMERGENTDB_KEY) { console.error("Set EMERGENTDB_KEY environment variable"); process.exit(1); }

const openai = new OpenAI({ apiKey: OPENAI_API_KEY });
const db = new EmergentDB(EMERGENTDB_KEY);

const NAMESPACE = "openai-example";

// ── Helper: generate embeddings with OpenAI ──────────────────────

async function embed(text) {
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: text,
  });
  return response.data[0].embedding;
}

async function embedBatch(texts) {
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: texts,
  });
  return response.data.map(item => item.embedding);
}

// ── Sample documents ─────────────────────────────────────────────
const documents = [
  { id: 8001, title: "Python basics", text: "Python is a high-level programming language known for its readability and simplicity. It supports multiple paradigms including procedural, object-oriented, and functional programming." },
  { id: 8002, title: "JavaScript overview", text: "JavaScript is the language of the web. It runs in browsers and on servers via Node.js. It is essential for building interactive web applications and APIs." },
  { id: 8003, title: "Machine learning intro", text: "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. Common approaches include supervised, unsupervised, and reinforcement learning." },
  { id: 8004, title: "Database fundamentals", text: "Databases store and organize data for efficient retrieval. SQL databases use structured tables while NoSQL databases offer flexible schemas for unstructured data." },
  { id: 8005, title: "Vector search explained", text: "Vector search finds similar items by comparing high-dimensional embeddings. It powers semantic search, recommendation systems, and RAG pipelines by matching meaning rather than keywords." },
  { id: 8006, title: "REST API design", text: "REST APIs use HTTP methods like GET, POST, PUT, and DELETE to perform CRUD operations. Good API design includes versioning, pagination, and proper error handling." },
  { id: 8007, title: "Cloud computing", text: "Cloud computing provides on-demand access to computing resources like servers, storage, and databases over the internet. Major providers include AWS, Google Cloud, and Azure." },
  { id: 8008, title: "Neural networks", text: "Neural networks are computing systems inspired by biological brains. They consist of layers of interconnected nodes that process information using weighted connections and activation functions." },
];

// ── Step 1: Embed and insert ─────────────────────────────────────
console.log("\n=== EmergentDB + OpenAI text-embedding-3-small (1536-dim) ===\n");

console.log("1. Generating embeddings for documents...");
const texts = documents.map(d => d.text);
const embeddings = await embedBatch(texts);
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

// ── Step 2: Semantic search ──────────────────────────────────────
const queries = [
  "How do I build a web app?",
  "What is AI and how does it learn?",
  "How to store and query data efficiently?",
];

console.log("\n3. Running semantic searches...\n");
for (const query of queries) {
  const queryEmbedding = await embed(query);
  const results = await db.search(queryEmbedding, { k: 3, includeMetadata: true, namespace: NAMESPACE });

  console.log(`   Query: "${query}"`);
  results.results.forEach((r, i) => {
    const title = r.metadata?.title ?? "?";
    console.log(`     ${i + 1}. [${r.score.toFixed(4)}] ${title}`);
  });
  console.log();
}

// ── Step 3: Cleanup ──────────────────────────────────────────────
console.log("4. Cleaning up...");
for (const doc of documents) {
  await db.delete(doc.id, NAMESPACE);
}
console.log(`   Deleted ${documents.length} vectors from '${NAMESPACE}'`);

console.log("\nDone!");
