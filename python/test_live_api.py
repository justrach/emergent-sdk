"""
Live API test using the EmergentDB Python SDK.
Tests insert, search, namespaces, delete against the production API.
Bolt is configured for 1536-dim vectors.
"""
import os
import random
import sys
sys.path.insert(0, ".")
from emergentdb import EmergentDB

API_KEY = os.environ.get("EMERGENTDB_API_KEY")
if not API_KEY:
    print("ERROR: EMERGENTDB_API_KEY environment variable is required")
    sys.exit(1)
DIM = 1536  # Bolt is configured for 1536-dim (OpenAI ada-002)

def rand_vec(seed=None):
    """Generate a random 1536-dim vector."""
    if seed is not None:
        random.seed(seed)
    return [random.uniform(-0.1, 0.1) for _ in range(DIM)]

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        result = fn()
        passed += 1
        print(f"  PASS  {name}")
        if result:
            print(f"        -> {result}")
    except Exception as e:
        failed += 1
        print(f"  FAIL  {name}: {e}")

db = EmergentDB(API_KEY)

print("\n=== Live API Test with Python SDK (1536-dim) ===\n")

# ── 1. Insert into default namespace ──
def test_insert_default():
    result = db.insert(100, rand_vec(seed=42), metadata={"title": "SDK test doc"})
    assert result.success, f"Insert failed: {result}"
    assert result.id == 100
    assert result.namespace == "default"
    return f"id={result.id}, ns={result.namespace}, upserted={result.upserted}"
test("Insert vector into default namespace", test_insert_default)

# ── 2. Insert into "sdk-test" namespace ──
def test_insert_ns():
    result = db.insert(1, rand_vec(seed=1), metadata={"title": "Namespace doc 1"}, namespace="sdk-test")
    assert result.success
    assert result.namespace == "sdk-test"
    return f"id={result.id}, ns={result.namespace}"
test("Insert vector into sdk-test namespace", test_insert_ns)

# ── 3. Insert another into "sdk-test" ──
def test_insert_ns2():
    result = db.insert(2, rand_vec(seed=2), metadata={"title": "Namespace doc 2"}, namespace="sdk-test")
    assert result.success
    return f"id={result.id}, ns={result.namespace}"
test("Insert second vector into sdk-test namespace", test_insert_ns2)

# ── 4. Search in "sdk-test" ──
def test_search_ns():
    result = db.search(rand_vec(seed=1), k=5, include_metadata=True, namespace="sdk-test")
    assert result.namespace == "sdk-test"
    assert result.count > 0, "Expected results in sdk-test namespace"
    return f"{result.count} results: {[{'id': r.id, 'score': round(r.score, 4), 'meta': r.metadata} for r in result.results]}"
test("Search in sdk-test namespace", test_search_ns)

# ── 5. Search in default namespace — IDOR check ──
def test_search_default():
    result = db.search(rand_vec(seed=1), k=5, include_metadata=True)
    ids = [r.id for r in result.results]
    assert 1 not in ids, f"IDOR: sdk-test vector 1 leaked into default namespace! ids={ids}"
    assert 2 not in ids, f"IDOR: sdk-test vector 2 leaked into default namespace! ids={ids}"
    return f"{result.count} results, ids={ids}"
test("Search in default namespace (IDOR check)", test_search_default)

# ── 6. List namespaces ──
def test_list_ns():
    namespaces = db.list_namespaces()
    assert isinstance(namespaces, list)
    return f"namespaces: {namespaces}"
test("List namespaces", test_list_ns)

# ── 7. Upsert — re-insert same ID with new metadata ──
def test_upsert():
    result = db.insert(1, rand_vec(seed=10), metadata={"title": "Updated doc 1"}, namespace="sdk-test")
    assert result.success
    assert result.upserted, f"Expected upserted=True, got {result.upserted}"
    return f"upserted={result.upserted}"
test("Upsert vector in sdk-test namespace", test_upsert)

# ── 8. Delete from sdk-test namespace ──
def test_delete_ns():
    r1 = db.delete(1, namespace="sdk-test")
    assert r1.deleted
    r2 = db.delete(2, namespace="sdk-test")
    assert r2.deleted
    return "deleted ids 1,2 from sdk-test"
test("Delete vectors from sdk-test namespace", test_delete_ns)

# ── 9. Delete from default namespace ──
def test_delete_default():
    r = db.delete(100)
    assert r.deleted
    return "deleted id 100 from default"
test("Delete vector from default namespace", test_delete_default)

# ── 10. Verify deletion ──
def test_verify_deleted():
    result = db.search(rand_vec(seed=1), k=5, namespace="sdk-test")
    assert result.count == 0, f"Expected 0 results after delete, got {result.count}"
    return "0 results (correct)"
test("Verify sdk-test namespace is empty after delete", test_verify_deleted)

db.close()

print(f"\n  Results: {passed} passed, {failed} failed\n")
if failed > 0:
    sys.exit(1)
