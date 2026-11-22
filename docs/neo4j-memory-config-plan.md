# Neo4j Memory Native Configuration Plan

## Overview

Give the standalone `neo4j-memory` plugin a first-class Hermes configuration
surface. Users should configure ordinary behavior through the plugin's
`config.yaml` namespace and use Hermes' secret handling for credentials. The
same schema should drive CLI inspection/editing and the Desktop Settings →
Plugins form, while status and diagnostics remain available from native Hermes
commands. Configuration changes must take effect on the next session or
explicit reload; they must not mutate a live turn's prompt/tool surface.

## Architecture decisions

- Keep all Neo4j-specific behavior in the standalone plugin. Core only supplies
  the existing `TurnEnricher` and plugin context seams.
- Store settings under `plugins.entries.neo4j-memory.settings`, accessed through
  `ctx.get_config()` / `ctx.set_config()` with plugin-relative keys.
- Store URI, username, and password as manifest `secret` fields backed by the
  profile secret scope. Do not add new non-secret `HERMES_*` configuration
  variables.
- Default the plugin to disabled. Missing credentials or an unreachable server
  must produce a clear status/diagnostic result and never abort Hermes startup.
- Treat configuration writes as deferred lifecycle changes. The current
  enricher remains stable for the active session; a new session/reload rebuilds
  it from the saved profile configuration.
- Use the manifest `config_schema` as the source of truth so Desktop can render
  the settings form without Neo4j-specific Desktop code.

## Proposed settings

| Key | Type | Default | Surface | Notes |
|---|---|---:|---|---|
| `enabled` | bool | `false` | config + Desktop | Opt-in gate; never inferred from credentials |
| `database` | string | `neo4j` | config + Desktop | Database name |
| `debug_trace_enabled` | bool | `false` | config + Desktop | Stores bounded observable trace metadata |
| `trace_max_bytes` | int | `65536` | config + Desktop | Validate `1..262144` |
| `content_max_bytes` | int | `65536` | config + Desktop | Validate `1..262144` |
| `uri` | secret | unset | config + Desktop | Backed by `NEO4J_MEMORY_URI` |
| `username` | secret | unset | config + Desktop | Backed by `NEO4J_MEMORY_USERNAME` |
| `password` | secret | unset | config + Desktop | Backed by `NEO4J_MEMORY_PASSWORD` |

A `max_pending` setting was proposed but is **not** in the current schema, and
`MemoryManager._submit_background` has no pending-task cap to configure — it
serializes on a single-worker daemon executor.

`debug_trace_enabled` remains independent from `enabled` and never
permits hidden reasoning to be stored.

## Task list

### Phase 1: Configuration contract

#### Task 1: Add the manifest schema

**Description:** Extend the standalone plugin manifest with the settings above,
including labels, descriptions, defaults, numeric bounds, and secret-to-env
mappings.

**Acceptance criteria:**

- [ ] Desktop and generic plugin management can discover every setting from
      `plugin.yaml`.
- [ ] Secret values are masked and never returned as plain config values.
- [ ] Invalid ranges and malformed values are rejected before construction.

**Verification:** Add manifest/schema contract tests and run the plugin test
suite.

**Dependencies:** None.

**Files likely touched:**

- `contrib/neo4j-memory/plugin.yaml`
- `contrib/neo4j-memory/tests/test_config_schema.py`

**Estimated scope:** Small.

#### Task 2: Replace env-only construction with profile config resolution

**Description:** Add a config-based constructor/factory to `Neo4jEnricher`.
Read non-secret values from `ctx.get_config()` and credentials through the
plugin secret scope. Preserve a compatibility path for existing env-backed
profiles during migration, with config taking precedence.

**Acceptance criteria:**

- [ ] Disabled or incomplete configuration returns no enricher without raising.
- [ ] A complete profile config constructs the same bounded
      enricher used by the live smoke test.
- [ ] Existing env settings can be migrated/read once without becoming a new
      core configuration surface.

**Verification:** Unit-test disabled, missing-secret, invalid-range, precedence,
and successful-construction cases.

**Dependencies:** Task 1.

**Files likely touched:**

- `neo4j_memory/enrichment.py`
- `neo4j_memory/__init__.py`
- `tests/test_enrichment.py`

**Estimated scope:** Medium.

### Checkpoint: Configuration foundation

- [ ] Schema and constructor tests pass.
- [ ] No live turn starts a child process or localhost listener.
- [ ] Existing live smoke write/query/cleanup still passes.

### Phase 2: Native user surfaces

#### Task 3: Add plugin CLI commands

**Description:** Register a plugin-owned command tree with `status`, `config`,
and `doctor` subcommands. `status` reports enabled state, selected database,
endpoint, driver reachability, queue/metric counters, and the last
failure class. `config` reads/writes plugin-relative settings through Hermes'
config writer. `doctor` gives actionable remediation without exposing secrets.

**Acceptance criteria:**

- [ ] `hermes neo4j-memory status` is read-only and works when disabled.
- [ ] `hermes neo4j-memory config` never prints secret values.
- [ ] `hermes neo4j-memory doctor` distinguishes disabled, missing credentials,
      unreachable server, and healthy connection.
- [ ] Writes state that a new session/reload is required when applicable.

**Verification:** CLI tests with temporary `HERMES_HOME` and mocked driver;
manual checks for disabled and healthy profiles.

**Dependencies:** Tasks 1-2.

**Files likely touched:**

- `neo4j_memory/cli.py`
- `neo4j_memory/__init__.py`
- `tests/test_cli.py`

