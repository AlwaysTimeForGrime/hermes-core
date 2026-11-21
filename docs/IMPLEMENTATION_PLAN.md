# Prototype Implementation Plan

## Scope

Build a non-production, isolated prototype for evolving context injection. Do not replace Mnemosyne or modify the existing Neo4j enrichment path in this task.

## Allowed write set

- `agent/topic_context_ledger.py`
- `tests/agent/test_topic_context_ledger.py`

If the repository already contains an equivalent module, stop and report the collision instead of editing unrelated files.

## Required behavior

- Per-session bounded topic snapshot/ledger.
- Immutable accepted snapshots.
- Monotonic generation/turn sequence.
- At most one active job per session in the prototype coordinator.
- Reject stale session, generation, query-fingerprint, or deadline results.
- Current snapshot reads never wait on the provider.
- Safe fallback to empty/current-turn context on miss or expiry.
- No hidden reasoning fields or Neo4j dependency.

## TDD acceptance cases

1. Read path is immediate and never invokes the delayed provider.
2. Older out-of-order results cannot overwrite newer state.
3. A result for query A cannot satisfy query B.
4. A result from a prior session is rejected.
5. Expired results are rejected.
6. Duplicate submissions for a session are bounded/coalesced.
7. Snapshot output is bounded and immutable.

## Verification

- Run only the new focused tests first.
- Run compile/import smoke checks.
- Run `git diff --check`.
- Do not commit.
