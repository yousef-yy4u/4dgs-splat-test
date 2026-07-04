---
name: project-ssot-log
description: "PROJECT.md is the project's single source of truth — keep it updated every turn a decision changes"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7fa889b7-cdf5-419f-9a65-e527b3ffcb4b
---

The user wants a single canonical project log: `/home/sov2/projects/4dgs/PROJECT.md` holds the full project (vision, architecture, plan, feature specs, edge cases, open questions, next steps, and a Decision Log of how ideas evolved). A `CLAUDE.md` in the project root enforces the standing rule.

**Why:** the project is greenfield/architecture-only and the design has evolved a lot across conversation; the user wants the reasoning trail and current state captured in ONE place, not scattered.

**How to apply:** every time a decision/plan/spec/idea changes — in conversation or files — update PROJECT.md in the SAME turn (edit the section + append a dated Decision Log entry + bump the date). Don't delete superseded reasoning; mark "superseded by Dx". This is a semantic update only the model can do — NOT a settings.json hook. Treat as default behavior; don't make the user ask each time. See [[asset-library-architecture]], [[stealth-agent-glasses-product]].
