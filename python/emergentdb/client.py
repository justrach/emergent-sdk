"""
EmergentDB Python SDK

Usage:
    from emergentdb import EmergentDB

    db = EmergentDB("emdb_your_api_key")

    # Insert
    db.insert(1, [0.1, 0.2, ...], metadata={"title": "Hello"})

    # Search
    results = db.search([0.1, 0.2, ...], k=5)

    # Namespaces
    db.insert(1, [0.1, ...], metadata={"title": "Prod"}, namespace="production")
    results = db.search([0.1, ...], namespace="production")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from dhi import BaseModel, Field


class EmergentDBError(Exception):
    """Raised when the EmergentDB API returns an error."""

    def __init__(self, message: str, status_code: int, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


# ── Response Models ────────────────────────────────────────────────


class InsertResult(BaseModel):
    success: bool
    id: int
    namespace: str = "default"
    upserted: bool = False


class BatchInsertResult(BaseModel):
    success: bool
    ids: List[int]
    count: int
    namespace: str = "default"
    new_count: int = 0
    upserted_count: int = 0


class SearchResult(BaseModel):
    id: int
    score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    count: int
    namespace: str = "default"


class DeleteResult(BaseModel):
    deleted: bool
    id: int
    namespace: str = "default"


# ── Analytics Models ──────────────────────────────────────────────


class EndpointStats(BaseModel):
    endpoint: str
    requestCount: Any = 0
    totalBytes: Any = 0
    avgLatencyMs: Any = 0
    p95LatencyMs: Any = 0
    errorCount: Any = 0


class NamespaceStats(BaseModel):
    namespace: Optional[str] = None
    requestCount: Any = 0
    totalVectors: Any = 0
    avgLatencyMs: Any = 0


class LatencyEntry(BaseModel):
    date: str
    p50: Any = 0
    p95: Any = 0
    p99: Any = 0
    requestCount: Any = 0


class ErrorEntry(BaseModel):
    date: str
    totalRequests: Any = 0
    errorCount: Any = 0
    error4xx: Any = 0
    error5xx: Any = 0


class KeyStats(BaseModel):
    apiKeyId: Optional[str] = None
    keyName: Optional[str] = None
    keyPrefix: Optional[str] = None
    requestCount: Any = 0
    totalBytes: Any = 0
    avgLatencyMs: Any = 0
    lastUsed: Optional[str] = None


class GrowthEntry(BaseModel):
    date: str
    vectorCount: Any = 0


# ── Client ─────────────────────────────────────────────────────────


class EmergentDB:
    """Client for the EmergentDB vector database API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.emergentdb.com",
        timeout: float = 30.0,
    ):
        if not api_key or not api_key.startswith("emdb_"):
            raise ValueError('API key must start with "emdb_"')

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "emergentdb-python/0.1.0",
            },
            timeout=timeout,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def _request(self, method: str, path: str, json: Any = None) -> Any:
        resp = self._client.request(method, path, json=json)
        data = resp.json()

        if resp.status_code >= 400:
            msg = data.get("error", f"HTTP {resp.status_code}")
            raise EmergentDBError(msg, resp.status_code, data)

        return data

    def insert(
        self,
        id: int,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> InsertResult:
        """
        Insert a single vector.

        Args:
            id: Positive integer ID (unique per namespace).
            vector: Embedding array.
            metadata: Optional metadata dict.
            namespace: Optional namespace (default: "default").

        Returns:
            InsertResult with success, id, namespace, upserted.
        """
        body: Dict[str, Any] = {"id": id, "vector": vector}
        if metadata:
            body["metadata"] = metadata
        if namespace and namespace != "default":
            body["namespace"] = namespace

        data = self._request("POST", "/vectors/insert", json=body)
        return InsertResult.model_validate(data)

    def batch_insert(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None,
    ) -> BatchInsertResult:
        """
        Batch insert up to 1000 vectors.

        Args:
            vectors: List of dicts with keys: id (int), vector (list), metadata (optional dict).
            namespace: Optional namespace for all vectors (default: "default").

        Returns:
            BatchInsertResult with ids, count, new_count, upserted_count.
        """
        if len(vectors) > 1000:
            raise ValueError("Batch insert supports max 1000 vectors per request")

        body: Dict[str, Any] = {"vectors": vectors}
        if namespace and namespace != "default":
            body["namespace"] = namespace

        data = self._request("POST", "/vectors/batch_insert", json=body)
        return BatchInsertResult.model_validate(data)

    def batch_insert_all(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Batch insert any number of vectors (auto-chunks into 1000-vector batches).

        Args:
            vectors: List of dicts with keys: id (int), vector (list), metadata (optional dict).
            namespace: Optional namespace for all vectors (default: "default").

        Returns:
            Dict with ids, count, new_count, upserted_count.
        """
        batch_size = 1000
        all_ids: List[int] = []
        total_new = 0
        total_upserted = 0

        for i in range(0, len(vectors), batch_size):
            chunk = vectors[i : i + batch_size]
            result = self.batch_insert(chunk, namespace=namespace)
            all_ids.extend(result.ids)
            total_new += result.new_count
            total_upserted += result.upserted_count

        return {
            "ids": all_ids,
            "count": len(all_ids),
            "new_count": total_new,
            "upserted_count": total_upserted,
        }

    def search(
        self,
        vector: List[float],
        k: int = 10,
        include_metadata: bool = False,
        namespace: Optional[str] = None,
    ) -> SearchResponse:
        """
        Search for similar vectors.

        Args:
            vector: Query embedding.
            k: Number of results (1-100, default 10).
            include_metadata: Include metadata in results.
            namespace: Optional namespace to search within (default: "default").

        Returns:
            SearchResponse with results list and count.
        """
        body: Dict[str, Any] = {
            "vector": vector,
            "k": k,
            "include_metadata": include_metadata,
        }
        if namespace and namespace != "default":
            body["namespace"] = namespace

        data = self._request("POST", "/vectors/search", json=body)
        return SearchResponse.model_validate(data)

    def delete(self, id: int, namespace: Optional[str] = None) -> DeleteResult:
        """
        Delete a vector by ID.

        Args:
            id: Vector ID to delete.
            namespace: Optional namespace (default: "default").

        Returns:
            DeleteResult with deleted status.
        """
        body: Dict[str, Any] = {"id": id}
        if namespace and namespace != "default":
            body["namespace"] = namespace

        data = self._request("POST", "/vectors/delete", json=body)
        return DeleteResult.model_validate(data)

    def list_namespaces(self) -> List[str]:
        """
        List all namespaces for the authenticated tenant.

        Returns:
            List of namespace name strings.
        """
        data = self._request("GET", "/vectors/namespaces")
        return data.get("namespaces", [])

    # ── Analytics Methods ─────────────────────────────────────────

    def analytics_endpoints(self) -> List[EndpointStats]:
        """Get request breakdown by endpoint (last 30 days)."""
        data = self._request("GET", "/api/dashboard/analytics/endpoints")
        return [EndpointStats.model_validate(e) for e in data.get("endpoints", [])]

    def analytics_namespaces(self) -> List[NamespaceStats]:
        """Get usage breakdown by namespace (last 30 days)."""
        data = self._request("GET", "/api/dashboard/analytics/namespaces")
        return [NamespaceStats.model_validate(n) for n in data.get("namespaces", [])]

    def analytics_latency(self) -> List[LatencyEntry]:
        """Get latency percentiles by day (last 30 days)."""
        data = self._request("GET", "/api/dashboard/analytics/latency")
        return [LatencyEntry.model_validate(l) for l in data.get("latency", [])]

    def analytics_errors(self) -> List[ErrorEntry]:
        """Get error rate breakdown by day (last 30 days)."""
        data = self._request("GET", "/api/dashboard/analytics/errors")
        return [ErrorEntry.model_validate(e) for e in data.get("errors", [])]

    def analytics_keys(self) -> List[KeyStats]:
        """Get per-API-key usage stats (last 30 days)."""
        data = self._request("GET", "/api/dashboard/analytics/keys")
        return [KeyStats.model_validate(k) for k in data.get("keys", [])]

    def analytics_growth(self) -> List[GrowthEntry]:
        """Get vector count growth over time (daily snapshots, last 90 days)."""
        data = self._request("GET", "/api/dashboard/analytics/growth")
        return [GrowthEntry.model_validate(g) for g in data.get("growth", [])]