**Estimated scope:** Medium.

#### Task 4: Add an in-session status command

**Description:** Register a read-only `/neo4j-memory status` command through the
plugin context. Do not provide a mid-turn enable/disable command; configuration
mutations stay in the CLI/config surfaces and apply on the next session.

**Acceptance criteria:**

- [ ] Status is available only when the plugin is loaded.
- [ ] Output is bounded and useful in CLI, gateway, and ACP contexts.
- [ ] The command does not rebuild the system prompt or tool surface.

**Verification:** Slash-command registry tests and a gateway/ACP serialization
smoke test.

**Dependencies:** Task 3.

**Files likely touched:**

- `neo4j_memory/cli.py`
- `tests/test_cli.py`

**Estimated scope:** Small.

#### Task 5: Enable Desktop Settings through the schema

**Description:** Verify that the manifest schema renders under Settings →
Plugins and that saves round-trip through `plugins.manage settings`. Add only
plugin metadata or descriptions needed for a usable form; do not add a
Neo4j-specific Desktop page.

**Acceptance criteria:**

- [ ] All non-secret settings render with correct controls and help text.
- [ ] Secret fields are masked and profile-scoped.
- [ ] Saving in Desktop produces the same values read by `ctx.get_config()`.

**Verification:** Desktop plugin-settings test or browser smoke test, plus a
config round-trip test against a temporary profile.

**Dependencies:** Tasks 1-3.

**Files likely touched:**

- `plugin.yaml`
- `tests/test_config_schema.py`
- Desktop tests only if the generic schema renderer exposes a defect.

**Estimated scope:** Small.

### Checkpoint: Native surfaces

- [ ] CLI status/config/doctor work from a temporary profile.
- [ ] Desktop schema form round-trips settings.
- [ ] Slash status is read-only and prompt-cache safe.

### Phase 3: Migration, diagnostics, and release

#### Task 6: Migrate existing env-only setups

**Description:** The `HERMES_NEO4J_*` names never existed as an activation path;
`tests/test_enrichment.py::test_legacy_hermes_environment_does_not_activate_plugin`
asserts they are ignored. Migration therefore covers only profiles that enable the
plugin from environment state (`NEO4J_MEMORY_URI` / `_USERNAME` / `_PASSWORD`) with
no `plugins.entries.neo4j-memory.settings` block: read the values once, write the
`enabled`/bounds settings, and leave the secrets where the schema expects them.

**Acceptance criteria:**

- [ ] A profile enabled only by `NEO4J_MEMORY_*` keeps working after upgrade.
- [ ] `HERMES_NEO4J_*` variables remain inert (existing test stays green).
- [ ] Migration can be rerun without changing values or duplicating state.
- [ ] A migration report identifies skipped/invalid values without secrets.

**Verification:** Temporary-profile migration tests and one live read-back.

**Dependencies:** Tasks 1-2.

**Files likely touched:**

- `neo4j_memory/migration.py`
- `neo4j_memory/__init__.py`
- `tests/test_migration.py`

**Estimated scope:** Medium.

#### Task 7: Add operational diagnostics and documentation

**Description:** Document setup, settings, health output, lifecycle timing,
privacy boundaries, and troubleshooting. Add counters for writes, retries,
failures, dropped queue entries, and last error class to `status` without
introducing telemetry.

**Acceptance criteria:**

- [ ] Users can configure and verify the plugin without editing Python or
      guessing environment variables.
- [ ] Documentation states that Neo4j is a secondary sink and no hidden
      reasoning is persisted.
- [ ] Metrics are local diagnostics only and are not sent externally.

**Verification:** Docs drift checks, CLI help snapshot, and live smoke test.

**Dependencies:** Tasks 3-6.

**Files likely touched:**

- `docs/neo4j-memory-plugin.md`
- standalone plugin `README.md`
- plugin tests

**Estimated scope:** Medium.

### Checkpoint: Complete

- [ ] Focused core and standalone plugin tests pass.
- [ ] `scripts/check` passes, or remaining findings are separately tracked and
      explicitly reviewed.
- [ ] Live Neo4j write/query/cleanup smoke passes.
- [ ] No new process or localhost listener is created by normal plugin startup.
- [ ] Config changes are deferred to a new session/reload.

## Dependency graph

```text
manifest schema + secret mapping
            |
            v
config-based enricher factory
       /          \
      v            v
CLI status/config  Desktop schema form
      |
      v
slash status + diagnostics
      |
      v
migration + docs + release verification
```

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Config mutation rebuilds a live agent | High | Defer to next session/reload; never change prompt/tool surface mid-turn |
| Plugin config is read outside profile scope | High | Resolve through `ctx` and profile-scoped secret APIs only |
| Bad settings block Hermes startup | High | Fail closed; report through `status`/`doctor`; keep plugin optional |
| Desktop and CLI schemas drift | Medium | One manifest `config_schema`; test both consumers against it |
| Legacy env profiles stop working | Medium | Idempotent migration/read-through with precedence tests |
| Driver reconnect or retries create hidden process growth | Medium | Keep the driver in-process; bound executor work and expose local counters |
| Schema grows into a graph modeling commitment | Medium | Limit this plan to connection, trace, and queue controls; defer ontology work |

## Open questions

- Should `enabled` default to `false` for every profile, or should an existing
  enabled env configuration be auto-migrated to `true` once?
- Should `doctor` perform a live connection by default, or require `--check`
  to avoid network activity in diagnostics?
- Which Hermes release/version first guarantees the manifest `config_schema`
  and plugin CLI APIs used by this plan?
