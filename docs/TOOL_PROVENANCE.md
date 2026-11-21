# Tool and Skill Provenance

This record exists so a future session can explain both **how** a workflow was
run and **why** delegated workers may not have appeared as visible subagents in
the desktop UI.

## Run scope

- **Workflow:** evolving, non-blocking memory context injection prototype
- **Date:** 2026-11-19
- **Workspace:** `C:\Users\ubuntu\AppData\Local\hermes\neo4j-memory\workflow\neo4j-memory-context`
- **Implementation target:** writable clone at
  `hermes-agent-writeable/`
- **Parent control:** manual approval mode

## Actually used

| Capability | Evidence/artifact | Purpose |
|---|---|---|
| `dynamic-workflow` skill | `BRIEF.md`, `manifest.jsonl`, `SYNTHESIS.md`, `IMPLEMENTATION_PLAN.md`, `workers.jsonl` | Shared brief, independent exploration wave, persisted reports, and recovery state |
| `multi_agent_v1` delegation runtime | worker records and exploration reports | Independent lifecycle, design, and Neo4j research workers |
| AST-aware inspection (`ast-grep`) | Structural search over Python executor submissions | Locate async submission seams without relying only on text matches |
| TDD workflow | `hermes-agent-writeable/tests/agent/test_topic_context_ledger.py`; RED run recorded before the module existed | Specify cache-only reads, versioning, isolation, deadlines, bounds, and async completion |
| Writable git clone | `hermes-agent-writeable/` | Keep implementation work separate from the original checkout, which was not writable |

## Loaded but not a completed execution path

| Capability | Status | Note |
|---|---|---|
| `codex` skill / Codex CLI | Attempted; implementation delegation did not complete | The CLI path was subject to manual approval and did not produce prototype files; parent continued in the writable clone |
| `subagent-driven-development` | Used as the review/TDD policy | A fresh implementer plus spec/quality review remains the intended gate; the parent must not treat a worker's self-report as review evidence |
| `dev-prompts` | Loaded for prompt framing | No source change depended on it |
| `parallel-cli` | Loaded as an option | Not used for the Neo4j research path |
| `code-wiki` | Loaded as an option | Not used; this task is implementation-oriented rather than wiki generation |

## Visibility finding

The delegated workers were launched through a backend orchestration runtime. The
runtime returns handles and result messages, but it does not automatically
create desktop UI subagent cards or a shared visual transcript. A worker can
therefore be active, finish, or stall without being visible in the chat surface
unless the parent explicitly relays its state.

That is a presentation/coordination boundary, not evidence that no worker ran.
The durable evidence is the combination of `workers.jsonl`, per-worker report
files, and the parent verification commands. A worker's summary alone is not
treated as proof.

## Convention for future workflows

Every delegated run should create or update these records before dispatch:

```text
TOOL_PROVENANCE.md  # loaded vs used vs attempted capabilities and UI caveats
workers.jsonl       # worker id, runtime, goal, timestamps, status, result path
BRIEF.md             # shared objective and invariants
manifest.jsonl       # one independent unit per line
```

Parent progress updates should expose, at minimum:

1. which worker handles were started;
2. the worker's current status and owned artifact;
3. when a result is received and verified;
4. whether the result is visible only in files/messages or also in the UI;
5. the exact review gate and command output used before acceptance.

Never put credentials, raw hidden chain-of-thought, or sensitive payloads in
these records. Log observable task state, tool names, paths, timestamps,
correlation ids, and concise evidence only.

## Review-handle history

- Ptolemy (`01a1f233-02ba-71b3-8249-4ccf3c5b4d62`) was dispatched as an
  independent read-only reviewer. It stayed live through repeated waits but
  returned no verdict and was shut down; it is not acceptance evidence.
- Bohr (`01a1f23b-38d1-7061-8420-c013e4013ef7`) was dispatched afterward with a
  narrower read-only review scope; a result was requested as an acceptance
  prerequisite.
- Bohr's handle later became `not_found` without a report, so it is excluded
  from acceptance evidence.
- Codex CLI `0.167.1` was invoked in `read-only` mode against the clone. It
  could not initialize because the existing Codex home was access-denied/read-
  only; no credentials were copied and no sandbox bypass was used.
- Turing (`01a1f23e-533d-72b2-862f-88622104388a`) was dispatched as a
  file-backed independent reviewer; its only allowed write was
  `REVIEW_GATE.md`.
- Turing's handle was later closed without writing a report. The parent ran a
  separate deterministic gate and recorded its evidence in `REVIEW_GATE.md`;
  this is explicitly not presented as Turing's approval.
