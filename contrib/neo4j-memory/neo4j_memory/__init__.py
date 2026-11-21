from __future__ import annotations

from .enrichment import Neo4jEnricher
from .topic_context_ledger import TopicContextLedger


def register(ctx) -> None:
    config = {}
    if hasattr(ctx, "get_config"):
        try:
            config = {key: ctx.get_config(key) for key in ("enabled", "database", "content_max_bytes", "debug_trace_enabled", "trace_max_bytes", "uri", "username", "password")}
        except (AttributeError, KeyError, TypeError, ValueError):
            config = {}
    enricher = Neo4jEnricher.from_config(config) if config else Neo4jEnricher.from_environment()
    if enricher is not None and hasattr(ctx, "register_turn_enricher"):
        ctx.register_turn_enricher(enricher)


__all__ = ["Neo4jEnricher", "TopicContextLedger", "register"]
