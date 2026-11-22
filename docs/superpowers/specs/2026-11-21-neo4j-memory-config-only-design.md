# Neo4j Memory Config-Only Design

## Intent

Make the standalone `neo4j-memory` plugin use Hermes' native plugin settings and
profile-scoped secret surface exclusively. The plugin must not define or read a
parallel `HERMES_NEO4J_*` configuration API.

## Goals

- Read ordinary settings through `ctx.get_config(...)`.
- Resolve `uri`, `username`, and `password` through `agent.secret_scope.get_secret`.
  All three remain secrets because a Neo4j URI may embed credentials and must not
  be exposed as ordinary plugin configuration.
- Declare explicit `env: NEO4J_MEMORY_URI`, `env: NEO4J_MEMORY_USERNAME`, and
  `env: NEO4J_MEMORY_PASSWORD` mappings on the existing `type: secret` schema
  fields; these are secret-scope names, not a new `HERMES_*` configuration
  surface. Do not duplicate them in `optional_env`.
- Remove `from_environment()` and all direct `os.getenv` fallback behavior.
- Preserve clean no-op behavior when disabled, incomplete, unscoped under
  multiplexing, or when `neo4j` is not installed.
- Add tests proving disabled config, missing secrets, and successful secret
  resolution.

## Non-goals

- No new core configuration keys or core tools.
- No migration shim for the old `HERMES_NEO4J_*` variables.
- No dashboard API redesign in this change. The separate dashboard import
  failure identified during review remains an independent fix.

## Approach

Use the existing plugin contract:

1. The package `contrib/neo4j-memory/neo4j_memory/__init__.py` owns
   `register(ctx)` and reads ordinary fields with `ctx.get_config(key)`; the
   root file only re-exports it for Hermes' path-based loader.
2. `Neo4jEnricher.from_config()` obtains the three credentials from the active
  Hermes secret scope using the manifest-declared names.
3. Missing credentials and `UnscopedSecretError` both fail closed: construction
   returns `None` and registration does nothing.
4. Tests use a fake secret getter and fake driver; no real credentials or
   network are required.

## Files

- `contrib/neo4j-memory/plugin.yaml`
- `contrib/neo4j-memory/__init__.py`
- `contrib/neo4j-memory/neo4j_memory/enrichment.py`
- `contrib/neo4j-memory/neo4j_memory/__init__.py`
- `contrib/neo4j-memory/tests/test_enrichment.py`

## Verification

- Focused plugin tests pass.
- `hermes plugins doctor contrib/neo4j-memory` passes.
- Repository diff contains no new `HERMES_NEO4J_*` reads; the only declared
  credential names are the explicit `NEO4J_MEMORY_*` secret mappings.
