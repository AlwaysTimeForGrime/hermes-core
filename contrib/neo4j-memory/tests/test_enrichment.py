from neo4j_memory.enrichment import Neo4jEnricher


def test_enricher_writes_bounded_parameterized_turn():
    calls = []
    class Session:
        def run(self, query, **params): calls.append((query, params))
        def __enter__(self): return self
        def __exit__(self, *args): return False
    class Driver:
        def session(self, **kwargs): return Session()
        def close(self): pass
    Neo4jEnricher(Driver(), content_max_bytes=8).enrich_turn("😀" * 10, "answer", session_id="s")
    assert len(calls[0][1]["user_content"].encode()) <= 8
