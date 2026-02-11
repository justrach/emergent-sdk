"""
Test: dhi models are compatible with Pydantic workflows

Users who use Pydantic in their app should be able to:
1. Use model_validate() / model_dump() / model_dump_json()
2. Use model_json_schema() for JSON Schema generation
3. Inherit/extend our models
4. Use Field constraints
5. Use .model_fields to introspect
6. Mix with their own Pydantic models
"""

import json
import sys
from typing import Any, Dict, List, Optional

# Simulate what a user would do: import from emergentdb
sys.path.insert(0, ".")
from emergentdb import (
    InsertResult,
    BatchInsertResult,
    SearchResult,
    SearchResponse,
    DeleteResult,
)


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


print("\n=== dhi <> Pydantic Compatibility Tests (Python SDK) ===\n")


# ── 1. model_validate() on valid data ──
def test_model_validate():
    result = InsertResult.model_validate(
        {"success": True, "id": 42, "namespace": "default", "upserted": False}
    )
    assert result.success is True
    assert result.id == 42
    assert result.namespace == "default"


test("model_validate() accepts valid InsertResult", test_model_validate)


# ── 2. model_validate() rejects bad data ──
def test_model_validate_reject():
    threw = False
    try:
        InsertResult.model_validate({"success": "yes", "id": "abc"})
    except Exception:
        threw = True
    assert threw, "Should have thrown on invalid data"


test("model_validate() rejects invalid data", test_model_validate_reject)


# ── 3. model_dump() returns dict ──
def test_model_dump():
    result = InsertResult(success=True, id=1, namespace="prod", upserted=True)
    d = result.model_dump()
    assert isinstance(d, dict)
    assert d["success"] is True
    assert d["id"] == 1
    assert d["namespace"] == "prod"
    assert d["upserted"] is True


test("model_dump() returns dict", test_model_dump)


# ── 4. model_dump_json() returns JSON string ──
def test_model_dump_json():
    result = InsertResult(success=True, id=1, namespace="default", upserted=False)
    j = result.model_dump_json()
    assert isinstance(j, str)
    data = json.loads(j)
    assert data["success"] is True
    assert data["id"] == 1


test("model_dump_json() returns valid JSON", test_model_dump_json)


# ── 5. Default values work ──
def test_defaults():
    # namespace and upserted have defaults
    result = InsertResult.model_validate({"success": True, "id": 5})
    assert result.namespace == "default"
    assert result.upserted is False


test("Default field values work", test_defaults)


# ── 6. Nested model validation (SearchResponse with List[SearchResult]) ──
def test_nested():
    resp = SearchResponse.model_validate(
        {
            "results": [
                {"id": 1, "score": 0.95, "metadata": {"title": "hello"}},
                {"id": 2, "score": 0.87},
            ],
            "count": 2,
            "namespace": "default",
        }
    )
    assert len(resp.results) == 2
    assert resp.results[0].score == 0.95
    assert resp.results[0].metadata == {"title": "hello"}
    assert resp.results[1].metadata is None


test("Nested model validation (SearchResponse)", test_nested)


# ── 7. model_json_schema() generates JSON Schema ──
def test_json_schema():
    schema = InsertResult.model_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "success" in schema["properties"]
    assert "id" in schema["properties"]


test("model_json_schema() generates valid schema", test_json_schema)


# ── 8. Model inheritance/extension ──
def test_inheritance():
    class ExtendedResult(InsertResult):
        latency_ms: float = 0.0

    result = ExtendedResult.model_validate(
        {
            "success": True,
            "id": 1,
            "namespace": "default",
            "upserted": False,
            "latency_ms": 12.5,
        }
    )
    assert result.latency_ms == 12.5
    assert result.success is True


test("Model inheritance/extension works", test_inheritance)


# ── 9. model_fields introspection ──
def test_model_fields():
    fields = InsertResult.model_fields
    assert "success" in fields
    assert "id" in fields
    assert "namespace" in fields
    assert "upserted" in fields


test("model_fields introspection", test_model_fields)


# ── 10. Attribute access on model instances ──
def test_attribute_access():
    result = SearchResult(id=1, score=0.95, metadata={"tag": "a"})
    assert result.id == 1
    assert result.score == 0.95
    assert result.metadata == {"tag": "a"}


test("Attribute access on model instances", test_attribute_access)


# ── 11. BatchInsertResult with all fields ──
def test_batch_insert():
    result = BatchInsertResult.model_validate(
        {
            "success": True,
            "ids": [1, 2, 3],
            "count": 3,
            "namespace": "test-ns",
            "new_count": 2,
            "upserted_count": 1,
        }
    )
    assert result.ids == [1, 2, 3]
    assert result.count == 3
    assert result.namespace == "test-ns"
    assert result.new_count == 2
    assert result.upserted_count == 1


test("BatchInsertResult with all fields", test_batch_insert)


# ── 12. DeleteResult model ──
def test_delete():
    result = DeleteResult.model_validate(
        {"deleted": True, "id": 99, "namespace": "cleanup"}
    )
    assert result.deleted is True
    assert result.id == 99
    assert result.namespace == "cleanup"


test("DeleteResult model", test_delete)


# ── 13. model_validate from JSON string ──
def test_validate_json():
    json_str = '{"success": true, "id": 1, "namespace": "default", "upserted": false}'
    result = InsertResult.model_validate_json(json_str)
    assert result.success is True
    assert result.id == 1


test("model_validate_json() from JSON string", test_validate_json)


# ── 14. Can use models as type hints in user code ──
def test_type_hint():
    def process_results(response: SearchResponse) -> List[int]:
        return [r.id for r in response.results]

    resp = SearchResponse(
        results=[SearchResult(id=1, score=0.9), SearchResult(id=2, score=0.8)],
        count=2,
        namespace="default",
    )
    ids = process_results(resp)
    assert ids == [1, 2]


test("Models work as type hints", test_type_hint)


# ── Summary ──
print(f"\n  Results: {passed} passed, {failed} failed\n")
if failed > 0:
    sys.exit(1)
