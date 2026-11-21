# Topic Context Prototype Handoff

## Current state

The non-production prototype lives only in the writable clone:

```text
C:\Users\ubuntu\AppData\Local\hermes\neo4j-memory\workflow\neo4j-memory-context\hermes-agent-writeable
```

Allowed prototype files:

- `agent/topic_context_ledger.py`
- `tests/agent/test_topic_context_ledger.py`

The original checkout has no prototype files and was not modified by this
prototype. Its pre-existing Neo4j-related dirty files remain untouched.

## Verified behavior

- Cached reads never invoke or wait for a provider.
- Per-session immutable snapshots are bounded by UTF-8 byte size and TTL.
- Generations reject out-of-order results.
- Session and query fingerprints reject cross-context results.
- Deadlines are checked at asynchronous publication using the live clock.
- Admission is bounded and a rejected replacement does not evict a live job.
- Caller-provided current-turn/empty fallback is returned on misses and expiry.
- The module has no Neo4j or hidden-reasoning dependency.

## Verification

```text
python -B -m unittest tests.agent.test_topic_context_ledger -q
Ran 11 tests in 0.002s
OK

python -B review_gate_check.py
22 PASS checks
```

Also verified: compile/import smoke, `git diff --check` for tracked changes,
new-file whitespace, AST structural inspection of executor submissions, and
original-checkout isolation.

## Orchestration record

- Shared brief/design/plan: `BRIEF.md`, `SYNTHESIS.md`, `IMPLEMENTATION_PLAN.md`
- Worker lifecycle: `workers.jsonl`
- Tool/skill and UI visibility provenance: `TOOL_PROVENANCE.md`
- Acceptance gate: `REVIEW_GATE.md`
- Re-runnable gate: `review_gate_check.py`

No commit was created. Any transplant into the original checkout requires an
explicit follow-up decision and a separate integration review.
