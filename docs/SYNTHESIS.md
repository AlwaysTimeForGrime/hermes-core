# Exploration Synthesis: Non-Blocking Evolving Context

Status: exploration wave complete; no production code or tests changed.

## Converged design

Use a **versioned per-session topic ledger** as the fast operational layer, with Neo4j as asynchronous durable enrichment:

1. Completed turns enqueue bounded topic extraction/update beside existing post-turn memory work.
2. Turn start reads only the latest immutable, already-computed snapshot; it never waits for Neo4j or a fresh search.
3. Each job carries `session_id`, monotonic `turn_seq`/generation, query fingerprint, deadline, and cancellation/admission state.
4. Accept results only when session, generation, query fingerprint, and deadline still match.
5. Keep one active prefetch job per session and bound the queue.
6. Inject a compact rolling summary plus active topic IDs/status/confidence and provenance metadata.
7. Persist topic summaries/edges and observable events asynchronously; never let Neo4j schedule or control turn execution.
8. On cache miss, timeout, backend failure, or stale result, fall back to Mnemosyne/current-turn context and discard the late result.

## Why this fits the current code

- Current turn-start prefetch can block; the safer seam is a ready-cache read at prologue time.
- Post-turn `sync_all()` / `queue_prefetch_all()` already provide an asynchronous serialized boundary.
- Existing timeout behavior is cooperative rather than true cancellation, so generation checks are required even when cancellation is unavailable.
- Current prompt construction keeps the system prompt stable and injects recalled context into current-turn content, which preserves prompt-cache safety.

## Missing protections to prototype

- Out-of-order completion must not overwrite newer state.
- Query A's cache must not satisfy query B.
- Session A results must be rejected after switching to session B.
- Expired results must be rejected even when the backend eventually returns.
- Burst traffic must not create unbounded prefetch concurrency.
- Trace/enrichment metadata should expose `topic_generation`, `source_turn_id`, `computed_at`, `injected_at`, `stale`, and `discard_reason`.

## Neo4j research direction

Official Neo4j material supports this separation:

- [Meet Lenny's Memory: Building Context Graphs for AI Agents](https://neo4j.com/blog/developer/meet-lennys-memory-building-context-graphs-for-ai-agents/)
- [Neo4j Agent Memory](https://neo4j.com/labs/agent-memory/)
- [Agent Memory how-to guides](https://neo4j.com/labs/agent-memory/how-to/)
- [Modeling Agent Memory](https://neo4j.com/blog/developer/modeling-agent-memory/)
- [Change Data Capture and Neo4j Connector](https://neo4j.com/blog/developer/change-data-capture-cdc-ga/)
- [Graph data models for RAG applications](https://neo4j.com/blog/developer/graph-data-models-rag-applications/)

The useful pattern is: immutable observable events → incremental topic projections → read-only injection snapshot. Buffered writes, consolidation, CDC, and topic summaries remain background mechanisms with explicit eventual-consistency and backpressure tradeoffs.

## Next experiment

Build a non-production prototype with a fake delayed provider and tests for stale-result rejection, cross-query/session isolation, deadlines, and one-active-job-per-session. Measure active-turn latency, cache-hit rate, stale-discard count, queue depth, timeout count, and injected-context size before considering a live Mnemosyne/Neo4j run.
