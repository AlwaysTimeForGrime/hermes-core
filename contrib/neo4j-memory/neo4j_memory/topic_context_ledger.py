from __future__ import annotations

import hashlib
import threading
import time
import queue
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class UpdateToken:
    session_id: str
    topic: str
    generation: int
    query_fingerprint: str
    deadline: float


@dataclass(frozen=True)
class Snapshot:
    session_id: str
    topic: str
    generation: int
    context: str
    query_fingerprint: str
    expires_at: float


@dataclass
class _State:
    generation: int = 0
    active: UpdateToken | None = None
    snapshot: Snapshot | None = None


class TopicContextLedger:
    """Bounded cache of immutable, versioned topic context snapshots."""

    def __init__(self, *, ttl_seconds: float = 300, max_context_bytes: int = 65536,
                 max_workers: int = 4, max_sessions: int = 1024,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_seconds = max(1.0, ttl_seconds)
        self.max_context_bytes = max(1, max_context_bytes)
        self.max_sessions = max(1, max_sessions)
        self._clock = clock
        self._lock = threading.RLock()
        self._states: dict[tuple[str, str], _State] = {}
        self._queue: queue.Queue[Callable[[], None] | None] = queue.Queue(maxsize=max(1, max_workers) * 2)
        self._workers = []
        for index in range(max(1, max_workers)):
            worker = threading.Thread(target=self._worker, name=f"neo4j-ledger-{index}", daemon=True)
            worker.start()
            self._workers.append(worker)
        self._active_jobs = 0
        self._stats = {"cache_hits": 0, "cache_misses": 0, "query_misses": 0, "session_misses": 0,
                       "stale_rejections": 0, "deadline_rejections": 0, "dropped": 0}

    @staticmethod
    def _fingerprint(query: str) -> str:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:24]

    def _bounded(self, value: str) -> str:
        raw = value.encode("utf-8")
        return raw[: self.max_context_bytes].decode("utf-8", "ignore")

    def read(self, session_id: str, topic: str, *, fallback: str, now: float | None = None) -> str:
        now = self._clock() if now is None else now
        with self._lock:
            state = self._states.get((session_id, topic))
            snapshot = state.snapshot if state else None
            if snapshot and snapshot.expires_at > now:
                self._stats["cache_hits"] += 1
                return snapshot.context
            self._stats["cache_misses"] += 1
            if (state and state.snapshot) or any(key[0] == session_id for key in self._states):
                self._stats["query_misses"] += 1
            else:
                self._stats["session_misses"] += 1
            return fallback

    def snapshot(self, session_id: str, topic: str, *, now: float | None = None) -> Snapshot | None:
        now = self._clock() if now is None else now
        with self._lock:
            item = self._states.get((session_id, topic))
            return item.snapshot if item and item.snapshot and item.snapshot.expires_at > now else None

    def start_update(self, session_id: str, topic: str, query: str, *, deadline_seconds: float = 30,
                     now: float | None = None, replace: bool = False) -> UpdateToken | None:
        now = self._clock() if now is None else now
        key = (session_id, topic)
        with self._lock:
            state = self._states.get(key)
            if state is None:
                if len(self._states) >= self.max_sessions:
                    idle = [k for k, v in self._states.items() if v.active is None]
                    if not idle:
                        self._stats["dropped"] += 1
                        return None
                    del self._states[idle[0]]
                state = self._states.setdefault(key, _State())
            if state.active and not replace:
                return None
            state.generation += 1
            token = UpdateToken(session_id, topic, state.generation, self._fingerprint(query), now + max(0.0, deadline_seconds))
            state.active = token
            return token

    def accept(self, token: UpdateToken, context: str, *, now: float | None = None) -> bool:
        now = self._clock() if now is None else now
        with self._lock:
            state = self._states.get((token.session_id, token.topic))
            if not state or state.active != token:
                self._stats["stale_rejections"] += 1
                return False
            if now > token.deadline:
                state.active = None
                self._stats["deadline_rejections"] += 1
                return False
            state.snapshot = Snapshot(token.session_id, token.topic, token.generation, self._bounded(context), token.query_fingerprint, now + self.ttl_seconds)
            state.active = None
            return True

    def schedule(self, session_id: str, topic: str, query: str, provider: Callable[[UpdateToken], str], *,
                 deadline_seconds: float = 30, now: float | None = None, replace: bool = False) -> UpdateToken | None:
        token = self.start_update(session_id, topic, query, deadline_seconds=deadline_seconds, now=now, replace=replace)
        if token is None:
            return None
        with self._lock:
            self._active_jobs += 1
        def run() -> None:
            try:
                self.accept(token, provider(token))
            finally:
                with self._lock:
                    self._active_jobs -= 1
        try:
            self._queue.put_nowait(run)
        except queue.Full:
            with self._lock:
                self._active_jobs -= 1
                self._stats["dropped"] += 1
            with self._lock:
                state = self._states.get((session_id, topic))
                if state and state.active == token:
                    state.active = None
            return None
        return token

    def _worker(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                self._queue.task_done()
                return
            try:
                task()
            finally:
                self._queue.task_done()

    def active_jobs(self) -> int:
        with self._lock:
            return self._active_jobs

    def wait_for_idle(self, timeout: float = 2) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.active_jobs() == 0:
                return True
            time.sleep(0.01)
        return self.active_jobs() == 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def close(self) -> None:
        for _ in self._workers:
            self._queue.put(None)
        for worker in self._workers:
            worker.join(timeout=2)
