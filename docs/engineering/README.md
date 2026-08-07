# Engineering Documentation — Source of Truth

**Milestone:** PM-00
**Purpose:** convert accumulated engineering knowledge about this repository into permanent, versioned documentation.

## Charter

From this milestone forward, these documents are the authoritative reference for the state of the
Enterprise Service Desk codebase. Engineering decisions — what to build, what to fix, what to avoid —
should cite these files, not prior chat sessions. Chat history is not durable and should not be treated
as a record of fact once a finding has been written here.

When new investigation surfaces a fact that contradicts a document in this folder, **update the
document in the same change**, don't leave the correction only in conversation.

## Index

| Document | Covers |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | What actually runs vs. what is unregistered scaffolding; known file-collision hazards; configuration state |
| [ROADMAP.md](ROADMAP.md) | Prioritized engineering roadmap, current as of this milestone |
| [INCIDENT_LOG.md](INCIDENT_LOG.md) | Record of production-breaking regressions found and fixed, with root cause |
| [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](DESIGN_PM-02_PROBLEM_MANAGEMENT.md) | Approved-pending design for the Problem Management / RCA feature — not yet implemented |

## Provenance

The findings captured here come from direct inspection of the repository as of **2026-08-07**, on branch
`feature/incident-management-dashboard` (HEAD `d2bafee`, plus one uncommitted fix to `apps/service_desk/views.py`
restoring the four deleted ticket views — see INCIDENT_LOG.md). Every claim in these documents was verified
against the actual filesystem, git history, or a running Django management command — not inferred from
memory or assumption. Where an earlier verbal assessment turned out to be wrong (see ARCHITECTURE.md,
"Model resolution"), the correction is recorded rather than silently dropped.

These documents describe a snapshot. Re-verify claims against the live repository before relying on them
for a decision with real consequences — see each document's own guidance on how to re-check its claims.
