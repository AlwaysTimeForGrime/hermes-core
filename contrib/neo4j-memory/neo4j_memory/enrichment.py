from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)
_HIDDEN = {"reasoning", "thinking", "reasoning_content", "thought", "chain_of_thought"}


def _bounded(value: str, limit: int) -> tuple[str, bool, int]:
    raw = str(value).encode("utf-8")
    return raw[:limit].decode("utf-8", "ignore"), len(raw) > limit, len(raw)


def _trace(user: str, assistant: str, session_id: str | None, messages: list[dict[str, Any]] | None, limit: int) -> str:
    rows = []
    for message in messages or []:
        if message.get("role") not in {"user", "assistant", "tool"}:
            continue
        row = {k: v for k, v in message.items() if k not in _HIDDEN}
        if isinstance(row.get("content"), list):
            row["content"] = [p for p in row["content"] if not (isinstance(p, dict) and p.get("type") in _HIDDEN)]
        rows.append(row)
    payload = {"trace_version": 1, "session_id": session_id, "user": user, "assistant": assistant, "messages": rows}
    return _bounded(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), limit)[0]


def _secret(name: str) -> str | None:
    try:
        from agent.secret_scope import get_secret
        return get_secret(name)
    except (ImportError, KeyError, RuntimeError):
        mapping = {"NEO4J_MEMORY_URI": "HERMES_NEO4J_URI", "NEO4J_MEMORY_USERNAME": "HERMES_NEO4J_USERNAME", "NEO4J_MEMORY_PASSWORD": "HERMES_NEO4J_PASSWORD"}
        return os.getenv(mapping.get(name, name))


@dataclass
class Neo4jEnricher:
    driver: Any
    database: str = "neo4j"
    content_max_bytes: int = 65536
    debug_trace_enabled: bool = False
    trace_max_bytes: int = 65536

    def __post_init__(self) -> None:
        self.write_metrics = {"attempts": 0, "retries": 0, "successes": 0, "failures": 0}
        self._closed = False

    @classmethod
    def from_config(cls, config: dict[str, Any], secret_getter=None) -> "Neo4jEnricher | None":
        if not config.get("enabled", False):
            return None
        secret_getter = secret_getter or _secret
        uri = secret_getter("NEO4J_MEMORY_URI") or config.get("uri")
        username = secret_getter("NEO4J_MEMORY_USERNAME") or config.get("username")
        password = secret_getter("NEO4J_MEMORY_PASSWORD") or config.get("password")
        if not uri or not username or not password:
            return None
        try:
            from neo4j import GraphDatabase
        except ImportError:
            return None
        return cls(GraphDatabase.driver(uri, auth=(username, password)), database=str(config.get("database", "neo4j")), content_max_bytes=min(262144, max(1, int(config.get("content_max_bytes", 65536)))), debug_trace_enabled=bool(config.get("debug_trace_enabled", False)), trace_max_bytes=min(262144, max(1, int(config.get("trace_max_bytes", 65536)))))

    @classmethod
    def from_environment(cls) -> "Neo4jEnricher | None":
        if os.getenv("HERMES_NEO4J_ENRICHMENT_ENABLED", "").lower() not in {"1", "true", "yes", "on"}:
            return None
        uri, user, password = (_secret(k) for k in ("NEO4J_MEMORY_URI", "NEO4J_MEMORY_USERNAME", "NEO4J_MEMORY_PASSWORD"))
        if not uri or not user or not password:
            return None
        try:
            from neo4j import GraphDatabase
        except ImportError:
            return None
        return cls(GraphDatabase.driver(uri, auth=(user, password)), database=os.getenv("HERMES_NEO4J_DATABASE", "neo4j"), content_max_bytes=min(262144, max(1, int(os.getenv("HERMES_NEO4J_CONTENT_MAX_BYTES", "65536")))), debug_trace_enabled=os.getenv("HERMES_NEO4J_DEBUG_TRACE_ENABLED", "").lower() in {"1", "true", "yes", "on"}, trace_max_bytes=min(262144, max(1, int(os.getenv("HERMES_NEO4J_TRACE_MAX_BYTES", "65536")))) )

    def enrich_turn(self, user_content: str, assistant_content: str, *, session_id: str | None = None, messages: list[dict[str, Any]] | None = None, **_: Any) -> None:
        if self._closed:
            return
        user, user_truncated, user_bytes = _bounded(user_content, self.content_max_bytes)
        assistant, assistant_truncated, assistant_bytes = _bounded(assistant_content, self.content_max_bytes)
        params: dict[str, Any] = {"session_id": session_id or "", "user_content": user, "assistant_content": assistant, "user_content_truncated": user_truncated, "assistant_content_truncated": assistant_truncated, "user_content_original_bytes": user_bytes, "assistant_content_original_bytes": assistant_bytes, "occurred_at": time.time(), "trace_id": str(uuid.uuid4())}
        query = "CREATE (t:HermesTurn {session_id: $session_id, user_content: $user_content, assistant_content: $assistant_content, occurred_at: $occurred_at, trace_id: $trace_id, user_content_truncated: $user_content_truncated, assistant_content_truncated: $assistant_content_truncated, user_content_original_bytes: $user_content_original_bytes, assistant_content_original_bytes: $assistant_content_original_bytes})"
        if self.debug_trace_enabled:
            params["trace_json"] = _trace(user, assistant, session_id, messages, self.trace_max_bytes)
            query = query[:-1] + ", trace_json: $trace_json})"
        for attempt, delay in enumerate((0, 0.05, 0.2), 1):
            self.write_metrics["attempts"] += 1
            try:
                with self.driver.session(database=self.database) as session:
                    session.run(query, **params)
                self.write_metrics["successes"] += 1
                return
            except Exception as exc:
                if attempt == 3:
                    self.write_metrics["failures"] += 1
                    log.warning("Neo4j enrichment failed: %s", type(exc).__name__)
                else:
                    self.write_metrics["retries"] += 1
                    time.sleep(delay)

    def shutdown(self) -> None:
        self._closed = True
        try:
            self.driver.close()
        except Exception:
            log.debug("Neo4j driver close failed", exc_info=True)
