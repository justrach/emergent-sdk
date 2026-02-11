"""
EmergentDB + OpenAI Embeddings Example
=======================================

Semantic search using OpenAI's text-embedding-3-small (1536-dim)
with EmergentDB as the vector store.

Requirements:
    pip install openai emergentdb

Environment variables:
    OPENAI_API_KEY   - Your OpenAI API key
    EMERGENTDB_KEY   - Your EmergentDB API key

Usage:
    python openai_embeddings.py
"""
import os
import sys

from openai import OpenAI
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from emergentdb import EmergentDB

# ── Config ────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMERGENTDB_KEY = os.environ.get("EMERGENTDB_KEY")

if not OPENAI_API_KEY:
    print("Set OPENAI_API_KEY environment variable")
    sys.exit(1)
if not EMERGENTDB_KEY:
    print("Set EMERGENTDB_KEY environment variable")
    sys.exit(1)

openai_client = OpenAI(api_key=OPENAI_API_KEY)
db = EmergentDB(EMERGENTDB_KEY)

NAMESPACE = "openai-example"

# ── Helper: generate embedding with OpenAI ────────────────────────
def embed(text: str) -> list[float]:
    """Generate a 1536-dim embedding using text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in one API call."""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


# ── Sample documents ──────────────────────────────────────────────
documents = [
    {"id": 7001, "title": "Python basics", "text": "Python is a high-level programming language known for its readability and simplicity. It supports multiple paradigms including procedural, object-oriented, and functional programming."},
    {"id": 7002, "title": "JavaScript overview", "text": "JavaScript is the language of the web. It runs in browsers and on servers via Node.js. It is essential for building interactive web applications and APIs."},
    {"id": 7003, "title": "Machine learning intro", "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. Common approaches include supervised, unsupervised, and reinforcement learning."},
    {"id": 7004, "title": "Database fundamentals", "text": "Databases store and organize data for efficient retrieval. SQL databases use structured tables while NoSQL databases offer flexible schemas for unstructured data."},
    {"id": 7005, "title": "Vector search explained", "text": "Vector search finds similar items by comparing high-dimensional embeddings. It powers semantic search, recommendation systems, and RAG pipelines by matching meaning rather than keywords."},
    {"id": 7006, "title": "REST API design", "text": "REST APIs use HTTP methods like GET, POST, PUT, and DELETE to perform CRUD operations. Good API design includes versioning, pagination, and proper error handling."},
    {"id": 7007, "title": "Cloud computing", "text": "Cloud computing provides on-demand access to computing resources like servers, storage, and databases over the internet. Major providers include AWS, Google Cloud, and Azure."},
    {"id": 7008, "title": "Neural networks", "text": "Neural networks are computing systems inspired by biological brains. They consist of layers of interconnected nodes that process information using weighted connections and activation functions."},
]

# ── Step 1: Embed and insert all documents ────────────────────────
print("\n=== EmergentDB + OpenAI text-embedding-3-small (1536-dim) ===\n")

print("1. Generating embeddings for documents...")
texts = [doc["text"] for doc in documents]
embeddings = embed_batch(texts)
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

print("\n3. Running semantic searches...\n")
for query in queries:
    query_embedding = embed(query)
    results = db.search(query_embedding, k=3, include_metadata=True, namespace=NAMESPACE)

    print(f'   Query: "{query}"')
    for i, r in enumerate(results.results):
        title = r.metadata.get("title", "?") if r.metadata else "?"
        print(f"     {i+1}. [{r.score:.4f}] {title}")
    print()

# ── Step 3: Cleanup ──────────────────────────────────────────────
print("4. Cleaning up...")
for doc in documents:
    db.delete(doc["id"], namespace=NAMESPACE)
print(f"   Deleted {len(documents)} vectors from '{NAMESPACE}'")

db.close()
print("\nDone!")
