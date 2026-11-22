# docs/

Project documentation for the Neo4j memory workstream. Entry point:
[`neo4j-memory-plugin.md`](neo4j-memory-plugin.md) — compiled inventory, known
bugs, and the plugin-ification plan.

Historical run-record docs (moved here from `neo4j-memory/workflow/neo4j-memory-context/`;
their prototype paths and test commands describe the 2026-11-19 isolated experiment, not
the current plugin checkout):

- `IDEA.md` - product idea
- `BRIEF.md` - workflow brief and invariants
- `SYNTHESIS.md` - design synthesis
- `IMPLEMENTATION_PLAN.md` - prototype plan and acceptance cases
- `REVIEW_GATE.md` - deterministic acceptance evidence
- `HANDOFF.md` - prototype state and verification commands
- `TOOL_PROVENANCE.md` - tooling/skill provenance for the workflow run

The prototype those records describe survives as
`contrib/neo4j-memory/neo4j_memory/topic_context_ledger.py` (with
`tests/test_ledger.py`), not at the `agent/topic_context_ledger.py` path the
run-records cite.

Current planning docs:

- `neo4j-memory-config-plan.md` - config surface: plugin settings, secrets, CLI/Desktop
- `superpowers/specs/2026-11-21-neo4j-memory-config-only-design.md` - config-only scope decision
- `superpowers/plans/2026-11-21-neo4j-memory-config-only.md` - task breakdown for that scope

Note: `hermes-agent` upstream keeps user docs in `website/docs/` (Docusaurus).
This directory is project-local working documentation, not part of the docs
site build.
