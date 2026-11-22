from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException

_PLUGIN_ROOT = str(Path(__file__).resolve().parents[1])
_INSERTED_PLUGIN_ROOT = _PLUGIN_ROOT not in sys.path
if _INSERTED_PLUGIN_ROOT:
    sys.path.insert(0, _PLUGIN_ROOT)
try:
    from neo4j_memory.topic_context_ledger import TopicContextLedger
finally:
    if _INSERTED_PLUGIN_ROOT:
        sys.path.remove(_PLUGIN_ROOT)

router = APIRouter()


@dataclass
class DebugController:
    ledger: TopicContextLedger

    def sessions(self) -> dict:
        return {"stats": self.ledger.stats(), "active_jobs": self.ledger.active_jobs()}

    def inspect(self, session_id: str, topic: str) -> dict:
        snapshot = self.ledger.snapshot(session_id, topic)
        return {"session_id": session_id, "topic": topic, "snapshot": None if snapshot is None else {
            "generation": snapshot.generation, "context": snapshot.context,
            "query_fingerprint": snapshot.query_fingerprint, "expires_at": snapshot.expires_at}}

    def trigger(self, session_id: str, topic: str, query: str, delay_ms: int) -> dict:
        delay = max(0, min(5000, delay_ms)) / 1000
        token = self.ledger.schedule(session_id, topic, query,
                                     lambda _token: (time.sleep(delay), f"delayed:{query}")[1], replace=True)
        if token is None:
            raise RuntimeError("ledger capacity exhausted")
        return {"generation": token.generation, "query_fingerprint": token.query_fingerprint, "deadline": token.deadline}


_controller = DebugController(TopicContextLedger())


@router.get("/state")
async def state() -> dict:
    return await asyncio.to_thread(_controller.sessions)


@router.get("/sessions/{session_id}/topics/{topic}")
async def topic_snapshot(session_id: str, topic: str) -> dict:
    return await asyncio.to_thread(_controller.inspect, session_id, topic)


@router.post("/scenarios/delayed")
async def delayed_scenario(session_id: str, topic: str, query: str = "debug", delay_ms: int = 100) -> dict:
    try:
        return await asyncio.to_thread(_controller.trigger, session_id, topic, query, delay_ms)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
