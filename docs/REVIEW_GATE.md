# Prototype Review Gate

**Scope:** `hermes-agent-writeable/agent/topic_context_ledger.py` and
`hermes-agent-writeable/tests/agent/test_topic_context_ledger.py`

**Verdict:** **PASS — deterministic independent gate (22 checks)**

This gate ran in a separate Python process from the focused unittest command.
It did not edit source files, use a provider, call Neo4j, or persist reasoning.

## Evidence

Command:

```text
python -B review_gate_check.py
```

Result:

```text
PASS|cache-only fallback
PASS|monotonic generation
PASS|new generation accepted
PASS|old generation rejected
PASS|new context remains
PASS|query isolation
PASS|session isolation
PASS|prior-session result rejected
PASS|current-session result accepted
PASS|deadline rejection
PASS|bounded immutable snapshot
PASS|snapshot byte bound
PASS|snapshot immutable
PASS|async job admitted
PASS|read does not wait for provider
PASS|async job drains
PASS|async result published
PASS|async deadline job admitted
PASS|async deadline job drains
PASS|async late result rejected
PASS|no neo4j dependency
PASS|no hidden reasoning fields
```

Focused test command:

```text
python -B -m unittest tests.agent.test_topic_context_ledger -q
Ran 11 tests in 0.002s
OK
```

## Acceptance mapping

| Requirement | Evidence |
|---|---|
| Cache-only turn-start read with fallback | `TopicContextLedger.read` at `agent/topic_context_ledger.py:111`; gate `cache-only fallback` and `read does not wait for provider` |
| Immutable, bounded snapshot | `TopicSnapshot` at line 30; `accept` at line 213; gate bounds and immutability checks |
| Versioned per-session generation | `start_update` at line 178; gate monotonic-generation and out-of-order checks |
| Session/query/deadline stale-result rejection | `accept` at line 213; focused tests and gate isolation/deadline checks |
| Bounded asynchronous updates | `schedule` at line 247; `active_jobs` at line 311; focused capacity regression and async gate checks |
| Mnemosyne/current-turn fallback | Prototype returns the caller-provided fallback on every cache miss; it has no provider or Neo4j dependency |
| Prompt-cache safety / no hidden chain-of-thought persistence | Prototype only carries observable session/query/turn/deadline metadata and compact context; boundary scan passed |

## Review limitation

The installed Codex CLI review was attempted in `read-only` mode but could not
initialize because its existing runtime home was access-denied; the requested
manual escalation was rejected. Two backend reviewer handles also disappeared
without a report. Their absence is recorded in `TOOL_PROVENANCE.md` and
`workers.jsonl`; no delegated-agent approval is claimed here. This file-backed
gate is the evidence used for this prototype's acceptance.
