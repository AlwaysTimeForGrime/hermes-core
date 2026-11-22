# neo4j-memory plugin — compiled reference

Everything known about the Neo4j memory work as of 2026-11-22: the generic core seam,
the standalone plugin working copy, verification status, and remaining deployment gaps.
This file is the single entry point; the run-record docs sit beside it.

## Documents in this directory

| File | Contents |
|---|---|
| `IDEA.md` | Original product idea: Neo4j-backed memory layer (conversations, entities, graph retrieval, lifecycle controls, SDK/REST) |
| `BRIEF.md` | Workflow brief + invariants (Mnemosyne primary, Neo4j secondary, async/bounded, no CoT, prompt-cache safe) |
| `SYNTHESIS.md` | Exploration findings: versioned per-session topic ledger + async Neo4j enrichment design |
| `IMPLEMENTATION_PLAN.md` | Prototype scope: allowed write set, required behavior, TDD acceptance cases |
| `REVIEW_GATE.md` | Deterministic acceptance gate: 22 PASS checks + 11 unittests |
| `HANDOFF.md` | Prototype state, verified behavior, verification commands, orchestration record |
| `TOOL_PROVENANCE.md` | Which tools/skills were used vs attempted; worker visibility caveats |
| `neo4j-memory-config-plan.md` | Config-surface plan: plugin settings, secrets, CLI/Desktop surfaces |
| `superpowers/specs/2026-11-21-neo4j-memory-config-only-design.md` | Config-only scope decision for the plugin |
| `superpowers/plans/2026-11-21-neo4j-memory-config-only.md` | Task breakdown for that scope |
| `neo4j-memory-plugin.md` | This file — compiled technical reference |

Run records that stayed in the workflow dir (not docs):
`C:\Users\ubuntu\AppData\Local\hermes\neo4j-memory\workflow\neo4j-memory-context\`
→ `workers.jsonl`, `manifest.jsonl`, `dynamic-workflow-recovery.patch`, and
`review_gate_check.py`. The plugin actually shipped in this repository at
`contrib/neo4j-memory/`; the separate `C:\Users\ubuntu\AppData\Local\hermes\neo4j-memory`
checkout is a second, only loosely synced copy.

## Decision history

1. **Full memory system first** — `IDEA.md`: Neo4j-backed memory layer with entity/relationship
   extraction, lifecycle controls, SDK/REST. Judged too large an undertaking ("insane") and
   abandoned before implementation.
2. **Pivot to async context injection** — `BRIEF.md`/`SYNTHESIS.md`: keep Mnemosyne as the memory
   system of record; Neo4j becomes a secondary index; topic context is computed off-turn and
   injected from an immutable cache snapshot. Built as the enricher plus the ledger prototype.
   The dashboard/debug harness was later dropped (see *Dashboard API* below).
3. **NAM via MCP evaluated** — Neo4j Labs Agent Memory (`neo4j-agent-memory.exe mcp serve`) was
   wired as two stdio MCP servers (`memory_nams` + `memory_bolt` backends) in `config.yaml`.
   Rejected for daily use: 2 spawned python processes per agent = process sprawl; currently
   `enabled: false` everywhere. Note NAM is a *full* memory product — if a real memory backend is
   ever wanted, enabling ONE of these is the heavyweight option versus the lightweight in-core
   `:HermesTurn` sink.

## Current implementation inventory

The generic seam is complete in this checkout, and the Neo4j implementation is
in-tree at `contrib/neo4j-memory/`. A separate standalone checkout also exists at
`C:\Users\ubuntu\AppData\Local\hermes\neo4j-memory`; the two are **not** kept
byte-identical and this file describes the in-tree copy.

### Plugin files (new, under `contrib/neo4j-memory/`)

| File | Role |
|---|---|
| `neo4j_memory/enrichment.py` | `Neo4jEnricher`: config-gated secondary sink; writes `:HermesTurn` nodes; bounded trace projection; 3-attempt retry on transient errors |
| `neo4j_memory/topic_context_ledger.py` | `TopicContextLedger`: non-production prototype — per-session versioned topic snapshots, generation/deadline/query-fingerprint stale-result rejection, bounded daemon workers |
| `dashboard/plugin_api.py` | Debug `APIRouter` + `DebugController` over a throwaway ledger; **unmaintained, pending deletion** (see *Dashboard API*) |
| `tests/test_enrichment.py` | Enricher + registration tests (6) |
| `tests/test_ledger.py` | Ledger stale-result test (1) |
| `tests/test_api.py` | Dashboard route tests (2) |

### Modified tracked files

| File | Change |
|---|---|
| `agent/memory_manager.py` | Provider-agnostic secondary-enricher registry, lifecycle, background submission |
| `agent/memory_provider.py` | `TurnEnricher` ABC |
| `hermes_cli/plugins_context.py` | `PluginContext.register_turn_enricher(...)` host seam |
| `hermes_cli/plugins.py`, `hermes_cli/plugin_isolation.py` | Registration surface wiring |
| `hermes_cli/data/plugin_api.json` | Published API entry for the registration seam |
| `tests/hermes_cli/test_plugins_context.py`, `tests/agent/test_memory_async_sync.py` | Seam tests |
| `website/docs/developer-guide/memory-provider-plugin.md`, `.../plugins/public-api.md` | Seam documentation |

The diff also removes `.github/`, `lefthook.yml`, and the JS lockfile entries; that
is the fork's no-CI choice, not plugin work.

## How it works

## Dashboard API

The plugin exposes `dashboard/plugin_api.py`, mounted by Hermes at
`/api/plugins/neo4j-memory/`. Hermes applies authentication, profile secret
scope, plugin enablement, and runtime-disable guards around these handlers;
the plugin itself does not duplicate an enabled-state guard.

**Status: dropped 2026-11-22.** No dashboard integration is planned. The router
inspects a module-level `TopicContextLedger()` — a throwaway instance in the
dashboard's process, never the ledger of a live turn — so it renders an empty
sandbox. The files remain until deleted.

| Route | Purpose |
|---|---|
| `GET /state` | Ledger counters and active worker count (of the throwaway instance) |
| `GET /sessions/{session_id}/topics/{topic}` | One immutable snapshot, if present |
| `POST /scenarios/delayed` | Deterministic delayed-provider trigger for diagnostics |

Unauthenticated requests return `401`; a disabled plugin is not mounted and
returns `404` from the dashboard host.

```
turn completes (not interrupted)
  └─ MemoryManager.sync_all()
       └─ primary provider sync, then registered secondary enrichers
            (the standalone plugin registers Neo4jEnricher in-process)
