# ADR 0002 — One source clip, many outputs

- Status: accepted
- Date: 2026-06-24

## Context
The channel publishes a **mix of Shorts and long-form** (the owner's chosen format). Shorts are
the growth funnel; long-form earns. Producing each format by hand from scratch would not scale to
the target of daily Shorts.

## Decision
Treat each raw clip as a single source that fans out into multiple outputs from one edit: a 16:9
master, a 9:16 Short, and (bundled with others) a long-form montage. The expensive/creative
choices are made once; formats are derived deterministically. (Same "one master, many children"
idea as the ORIGIN project.)

## Alternatives considered
- **Separate hand-edits per format:** maximum control per output, but far too slow for daily
  volume and duplicates effort.
- **Shorts-only:** simplest, but Shorts RPM is tiny — long-form is where monetization happens, so
  long-form can't be dropped.

## Consequences
- One editing pass yields every format — the basis of the daily-volume workflow.
- Output formats stay visually consistent because they share a source edit.
- Some outputs are compromises (a Short reframed from 16:9 is not natively shot vertical) —
  accepted, and mitigated by the blurred-background fit (ADR 0005).
