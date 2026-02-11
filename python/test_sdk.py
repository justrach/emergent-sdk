"""
Live API test for the EmergentDB Python SDK.
Tests all SDK methods against production: insert, search, delete,
batch insert, namespaces, upsert, and analytics endpoints.
Bolt is configured for 1536-dim vectors.

Run: python test_sdk.py
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
DIM = 1536


def rand_vec(seed=0):
    """Generate a reproducible 1536-dim vector."""
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
    result = db.insert(300, rand_vec(seed=42), metadata={"title": "PY SDK test doc"})
    assert result.success, f"Insert failed: {result}"
    assert result.id == 300, f"Expected id=300, got {result.id}"
    assert result.namespace == "default", f"Expected ns=default, got {result.namespace}"
    return f"id={result.id}, ns={result.namespace}, upserted={result.upserted}"
test("Insert vector into default namespace", test_insert_default)

# ── 2. Insert into "py-sdk-test" namespace ──
def test_insert_ns():
    result = db.insert(1, rand_vec(seed=1), metadata={"title": "NS doc 1"}, namespace="py-sdk-test")
    assert result.success
    assert result.namespace == "py-sdk-test", f"Expected ns=py-sdk-test, got {result.namespace}"
    return f"id={result.id}, ns={result.namespace}"
test("Insert vector into py-sdk-test namespace", test_insert_ns)

# ── 3. Insert second vector into "py-sdk-test" ──
def test_insert_ns2():
    result = db.insert(2, rand_vec(seed=2), metadata={"title": "NS doc 2"}, namespace="py-sdk-test")
    assert result.success
    return f"id={result.id}, ns={result.namespace}"
test("Insert second vector into py-sdk-test namespace", test_insert_ns2)

# ── 4. Search in "py-sdk-test" namespace ──
def test_search_ns():
    result = db.search(rand_vec(seed=1), k=5, include_metadata=True, namespace="py-sdk-test")
    assert result.namespace == "py-sdk-test", f"Expected ns=py-sdk-test, got {result.namespace}"
    assert result.count > 0, "Expected results in py-sdk-test namespace"
    return f"{result.count} results: {[{'id': r.id, 'score': round(r.score, 4)} for r in result.results]}"
test("Search in py-sdk-test namespace", test_search_ns)

# ── 5. Search in default namespace — IDOR check ──
def test_search_default_idor():
    result = db.search(rand_vec(seed=1), k=5, include_metadata=True)
    ids = [r.id for r in result.results]
    assert 1 not in ids, f"IDOR: py-sdk-test vector 1 leaked into default namespace! ids={ids}"
    assert 2 not in ids, f"IDOR: py-sdk-test vector 2 leaked into default namespace! ids={ids}"
    return f"{result.count} results, ids={ids}"
test("Search in default namespace (IDOR check)", test_search_default_idor)

# ── 6. List namespaces ──
def test_list_ns():
    namespaces = db.list_namespaces()
    assert isinstance(namespaces, list), "Expected list of namespaces"
    return f"namespaces: {namespaces}"
test("List namespaces", test_list_ns)

# ── 7. Upsert — re-insert same ID with new metadata ──
def test_upsert():
    result = db.insert(1, rand_vec(seed=10), metadata={"title": "Updated doc 1"}, namespace="py-sdk-test")
    assert result.success
    assert result.upserted, f"Expected upserted=True, got {result.upserted}"
    return f"upserted={result.upserted}"
test("Upsert vector in py-sdk-test namespace", test_upsert)

# ── 8. Verify upserted metadata ──
def test_verify_upsert():
    result = db.search(rand_vec(seed=10), k=5, include_metadata=True, namespace="py-sdk-test")
    assert result.count > 0, "Expected at least 1 result"
    match = next((r for r in result.results if r.id == 1), None)
    assert match is not None, f"Expected id=1 in results, got ids={[r.id for r in result.results]}"
    assert match.metadata and match.metadata.get("title") == "Updated doc 1", \
        f"Expected updated metadata, got {match.metadata}"
    return f"found id=1 with meta={match.metadata}"
test("Verify upserted metadata in search results", test_verify_upsert)

# ── 9. Batch insert ──
def test_batch_insert():
    vectors = [
        {"id": i + 1, "vector": rand_vec(seed=100 + i), "metadata": {"batch": True, "index": i}}
        for i in range(5)
    ]
    result = db.batch_insert(vectors, namespace="py-batch-test")
    assert result.success, f"Batch insert failed: {result}"
    assert result.count == 5, f"Expected count=5, got {result.count}"
    assert len(result.ids) == 5, f"Expected 5 ids, got {len(result.ids)}"
    assert result.namespace == "py-batch-test", f"Expected ns=py-batch-test, got {result.namespace}"
    return f"ids={result.ids}, new={result.new_count}, upserted={result.upserted_count}"
test("Batch insert 5 vectors into py-batch-test namespace", test_batch_insert)

# ── 10. Search in batch namespace ──
def test_search_batch():
    result = db.search(rand_vec(seed=100), k=5, include_metadata=True, namespace="py-batch-test")
    assert result.count > 0, "Expected results in py-batch-test namespace"
    assert result.namespace == "py-batch-test"
    return f"{result.count} results"
test("Search in py-batch-test namespace", test_search_batch)

# ── 11. Batch namespace isolation — IDOR check ──
def test_batch_idor():
    result = db.search(rand_vec(seed=100), k=10, include_metadata=True, namespace="py-sdk-test")
    for r in result.results:
        if r.metadata and r.metadata.get("batch") is True:
            raise AssertionError(f"IDOR: batch vector leaked into py-sdk-test! id={r.id}")
    return f"{result.count} results, no batch vectors leaked"
test("Batch namespace isolation (IDOR check)", test_batch_idor)

# ── 12. Analytics: endpoints ──
def test_analytics_endpoints():
    stats = db.analytics_endpoints()
    assert isinstance(stats, list), "Expected list of endpoint stats"
    return f"{len(stats)} endpoints tracked"
test("Analytics: endpoint stats", test_analytics_endpoints)

# ── 13. Analytics: namespaces ──
def test_analytics_namespaces():
    stats = db.analytics_namespaces()
    assert isinstance(stats, list), "Expected list of namespace stats"
    return f"{len(stats)} namespaces tracked"
test("Analytics: namespace stats", test_analytics_namespaces)

# ── 14. Analytics: latency ──
def test_analytics_latency():
    stats = db.analytics_latency()
    assert isinstance(stats, list), "Expected list of latency entries"
    if len(stats) > 0:
        assert stats[0].date, "Expected date field"
    return f"{len(stats)} days of latency data"
test("Analytics: latency percentiles", test_analytics_latency)

# ── 15. Analytics: errors ──
def test_analytics_errors():
    stats = db.analytics_errors()
    assert isinstance(stats, list), "Expected list of error entries"
    return f"{len(stats)} days of error data"
test("Analytics: error rates", test_analytics_errors)

# ── 16. Analytics: keys ──
def test_analytics_keys():
    stats = db.analytics_keys()
    assert isinstance(stats, list), "Expected list of key stats"
    return f"{len(stats)} API keys tracked"
test("Analytics: API key stats", test_analytics_keys)

# ── 17. Analytics: growth ──
def test_analytics_growth():
    stats = db.analytics_growth()
    assert isinstance(stats, list), "Expected list of growth entries"
    return f"{len(stats)} days of growth data"
test("Analytics: vector growth", test_analytics_growth)

# ── Cleanup: delete all test vectors ──

# Delete from py-sdk-test namespace
def test_cleanup_ns():
    r1 = db.delete(1, namespace="py-sdk-test")
    assert r1.deleted, "Failed to delete id=1 from py-sdk-test"
    r2 = db.delete(2, namespace="py-sdk-test")
    assert r2.deleted, "Failed to delete id=2 from py-sdk-test"
    return "deleted ids 1,2 from py-sdk-test"
test("Cleanup: delete vectors from py-sdk-test namespace", test_cleanup_ns)

# Delete from py-batch-test namespace
def test_cleanup_batch():
    for i in range(1, 6):
        r = db.delete(i, namespace="py-batch-test")
        assert r.deleted, f"Failed to delete id={i} from py-batch-test"
    return "deleted ids 1-5 from py-batch-test"
test("Cleanup: delete vectors from py-batch-test namespace", test_cleanup_batch)

# Delete from default namespace
def test_cleanup_default():
    r = db.delete(300)
    assert r.deleted, "Failed to delete id=300 from default"
    return "deleted id 300 from default"
test("Cleanup: delete vector from default namespace", test_cleanup_default)

# ── Verify cleanup ──
def test_verify_ns_empty():
    result = db.search(rand_vec(seed=1), k=5, namespace="py-sdk-test")
    assert result.count == 0, f"Expected 0 results after cleanup, got {result.count}"
    return "0 results (correct)"
test("Verify py-sdk-test namespace is empty after cleanup", test_verify_ns_empty)

def test_verify_batch_empty():
    result = db.search(rand_vec(seed=100), k=5, namespace="py-batch-test")
    assert result.count == 0, f"Expected 0 results after cleanup, got {result.count}"
    return "0 results (correct)"
test("Verify py-batch-test namespace is empty after cleanup", test_verify_batch_empty)

db.close()

print(f"\n  Results: {passed} passed, {failed} failed\n")
if failed > 0:
    sys.exit(1)
