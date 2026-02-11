"""
Test: Can a user who uses Pydantic in their own app work with our SDK outputs?

Simulates real user workflows:
- They have their OWN Pydantic models in their app
- They call our SDK methods and get back typed model instances
- They want to feed our results into their own models, functions, pipelines
- They want to serialize, destructure, extend our models
"""

import json
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, ".")
from emergentdb import (
    InsertResult,
    BatchInsertResult,
    SearchResult,
    SearchResponse,
    DeleteResult,
)

# Try importing from dhi (what our SDK uses)
from dhi import BaseModel, Field

passed = 0
failed = 0


def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        print(f"  FAIL  {name}: {e}")


# ── Simulate API responses (what SDK methods return) ──
mock_insert = InsertResult.model_validate(
    {"success": True, "id": 42, "namespace": "production", "upserted": False}
)

mock_search = SearchResponse.model_validate(
    {
        "results": [
            {"id": 1, "score": 0.95, "metadata": {"title": "Doc A", "category": "science"}},
            {"id": 2, "score": 0.87, "metadata": {"title": "Doc B", "category": "math"}},
            {"id": 3, "score": 0.72},
        ],
        "count": 3,
        "namespace": "production",
    }
)

mock_batch = BatchInsertResult.model_validate(
    {
        "success": True,
        "ids": [1, 2, 3, 4, 5],
        "count": 5,
        "namespace": "default",
        "new_count": 3,
        "upserted_count": 2,
    }
)


print("\n=== User Workflow Tests: dhi SDK outputs in Pydantic pipelines ===\n")


# ── 1. User has their own Pydantic model and populates from SDK result ──
def test_user_model_from_sdk():
    class AppLogEntry(BaseModel):
        action: str
        vector_id: int
        namespace: str
        success: bool

    log = AppLogEntry(
        action="insert",
        vector_id=mock_insert.id,
        namespace=mock_insert.namespace,
        success=mock_insert.success,
    )
    assert log.vector_id == 42
    assert log.namespace == "production"
    assert log.success is True


test("User populates their Pydantic model from SDK result", test_user_model_from_sdk)


# ── 2. User filters search results ──
def test_filter_search():
    high_score = [r for r in mock_search.results if r.score > 0.8]
    titles = [r.metadata.get("title", "untitled") for r in high_score]
    assert len(high_score) == 2
    assert titles == ["Doc A", "Doc B"]


test("User filters search results with list comprehension", test_filter_search)


# ── 3. User validates SDK metadata with their own model ──
def test_validate_metadata():
    class DocMetadata(BaseModel):
        title: str
        category: str

    result = mock_search.results[0]
    validated = DocMetadata.model_validate(result.metadata)
    assert validated.title == "Doc A"
    assert validated.category == "science"


test("User validates SDK metadata with their own Pydantic model", test_validate_metadata)


# ── 4. User converts SDK result to dict and spreads into new dict ──
def test_dict_spread():
    data = mock_insert.model_dump()
    enriched = {**data, "source": "my-app", "inserted_at": 1234567890}
    assert enriched["id"] == 42
    assert enriched["namespace"] == "production"
    assert enriched["source"] == "my-app"


test("User spreads SDK model_dump() into custom dict", test_dict_spread)


# ── 5. User destructures SDK result via attribute access ──
def test_destructure():
    vid = mock_insert.id
    ns = mock_insert.namespace
    ups = mock_insert.upserted
    assert vid == 42
    assert ns == "production"
    assert ups is False


test("User accesses SDK result attributes directly", test_destructure)


# ── 6. User maps SDK results into their own DB model ──
def test_map_to_db_model():
    class DbRecord(BaseModel):
        external_id: int
        relevance_score: float
        title: str
        retrieved: bool = True

    records = [
        DbRecord(
            external_id=r.id,
            relevance_score=r.score,
            title=r.metadata.get("title", ""),
        )
        for r in mock_search.results
        if r.metadata
    ]
    assert len(records) == 2
    assert records[0].external_id == 1
    assert records[0].relevance_score == 0.95
    assert records[0].title == "Doc A"


test("User maps SDK search results into their own DB records", test_map_to_db_model)


# ── 7. User serializes SDK result to JSON for logging ──
def test_json_serialize():
    json_str = mock_insert.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["id"] == 42
    assert parsed["namespace"] == "production"


test("User serializes SDK result to JSON for logging", test_json_serialize)


# ── 8. User passes SDK result to their typed function ──
def test_typed_function():
    def process_insert(result: InsertResult) -> str:
        if result.upserted:
            return f"Updated vector {result.id}"
        return f"Inserted new vector {result.id} into {result.namespace}"

    msg = process_insert(mock_insert)
    assert msg == "Inserted new vector 42 into production"


test("User passes SDK result to their typed function", test_typed_function)


# ── 9. User uses batch IDs for downstream processing ──
def test_batch_downstream():
    ids = mock_batch.ids
    new_count = mock_batch.new_count
    needs_refresh = ids[:new_count]
    assert len(needs_refresh) == 3
    assert needs_refresh[0] == 1
    assert mock_batch.upserted_count == 2


test("User uses batch insert IDs for downstream pipeline", test_batch_downstream)


# ── 10. User stores results in a list and iterates ──
def test_accumulate():
    all_results: List[InsertResult] = []
    for i in range(1, 4):
        result = InsertResult.model_validate(
            {"success": True, "id": i, "namespace": "batch-test"}
        )
        all_results.append(result)

    assert len(all_results) == 3
    all_ids = [r.id for r in all_results]
    assert all_ids == [1, 2, 3]


test("User accumulates SDK results in a list", test_accumulate)


# ── 11. User wraps SDK response in their own API response ──
def test_wrap_api_response():
    class ApiResponse(BaseModel):
        status: str
        data: SearchResponse
        request_id: str

    response = ApiResponse(
        status="ok",
        data=mock_search,
        request_id="req_abc123",
    )
    assert response.data.results[0].id == 1
    assert response.request_id == "req_abc123"
    assert response.status == "ok"

    # Also verify serialization of nested SDK model
    d = response.model_dump()
    assert d["data"]["results"][0]["score"] == 0.95


test("User wraps SDK response in their own API response model", test_wrap_api_response)


# ── 12. User uses model_dump(exclude=...) to strip fields ──
def test_dump_exclude():
    d = mock_insert.model_dump(exclude={"upserted"})
    assert "upserted" not in d
    assert d["id"] == 42
    assert d["namespace"] == "production"


test("User uses model_dump(exclude=...) to strip fields", test_dump_exclude)


# ── 13. User compares two SDK results ──
def test_equality():
    a = InsertResult.model_validate({"success": True, "id": 1, "namespace": "default"})
    b = InsertResult.model_validate({"success": True, "id": 1, "namespace": "default"})
    assert a == b

    c = InsertResult.model_validate({"success": True, "id": 2, "namespace": "default"})
    assert a != c


test("User compares two SDK result instances", test_equality)


# ── 14. User converts SDK result for pandas / data processing ──
def test_tabular():
    rows = [
        {"id": r.id, "score": r.score, "has_metadata": r.metadata is not None}
        for r in mock_search.results
    ]
    assert len(rows) == 3
    assert rows[0]["score"] == 0.95
    assert rows[0]["has_metadata"] is True
    assert rows[2]["has_metadata"] is False


test("User converts SDK results to tabular dicts (for pandas/csv)", test_tabular)


# ── Summary ──
print(f"\n  Results: {passed} passed, {failed} failed\n")
if failed > 0:
    sys.exit(1)
