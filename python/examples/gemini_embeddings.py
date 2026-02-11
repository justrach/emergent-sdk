"""
EmergentDB + Gemini Embeddings Example
=======================================

Semantic search using Google's gemini-embedding-001 (1536-dim)
with EmergentDB as the vector store.

The Gemini embedding model supports output_dimensionality to control
embedding size. We use 1536 dimensions to match EmergentDB's Bolt config.

Gemini also supports task types for optimized embeddings:
  - RETRIEVAL_DOCUMENT: for documents to be indexed
  - RETRIEVAL_QUERY: for search queries
  - SEMANTIC_SIMILARITY: for comparing text similarity
  - CLASSIFICATION, CLUSTERING, etc.

Requirements:
    pip install google-genai emergentdb

Environment variables:
    GEMINI_API_KEY   - Your Gemini API key
    EMERGENTDB_KEY   - Your EmergentDB API key

Usage:
    python gemini_embeddings.py
"""
import os
import sys

from google import genai
from google.genai import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from emergentdb import EmergentDB

# ── Config ────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EMERGENTDB_KEY = os.environ.get("EMERGENTDB_KEY")

if not GEMINI_API_KEY:
    print("Set GEMINI_API_KEY environment variable")
    sys.exit(1)
if not EMERGENTDB_KEY:
    print("Set EMERGENTDB_KEY environment variable")
    sys.exit(1)

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
db = EmergentDB(EMERGENTDB_KEY)

NAMESPACE = "gemini-example"
DIM = 1536  # Matches Bolt's configured dimensionality

# ── Helper: normalize + generate embeddings with Gemini ───────────
def normalize(vec: list[float]) -> list[float]:
    """L2-normalize a vector. Required for Gemini embeddings at non-3072 dims."""
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec] if norm > 0 else vec


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed documents using RETRIEVAL_DOCUMENT task type at 1536-dim."""
    result = gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=DIM,
        ),
    )
    # Gemini 1536-dim embeddings are NOT pre-normalized (only 3072 are).
    # Normalize so inner_product == cosine similarity.
    return [normalize(e.values) for e in result.embeddings]


def embed_query(text: str) -> list[float]:
    """Embed a search query using RETRIEVAL_QUERY task type at 1536-dim."""
    result = gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=DIM,
        ),
    )
    return normalize(result.embeddings[0].values)


# ── Sample documents ──────────────────────────────────────────────
documents = [
    {"id": 6001, "title": "Python basics", "text": "Python is a high-level programming language known for its readability and simplicity. It supports multiple paradigms including procedural, object-oriented, and functional programming."},
    {"id": 6002, "title": "JavaScript overview", "text": "JavaScript is the language of the web. It runs in browsers and on servers via Node.js. It is essential for building interactive web applications and APIs."},
    {"id": 6003, "title": "Machine learning intro", "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. Common approaches include supervised, unsupervised, and reinforcement learning."},
    {"id": 6004, "title": "Database fundamentals", "text": "Databases store and organize data for efficient retrieval. SQL databases use structured tables while NoSQL databases offer flexible schemas for unstructured data."},
    {"id": 6005, "title": "Vector search explained", "text": "Vector search finds similar items by comparing high-dimensional embeddings. It powers semantic search, recommendation systems, and RAG pipelines by matching meaning rather than keywords."},
    {"id": 6006, "title": "REST API design", "text": "REST APIs use HTTP methods like GET, POST, PUT, and DELETE to perform CRUD operations. Good API design includes versioning, pagination, and proper error handling."},
    {"id": 6007, "title": "Cloud computing", "text": "Cloud computing provides on-demand access to computing resources like servers, storage, and databases over the internet. Major providers include AWS, Google Cloud, and Azure."},
    {"id": 6008, "title": "Neural networks", "text": "Neural networks are computing systems inspired by biological brains. They consist of layers of interconnected nodes that process information using weighted connections and activation functions."},
]

# ── Step 1: Embed and insert all documents ────────────────────────
print("\n=== EmergentDB + Gemini gemini-embedding-001 (1536-dim) ===\n")

print("1. Generating embeddings for documents...")
print("   Using task_type=RETRIEVAL_DOCUMENT, output_dimensionality=1536")
texts = [doc["text"] for doc in documents]
embeddings = embed_documents(texts)
print(f"   Generated {len(embeddings)} embeddings, each {len(embeddings[0])}-dim")

print("2. Inserting vectors into EmergentDB...")
for doc, emb in zip(documents, embeddings):
    db.insert(doc["id"], emb, metadata={"title": doc["title"], "text": doc["text"]}, namespace=NAMESPACE)
print(f"   Inserted {len(documents)} vectors into '{NAMESPACE}' namespace")

# ── Step 2: Semantic search ───────────────────────────────────────
queries = [
    "How do I build a web app?",
    "What is AI and how does it learn?",
    "How to store and query data efficiently?",
]

print("\n3. Running semantic searches...")
print("   Using task_type=RETRIEVAL_QUERY for queries\n")
for query in queries:
    query_embedding = embed_query(query)
    results = db.search(query_embedding, k=3, include_metadata=True, namespace=NAMESPACE)

    print(f'   Query: "{query}"')
    for i, r in enumerate(results.results):
        title = r.metadata.get("title", "?") if r.metadata else "?"
        print(f"     {i+1}. [{r.score:.4f}] {title}")
    print()

# ── Step 3: Semantic similarity (bonus) ──────────────────────────
print("4. Semantic similarity demo...")
print("   Using task_type=SEMANTIC_SIMILARITY\n")

similarity_texts = [
    "What is the meaning of life?",
    "What is the purpose of existence?",
    "How do I bake a cake?",
]

sim_result = gemini_client.models.embed_content(
    model="gemini-embedding-001",
    contents=similarity_texts,
    config=types.EmbedContentConfig(
        task_type="SEMANTIC_SIMILARITY",
        output_dimensionality=DIM,
    ),
)
sim_embeddings = [e.values for e in sim_result.embeddings]

# Compute cosine similarity
def cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0

for i in range(len(similarity_texts)):
    for j in range(i + 1, len(similarity_texts)):
        sim = cosine_sim(sim_embeddings[i], sim_embeddings[j])
        print(f'   "{similarity_texts[i]}" <-> "{similarity_texts[j]}"')
        print(f"     Cosine similarity: {sim:.4f}\n")

# ── Step 4: Cleanup ──────────────────────────────────────────────
print("5. Cleaning up...")
for doc in documents:
    db.delete(doc["id"], namespace=NAMESPACE)
print(f"   Deleted {len(documents)} vectors from '{NAMESPACE}'")

db.close()
print("\nDone!")
