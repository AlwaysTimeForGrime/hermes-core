from neo4j_memory.topic_context_ledger import TopicContextLedger


def test_versioned_snapshot_rejects_stale_result():
    ledger = TopicContextLedger(ttl_seconds=10)
    old = ledger.start_update("s", "t", "old", now=1)
    new = ledger.start_update("s", "t", "new", now=2, replace=True)
    assert old and new
    assert ledger.accept(new, "new", now=3)
    assert not ledger.accept(old, "old", now=4)
    assert ledger.read("s", "t", fallback="fallback", now=4) == "new"
