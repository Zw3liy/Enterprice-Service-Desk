# Session State — AI / Engineer Handoff

**This document is the permanent handoff point for any future session — human or AI.** Read this file,
[ROADMAP.md](ROADMAP.md), and [ADR/](ADR/) before touching the repository. Do not rely on prior chat
history; if this file and a chat transcript disagree, this file is correct and the transcript is stale —
update this file, don't defer to the conversation.

This file must be updated at the end of every engineering session (see WORKFLOW.md, "Session Handoff"
step). An out-of-date `SESSION_STATE.md` is itself a defect — treat it as one if found.

---

## Repository State

| | |
|---|---|
| **Project Name** | Enterprise Service Desk |
| **Repository** | `https://github.com/Zw3liy/Enterprice-Service-Desk.git` |
| **Current Branch** | `feature/incident-management-dashboard` |
| **Default Branch** | `main` |
| **Current Version** | No formal semantic version tag on current HEAD. Nearest tag is `fe12-rollback` (5 commits behind HEAD); last real release tag in history is `v1.0.1-frontend-stabilized`, well upstream of this branch. Treat this branch as unreleased/pre-tag work. |
| **Last Updated** | 2026-08-07 |

## Current Engineering Phase

| | |
|---|---|
| **Current Milestone** | PM-00.1 — Engineering Knowledge Base Enhancement |
| **Current Sprint** | Documentation & engineering governance (no feature work in this sprint) |
| **Current Objective** | Make the repository self-describing: any future session should be able to start from `docs/engineering/` alone, without conversation history |
| **Overall Repository Health** | **Mixed.** Core `service_desk` app is healthy (`manage.py check` clean, 12/12 tests passing, migrations in sync). Surrounding repository has significant scaffolding debt (~59 unregistered apps), two live file-collision hazards, empty CI, and hardcoded secrets. Full detail: [ARCHITECTURE.md](ARCHITECTURE.md). |

## Git Status

| | |
|---|---|
| **Current Branch** | `feature/incident-management-dashboard` |
| **Working Tree Status** | Clean (`nothing to commit, working tree clean`) |
| **Ahead / Behind Origin** | Ahead by **1** commit, behind by **0** |
| **Latest Commit** | `83f9182` — "DOC-01: Establish Enterprise Engineering Knowledge Base" |
| **Latest Local Commit** | `83f9182` (see above) |
| **Latest Remote Commit** (`origin/feature/incident-management-dashboard`) | `7180078` — "FIX-01: Restore Service Desk views and recover application startup" |

**How to re-check:** `git status`, `git rev-list --left-right --count origin/feature/incident-management-dashboard...HEAD`, `git log --oneline -5`.

## Completed Engineering Milestones

| Milestone | Description | Commit(s) |
|---|---|---|
| **RC-12** | "Recovery baseline — validated release candidate" — the `main` branch baseline this feature branch is built on | `a21b3ca` |
| **FE-01** | Enterprise sidebar integration, styling, and accessibility fixes | `8fd7b1d`, `d2bafee` |
| **FIX-01** | Restored `DashboardView`, `TicketListView`, `TicketCreateView`, `TicketDetailView` deleted by FE-01's final commit; recovered application startup and the test suite (12/12 passing again) | `7180078` |
| **DOC-01** | Established the engineering knowledge base (`docs/engineering/`: README, ARCHITECTURE, ROADMAP, INCIDENT_LOG, PM-02 design, WORKFLOW) | `83f9182` |

## Unpushed Commits

| Commit | Message |
|---|---|
| `83f9182` | DOC-01: Establish Enterprise Engineering Knowledge Base |

`origin/feature/incident-management-dashboard` is still at `7180078` (FIX-01). `83f9182` (DOC-01) exists
locally only — it has **not** been pushed. This is expected: the automatic `post-commit` push hook that
used to push every commit unprompted was disabled (see [WORKFLOW.md](WORKFLOW.md)) *before* DOC-01 was
committed, so DOC-01 stayed local as intended, pending explicit push approval. Re-check `git status` /
`git rev-list --left-right --count origin/feature/incident-management-dashboard...HEAD` rather than
trusting this table blindly once further commits land.

## Current Roadmap Item

- **Priority:** PM-00.1 — Engineering Knowledge Base Enhancement (this milestone).
- **Reason:** Prior milestones (FIX-01, DOC-01) proved the documentation-as-source-of-truth model works, but the knowledge base lacked a single handoff document, an ADR for the one open architecture question (Problem Management placement), and forward-looking roadmap/workflow structure. Without this, every new session would need to re-derive repository state from chat history, which is explicitly what this governance track is meant to eliminate.
- **Dependencies:** None — pure documentation, no code dependencies.
- **Expected completion:** This session (documentation only, no commit until explicit approval per Quality Rules).

## Open Decisions

### Problem Management location — `apps/service_desk` vs. `apps/problem_management`

