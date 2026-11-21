# Shared Brief: Evolving, Non-Blocking Context Injection

## Goal

Explore clever, implementable ways for Hermes memory to auto-inject useful topic context across turns without blocking or hanging the active conversation thread. The context should evolve over turns so an observer can understand the active topic(s).

## Invariants

- Mnemosyne remains the primary conversational-memory provider.
- Neo4j remains a secondary graph/index layer; it is not the orchestration system of record.
- Injection must be asynchronous, bounded, cancellable or deadline-aware, and failure-isolated.
- Do not persist hidden chain-of-thought. Use observable turns, tool metadata, topic summaries, entities, relationships, timestamps, and provenance.
- Preserve prompt-cache safety: do not mutate prior context or toolsets mid-turn.
- No source or test edits in this exploration wave.

## Deliverable

Each worker should provide independently falsifiable findings, candidate designs, tradeoffs, and a concrete recommendation. Include source locations or URLs, assumptions, failure modes, and a minimal next experiment.

## Coordination

Workers may challenge or extend one another through the parent, but should begin independently. The parent will reconcile overlaps and contradictions after results arrive.
