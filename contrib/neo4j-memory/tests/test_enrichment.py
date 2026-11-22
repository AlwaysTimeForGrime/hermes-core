from neo4j_memory.enrichment import Neo4jEnricher
from neo4j_memory import register
from types import SimpleNamespace
import sys


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


def test_register_reads_only_ordinary_plugin_settings(monkeypatch):
    calls = []
    class Context:
        def get_config(self, key):
            calls.append(key)
            return {"enabled": False}.get(key)
        def register_turn_enricher(self, _enricher):
            raise AssertionError("disabled config must not register")
    monkeypatch.setattr(Neo4jEnricher, "from_config", classmethod(lambda cls, config, secret_getter=None: None))
    register(Context())
    assert calls == ["enabled", "database", "content_max_bytes", "debug_trace_enabled", "trace_max_bytes"]


def test_from_config_missing_secret_is_inactive():
    config = {"enabled": True, "database": "neo4j"}
    assert Neo4jEnricher.from_config(config, secret_getter=lambda _name: None) is None


def test_from_config_unscoped_secret_is_fail_closed():
    from agent.secret_scope import UnscopedSecretError
    def missing_scope(_name):
        raise UnscopedSecretError("NEO4J_MEMORY_PASSWORD", "no scope")
    assert Neo4jEnricher.from_config({"enabled": True}, secret_getter=missing_scope) is None


def test_from_config_uses_explicit_profile_secret_names(monkeypatch):
    seen = []
    class Driver:
        def close(self): pass
    class GraphDatabase:
        @staticmethod
        def driver(uri, auth):
            assert uri == "bolt://db"
            assert auth == ("neo4j", "password")
            return Driver()
    monkeypatch.setitem(sys.modules, "neo4j", SimpleNamespace(GraphDatabase=GraphDatabase))
    values = {"NEO4J_MEMORY_URI": "bolt://db", "NEO4J_MEMORY_USERNAME": "neo4j", "NEO4J_MEMORY_PASSWORD": "password"}
    enricher = Neo4jEnricher.from_config({"enabled": True}, secret_getter=lambda name: (seen.append(name), values[name])[1])
    assert enricher is not None
    assert seen == ["NEO4J_MEMORY_URI", "NEO4J_MEMORY_USERNAME", "NEO4J_MEMORY_PASSWORD"]
