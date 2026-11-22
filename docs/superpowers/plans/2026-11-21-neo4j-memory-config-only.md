# Neo4j Memory Config-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the plugin's legacy `HERMES_NEO4J_*` configuration path and use native plugin settings plus Hermes profile-scoped secrets.

**Architecture:** The package `neo4j_memory/__init__.py` owns `register(ctx)`; the plugin root only re-exports it for Hermes' path-based loader. Registration reads ordinary values with `ctx.get_config(key)` and obtains the three credentials with `agent.secret_scope.get_secret` using explicit `NEO4J_MEMORY_*` names. Missing credentials, an unscoped multiplex secret read, disabled config, or missing Neo4j dependency all fail closed.

**Tech Stack:** Python 3.11+, FastAPI plugin surface, lazy Neo4j driver import, pytest, Hermes `PluginContext` and `agent.secret_scope`.

**Spec:** `docs/superpowers/specs/2026-11-21-neo4j-memory-config-only-design.md`

## Global Constraints

- Do not add or read `HERMES_NEO4J_*` variables.
- Ordinary settings live under `plugins.entries.neo4j-memory.settings` and are read through `ctx.get_config(key)`.
- Credentials use profile-scoped `agent.secret_scope.get_secret(name, default=None)`.
- Secret declarations remain the existing `config_schema` fields with explicit `env: NEO4J_MEMORY_URI`, `env: NEO4J_MEMORY_USERNAME`, and `env: NEO4J_MEMORY_PASSWORD`; do not duplicate them in `optional_env` or `requires_env`.
- Catch `UnscopedSecretError` and fail closed; never leak credentials in logs or status.
- Keep the dashboard import fix out of this change; it is a separate follow-up.

## Review Focus

- A multiplexed registration with no active secret scope must not raise; test `UnscopedSecretError` handling in `from_config`.
- A disabled plugin must not import or construct the Neo4j driver; test `enabled: false` before the fake driver is available.
- A missing one of the three optional secrets must return `None`; test partial credentials.
- A complete config must pass the exact profile-scoped names to the secret getter and construct the driver; test all three names.
- Legacy `HERMES_NEO4J_*` variables must have no effect; test with those variables set and no native config.

---

### Task 1: Make the manifest and registration surface native-config-only

**Files:**
- Modify: `contrib/neo4j-memory/plugin.yaml`
- Modify: `contrib/neo4j-memory/neo4j_memory/__init__.py`
- Modify: `contrib/neo4j-memory/__init__.py` only if the re-export needs adjustment
- Test: `contrib/neo4j-memory/tests/test_enrichment.py`

**Interfaces:**
- Consumes: `ctx.get_config(key)`, `agent.secret_scope.get_secret`, `UnscopedSecretError`.
- Produces: package `register(ctx)` that constructs only through `Neo4jEnricher.from_config(config, secret_getter=...)`.

- [ ] **Step 1: Write failing registration tests**

  Add tests asserting that package registration reads ordinary keys through `ctx.get_config`, disabled config registers nothing, partial secrets register nothing, complete secrets construct an enricher, and `UnscopedSecretError` is swallowed.

- [ ] **Step 2: Run the focused tests and confirm failure**

  Run: `\.venv\Scripts\python.exe -m pytest -q contrib/neo4j-memory/tests/test_enrichment.py`

- [ ] **Step 3: Update `plugin.yaml`**

  Keep the existing `type: secret` schema fields and add explicit `env: NEO4J_MEMORY_URI`, `env: NEO4J_MEMORY_USERNAME`, and `env: NEO4J_MEMORY_PASSWORD` mappings. Do not add a second `optional_env` or `requires_env` declaration.

- [ ] **Step 4: Implement package registration**

  In `contrib/neo4j-memory/neo4j_memory/__init__.py`, collect only `enabled`, `database`, `content_max_bytes`, `debug_trace_enabled`, and `trace_max_bytes` with `ctx.get_config(key)`. Pass those ordinary settings to `Neo4jEnricher.from_config`; the factory resolves credentials only through the explicit secret-scope names and fails closed for missing secrets and `UnscopedSecretError`. Keep the root file as a re-export shim.

- [ ] **Step 5: Run the focused tests and confirm they pass**

  Run: `\.venv\Scripts\python.exe -m pytest -q contrib/neo4j-memory/tests/test_enrichment.py`

- [ ] **Step 6: Commit**

  `git add contrib/neo4j-memory/plugin.yaml contrib/neo4j-memory/__init__.py contrib/neo4j-memory/neo4j_memory/__init__.py contrib/neo4j-memory/tests/test_enrichment.py && git commit -m "fix: register neo4j memory from native config"`

### Task 2: Remove the legacy environment construction path

**Files:**
- Modify: `contrib/neo4j-memory/neo4j_memory/enrichment.py`
- Modify: `contrib/neo4j-memory/neo4j_memory/__init__.py`
- Test: `contrib/neo4j-memory/tests/test_enrichment.py`

**Interfaces:**
- Consumes: `Neo4jEnricher.from_config(config, secret_getter=None)`.
- Produces: no `from_environment()` method, no direct `os.getenv` reads, and no `HERMES_NEO4J_*` fallback.

- [ ] **Step 1: Add a regression test for legacy env isolation**

  Set legacy `HERMES_NEO4J_*` variables, provide no native config, and assert registration remains inactive.

- [ ] **Step 2: Remove `from_environment()` and raw env access**

  Delete the compatibility constructor, rewrite/remove `_secret()` so it only calls `get_secret(name, None)`, catch `UnscopedSecretError` explicitly, and remove any fallback call from registration. `from_config()` must not fall back to `config.get("uri")`, `config.get("username")`, or `config.get("password")`. Keep lazy `neo4j` import and no-op behavior intact.

- [ ] **Step 3: Run all plugin tests**

  Run: `\.venv\Scripts\python.exe -m pytest -q contrib/neo4j-memory/tests`

- [ ] **Step 4: Verify forbidden legacy reads**

  Run: `rg -n "HERMES_NEO4J_|from_environment|os\.getenv|config\.get\(\"(uri|username|password)\"" contrib/neo4j-memory --glob "*.py" --glob "!tests/**"`
  Expected: no matches; test fixtures may mention legacy names only to prove they are ignored.

- [ ] **Step 5: Commit**

  `git add contrib/neo4j-memory && git commit -m "fix: remove neo4j memory env fallback"`

### Task 3: Doctor and repository verification

**Files:**
- Test/verify: `contrib/neo4j-memory/plugin.yaml`, `contrib/neo4j-memory/tests/`

**Interfaces:**
- Consumes: completed Tasks 1–2.
- Produces: a doctor-clean, test-green native-config-only plugin.

- [ ] **Step 1: Run the full focused plugin suite**

  Run: `\.venv\Scripts\python.exe -m pytest -q contrib/neo4j-memory/tests`
  Expected: all tests pass; no driver-dependent test requires an installed Neo4j package.

- [ ] **Step 2: Run plugin doctor**

  Run: `hermes plugins doctor contrib/neo4j-memory`
  Expected: no manifest, import, or registration findings.

- [ ] **Step 3: Inspect the final diff and commit status**

  Run: `git diff --check` and `git status --short --branch`.
  Expected: no whitespace errors and only the intended commits/clean tree.
