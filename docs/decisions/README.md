# Architecture Decision Records (ADRs)

Each ADR captures one real decision: the context, what was decided, and the consequences. One
file per decision, numbered in order. Never edit an old ADR's decision — if something changes,
write a new ADR that supersedes it.

**Format** (copy this for new ADRs):

```
# ADR NNNN — <short title>

- Status: accepted | superseded by ADR XXXX
- Date: YYYY-MM-DD

## Context
What situation forced a decision? Which constraints mattered?

## Decision
What we chose, stated plainly.

## Alternatives considered
What else was on the table, and why we didn't pick it.

## Consequences
What this makes easier, and what it costs or rules out.
```

## Index
- 0001 — Local-first, FFmpeg, config-driven, file-based re-runnable stages
- 0002 — One source clip, many outputs
- 0003 — English-facing channel, music-first (commentary later)
- 0004 — Royalty-free music only, organized into preset pools
- 0005 — Shorts via blurred-background fit
- 0006 — Folder-based presets now; AI content-understanding later