```

`Neo4jEnricher.enrich_turn` UTF-8-truncates both strings to `content_max_bytes`
(default 64 KiB, cap 256 KiB), then runs a
parameterized `CREATE (t:HermesTurn {...})`. With
the plugin setting `debug_trace_enabled` it also stores `trace_json` — a bounded
projection of observable user/assistant/tool messages only (system messages are
omitted); `_HIDDEN_TRACE_KEYS` filters
chain-of-thought/thinking/reasoning fields. Retries ≤3 on transient errors;
all failures are logged and swallowed — enrichment can never break a turn.

Enablement and ordinary bounds are native plugin settings under
`plugins.entries.neo4j-memory.settings`: `enabled`, `database`,
`content_max_bytes`, `debug_trace_enabled`, and `trace_max_bytes`.
`uri`, `username`, and `password` are secret-schema fields mapped to
`NEO4J_MEMORY_URI`, `NEO4J_MEMORY_USERNAME`, and `NEO4J_MEMORY_PASSWORD` and
resolved only through Hermes' profile-scoped secret reader. An unscoped
multiplex read fails closed. The `neo4j` driver is an opt-in PM extra, imported
lazily.

`TopicContextLedger` is a separate prototype: cache-only `read`/`snapshot` on the
turn-start path (never waits on a provider), `schedule`/`start_update`/`accept`
for async updates with monotonic generations, per-session query fingerprints,
deadlines checked at publication, and stale-result rejection. It has **no
production wiring** — nothing in the runtime path constructs it, and its only
in-tree consumer is the dropped dashboard harness.

## Known bugs — all fixed 2026-11-20

Verified by the plugin test suite (9 test functions: 6 enricher, 2 dashboard, 1 ledger).
They do not collect from the repo root — see *Verification status*.

**Lifecycle:**

1. ~~Driver leak on agent rebuild~~ — the generic `MemoryManager` registry rejects
   duplicate secondary enrichers and shuts down the rejected instance.
2. ~~Silent disable on provider-resolution failure~~ — enrichment is registered
   independently of primary-provider resolution and remains plugin/env gated.
8. ~~Unbounded submit queues~~ — `MemoryManager._submit_background` runs work on a
   single-worker daemon executor (`mem-sync`), so submissions serialize rather
   than fan out. There is no explicit pending-task cap in the manager.
10. ~~Shutdown race~~ — the generic manager shuts down registered enrichers before
    releasing its background executor; post-shutdown `enrich_turn` is a no-op.

**Prototype hygiene:**

3. ~~Debug API import side effect + crash~~ — replaced by a side-effect-free
   dashboard `APIRouter`; blocking ledger work is dispatched with `asyncio.to_thread`.
4. ~~Ledger `_states` unbounded~~ — `max_sessions=1024`; `start_update` evicts the
   least-useful idle state (no active token, earliest snapshot expiry) and refuses
   new sessions only when every state has an active update (`dropped` counter).
5. ~~Worker bound semantics~~ — `max_workers` (default now 4) is a documented GLOBAL
   concurrency ceiling; per-session single-active stays via `active_token`.

**Data hygiene / gating:**

6. ~~Enricher gating~~ — `sync_all` split: fork suppression and `_owner_allows`
   still gate everything, but provider content gates (empty-after-strip,
   no-providers) no longer silence enrichers; enrichers get the raw turn.
9. ~~Dead `correlation_id`~~ — removed from `enrich_turn`, `build_trace_json`,
   trace metadata, and the Cypher properties (nothing produced one).
11. ~~Trace minors~~ — `message_count` now counts published (post-truncation)
    rows; `_safe_message` also drops content parts whose `type` is a hidden key
    (e.g. `{"type":"reasoning",...}`).

## Plugin-ification analysis

Why it should be a plugin (per `plugins/AGENTS.md` + root rubric):

- "Capability lives at the edges"; new capability → plugin, not core.
- `plugins/memory/` is **closed** to new in-tree providers; new backends ship as
  standalone repos / catalog entries implementing `MemoryProvider`.
- New `HERMES_*` env vars for non-secret config are a rejected pattern; this
  plugin now uses the native plugin settings surface and profile-scoped secret
  fields via `agent.secret_scope.get_secret`.
- This checkout is a dirty release tag — every `hermes update` risks the work.

The generic seam is now exposed through `ctx.register_turn_enricher(...)`. Live
driver-owning enrichers remain intentionally unsupported in host-isolated mode;
the standalone plugin must run in-process until a proxy transport exists.

Implemented shape (2026-11-21):

- **Keep in core — generic seam only:**
  - `agent/memory_provider.py` (or a small sibling): a `TurnEnricher` ABC —
    `enrich_turn(user, assistant, *, session_id, messages)` + `shutdown()`.
  - `agent/memory_manager.py`: `_secondary_enrichers` + `add_secondary_enricher`
    + the `sync_and_enrich` block (already provider-agnostic).
  - `PluginContext.register_turn_enricher(...)` so general plugins can register
    sinks; entry in `hermes_cli/data/plugin_api.json`, regenerate `public-api.md`
    via `scripts/gen_plugin_api_docs.py`, update boundary baseline. Ship the ctx
    half together with the seam — a hook with no consumer is rejected upstream.
- Plugin-only enrichers receive turns even when no primary memory provider is configured.
- Registration is owner-tracked and unload removes the exact live instance before shutdown.
- **Plugin location:** `contrib/neo4j-memory/` in this repository (package, manifest,
  tests, bounded dependency declaration). The external checkout is not authoritative.
- **Isolation:** `register_turn_enricher` is listed in `HOST_UNSUPPORTED_CTX_METHODS`; use
  in-process execution until a live-driver proxy protocol exists.

## Verification status

- Core focused tests: 83 passed (`test_plugins_context.py`, memory manager scope,
  and memory provider contracts) — recorded 2026-11-21.
- Plugin tests: 9 test functions across `contrib/neo4j-memory/tests/`. **They do not
  collect from the repo root** (`ModuleNotFoundError: neo4j_memory` / `dashboard`);
  they were written to run from the plugin directory. No current pass/fail claim.
- **Registration is broken in this tree.** `Neo4jEnricher` is a bare dataclass and
  does not inherit `agent.memory_provider.TurnEnricher`; `register_turn_enricher`
  rejects it via `_wrong_type` (`plugins_context.py:105-112`), so no turn is ever
  written. The suite does not cover this path — no test registers through a real
  `PluginContext`.
- Live Neo4j smoke: not reproducible here. Any earlier "write/query/cleanup passed"
  result must have come from the external checkout.
- `scripts/check` (run 2026-11-22): 22 checks, failing `shims`, `backend-imports`,
  and `ruff`. `health` is clean: 0 blocking, 0 advisory.

Current `scripts/check` failures, for the record:

| Check | Finding |
|---|---|
| `shims` | `.gitattributes` differs from `scripts/move/generate_shims.py` output |
| `backend-imports` | `persistence.sqlite` imported outside the storage layer — every hit under `.worktrees/` |
| `ruff` | 3 errors: `enrichment.py:62` (quoted annotation), `topic_context_ledger.py:76` (combinable `if`), `tests/test_api.py:24` (`subprocess.run` without `check`) |

The `.worktrees/` hits are stale worktrees inside the repo being scanned, not
plugin code.

## Upstream docs to consult before plugin work

- `website/docs/developer-guide/plugins/index.md` — plugin kinds, compat contract
- `website/docs/developer-guide/plugins/public-api.md` — generated API surface
- `website/docs/developer-guide/memory-provider-plugin.md` — MemoryProvider ABC guide
- `website/docs/developer-guide/context-engine-plugin.md` — sibling plugin kind
- `plugins/AGENTS.md` — in-tree policy, boundary lint, host isolation rules
- `plugin-catalog/README.md` — catalog admission rules