- **Status:** Awaiting ADR approval.
- **Detail:** [ADR-009-Problem-Management-Architecture.md](ADR/ADR-009-Problem-Management-Architecture.md) documents both options and recommends Option A (build inside `apps/service_desk`). Not implemented. No code exists for PM-02 yet.

### Requester-role visibility into Problems (PM-02 design)

- **Status:** Unresolved, blocking PM-02 implementation regardless of which ADR-009 option is chosen.
- **Detail:** See [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](DESIGN_PM-02_PROBLEM_MANAGEMENT.md) §7. Default proposed is "Requester sees no problems," but this needs an explicit answer before `security/policies.py` (or its equivalent in a dedicated app) is written.

## Known Blockers

- **Scaffolding debt:** ~59 of ~60 apps under `apps/` are unregistered, untested dead code (ARCHITECTURE.md §2). Not a blocker to current work, but a standing risk that someone wires one in without realizing it has no tests or service-layer discipline.
- **File-collision hazard, unresolved:** `apps/service_desk/models.py` vs `apps/service_desk/models/` (package wins, flat file is dead) and `apps/service_desk/views.py` vs `apps/service_desk/views/` (flat file wins, package is dead, opposite resolution direction). See ARCHITECTURE.md §4. Tracked as ROADMAP item, not yet fixed.
- **CI is a placeholder:** all three `.github/workflows/*.yml` files are 0 bytes. The FIX-01 regression would have been caught automatically had this existed. Tracked as ROADMAP item.
- **Configuration debt:** hardcoded `SECRET_KEY` committed to version control, `DEBUG=True` not environment-gated. Tracked as ROADMAP item.
- **`IncidentDashboardView` follow-on defects (kept intentionally, not yet fixed):** missing template `service_desk/incidents.html`; `status__in`/`priority__in` filters use values (`"UNASSIGNED"`, `"CRITICAL"`, uppercase generally) that don't match the real lowercase `Ticket` choices. See INCIDENT_LOG.md, "Known follow-on defects."
- **`develop` branch divergence:** diverged since the second commit in repository history, missing ~130 files present on `main`. Not a blocker to this branch's work, but unresolved.

## Recent ADRs

- **ADR-009 — Problem Management Architecture** *(PROPOSED, this milestone)*: recommends building PM-02 inside `apps/service_desk` rather than reviving the dead `apps/problem_management` scaffold. Full reasoning in the ADR itself. Not yet approved or implemented.

## Next Recommended Tasks

Highest priority first — see [ROADMAP.md](ROADMAP.md) for full detail and status tracking:

1. Get ADR-009 approved (or overridden) so PM-02 has an unblocked target location.
2. Resolve the Requester-visibility open question in the PM-02 design.
3. Implement PM-02 per the approved design, once both of the above are resolved.
4. Stand up real CI (`django-tests.yml` at minimum) — this is cheap and prevents a repeat of FIX-01.
5. Resolve the `models.py`/`views.py` collision hazards as their own isolated change.
6. Move `SECRET_KEY`/`DEBUG` to environment configuration.
7. Get a scope decision on the ~59 unregistered scaffold apps.

## Required Checks Before Commit

Always perform, in order:

1. `git status`
2. `git diff` (and `git diff --cached` once staged)
3. `python manage.py check`
4. `python manage.py test`
5. Verify migrations — `python manage.py makemigrations --check --dry-run <app>` if models changed
6. Verify imports — especially around the known `models.py`/`views.py` collision hazards (ARCHITECTURE.md §4)
7. Verify URLs — confirm every view referenced in a `urls.py` actually exists (this is exactly what FIX-01 was fixing)
8. Verify templates — confirm every `template_name` a view references actually exists on disk
9. Verify documentation updates — if the change affects architecture, roadmap status, or leaves a new open decision, update the relevant file in `docs/engineering/` in the same change

## Required Checks Before Push

Confirm all of the following before ever running `git push`:

- Working tree clean
- Tests passing (`manage.py test` green)
- Documentation updated to reflect what was actually committed
- ADR updated/added if the change altered architecture
- **Explicit user approval received for this specific push** — a past approval to commit or to push a different commit does not carry forward

## Session Handoff

At the end of every engineering session, update this file with:

- **Current repository state** — re-run the Git Status commands above and update the table
- **Completed work** — what actually landed (commits, files), not what was attempted
- **Outstanding work** — anything left mid-flight
- **Next recommended task** — update the priority list above if it changed
- **Known blockers** — add, resolve, or re-confirm entries above
- **Date** — update "Last Updated" in the Repository State table

**Last session summary (this update):** PM-00.1 — added this file, `ADR/ADR-009-Problem-Management-Architecture.md`, and updated `ROADMAP.md` and `WORKFLOW.md`. No application code touched. Nothing committed yet — awaiting approval per this milestone's Quality Rules.
