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
| **Current Version** | No formal semantic version tag on current HEAD. Nearest tag is `fe12-rollback`; last real release tag in history is `v1.0.1-frontend-stabilized`, well upstream of this branch. Treat this branch as unreleased/pre-tag work. |
| **Last Updated** | 2026-08-07 |

## Current Engineering Phase

| | |
|---|---|
| **Current Milestone** | IM-01 — Ticket Create/Detail template defect fixes (first milestone of the Enterprise ITSM Master Development Program) |
| **Current Sprint** | Phase 1: Incident Management completion (see [ROADMAP.md](ROADMAP.md)) |
| **Current Objective** | Work the ITSM program milestone-by-milestone — inspect, design, implement, test, document, commit locally per milestone; push only on explicit approval regardless of local commit cadence (see [WORKFLOW.md](WORKFLOW.md)) |
| **Overall Repository Health** | **Improving, still mixed.** Core `service_desk` app is healthy (`manage.py check` clean, 16/16 tests passing, migrations in sync, zero drift). Problem Management domain (ADR-009, PM-02.1, PM-02.2) is implemented but not yet wired to any view. Surrounding repository still has scaffolding debt (~59 unregistered apps), two live file-collision hazards, empty CI, and hardcoded secrets. Full detail: [ARCHITECTURE.md](ARCHITECTURE.md). |

## Git Status

| | |
|---|---|
| **Current Branch** | `feature/incident-management-dashboard` |
| **Working Tree Status** | IM-01 changes staged for commit as of this update (see Unpushed Commits) |
| **Ahead / Behind Origin** | Was 0 / 0 immediately before this session's IM-01 commit(s) |
| **Latest Commit prior to this session** | `311c913` — "DOC-01 update engineering workflow and PM architecture documentation" |

**How to re-check:** `git status`, `git rev-list --left-right --count origin/feature/incident-management-dashboard...HEAD`, `git log --oneline -10`.

## Completed Engineering Milestones

| Milestone | Description | Commit(s) |
|---|---|---|
| **RC-12** | "Recovery baseline — validated release candidate" — the `main` branch baseline this feature branch is built on | `a21b3ca` |
| **FE-01** | Enterprise sidebar integration, styling, and accessibility fixes | `8fd7b1d`, `d2bafee` |
| **FIX-01** | Restored `DashboardView`, `TicketListView`, `TicketCreateView`, `TicketDetailView` deleted by FE-01's final commit; recovered application startup and the test suite | `7180078` |
| **DOC-01** | Established the engineering knowledge base (`docs/engineering/`) | `83f9182` |
| **PM-00.1 / DOC-01 update** | `SESSION_STATE.md`, `ADR-009` added; `ROADMAP.md`/`WORKFLOW.md` restructured | `311c913` |
| **ADR-009** | Problem Management architecture — **ACCEPTED**: build inside `apps/service_desk`, one Problem owns one RCA via `problem.rca` | decided in `311c913`, implemented in `8d30023`/`4c7a37c` |
| **PM-02.1** | `Problem`, `ProblemHistory`, `RootCauseAnalysis` (+ `FiveWhys`, `FishboneFactor`, `Evidence`, `Action`, `Approval`) models, migrations `0004`–`0005` | `8d30023` |
| **PM-02.2** | `ProblemService`, `ProblemSelector` — business logic and query layer, not yet wired to any view | `4c7a37c` |
| **IM-01** | Fixed `create.html`/`detail.html` template defects (wrong field set, dead uppercase status/priority comparisons, unloaded icon library, dead `ticket.attachment` reference); added 4 regression tests | *(this session, see Unpushed Commits)* |

## Unpushed Commits

Note the commits above through `311c913` were committed **and pushed** by the repository owner directly
(outside any AI session) — confirmed via `git log --oneline origin/...` matching local, author
`Zw3liy <goodwill00765@gmail.com>`. As of this update, **IM-01's changes are about to be committed
locally** under the standing local-commit authorization for this program (push still requires separate
explicit approval — see [WORKFLOW.md](WORKFLOW.md)). Re-run `git status` /
`git rev-list --left-right --count origin/feature/incident-management-dashboard...HEAD` rather than
trusting this section once further commits land — it will go stale the moment the next milestone starts.

## Current Roadmap Item

- **Priority:** IM-01 — Ticket Create/Detail template defect fixes (Phase 1, Incident Management completion).
- **Reason:** The frontend audit performed before starting Phase 1 found the live Create Ticket and Ticket Detail templates were out of sync with the real form/model — building bigger incident-lifecycle features on top of a known-broken create/detail page would compound the problem, so it was fixed first.
- **Dependencies:** None — template-and-test-only change, no model/migration impact.
- **Expected completion:** This session; committed locally under the standing per-milestone local-commit authorization, push pending separate explicit approval.

## Open Decisions

### Problem Management location — `apps/service_desk` vs. `apps/problem_management`

- **Status:** **RESOLVED.** ADR-009 accepted. Implemented inside `apps/service_desk` (`8d30023`, `4c7a37c`).

### Requester-role visibility into Problems (PM-02 design)

- **Status:** Still unresolved — not yet blocking anything since Problem Management has no views/URLs yet, but will block Phase 2 (Problem Management UI) as soon as `security/policies.py` needs a `get_problem_queryset`.
- **Detail:** See [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](DESIGN_PM-02_PROBLEM_MANAGEMENT.md) §7. Default proposed is "Requester sees no problems," needs an explicit answer before Phase 2 work starts.

### IM-04 — Work notes / Attachments / Requester confirmation semantics (Phase 1)

- **Status:** Unresolved, blocking IM-04 specifically (not IM-02/IM-03).
- **Detail:** See ROADMAP.md, Phase 1 item 3, for the three specific sub-decisions needed (work note visibility model, attachment storage design, whether requester confirmation is a hard workflow gate). Do not guess at these — they're schema/behavior decisions, not implementation details.

## Known Blockers

- **Scaffolding debt:** ~59 of ~60 apps under `apps/` are unregistered, untested dead code (ARCHITECTURE.md §2). Not a blocker to current work, but a standing risk that someone wires one in without realizing it has no tests or service-layer discipline.
- **File-collision hazard, unresolved:** `apps/service_desk/models.py` vs `apps/service_desk/models/` (package wins, flat file is dead) and `apps/service_desk/views.py` vs `apps/service_desk/views/` (flat file wins, package is dead, opposite resolution direction). See ARCHITECTURE.md §4. Tracked as ROADMAP item, not yet fixed.
- **CI is a placeholder:** all three `.github/workflows/*.yml` files are 0 bytes. The FIX-01 regression would have been caught automatically had this existed. Tracked as ROADMAP item CI-01.
- **Configuration debt:** hardcoded `SECRET_KEY` committed to version control, `DEBUG=True` not environment-gated. Tracked as ROADMAP item SEC-01.
- **`IncidentDashboardView` follow-on defects (kept intentionally, not yet fixed):** missing template `service_desk/incidents.html`; `status__in`/`priority__in` filters use values (`"UNASSIGNED"`, `"CRITICAL"`, uppercase generally) that don't match the real lowercase `Ticket` choices. See INCIDENT_LOG.md, "Known follow-on defects"; now tracked as ROADMAP item IM-02.
- **`develop` branch divergence:** diverged since the second commit in repository history, missing ~130 files present on `main`. Not a blocker to this branch's work, but unresolved.
- **Dead duplicate templates:** `templates/navbar.html` (identical to live `templates/includes/navbar.html`) and `templates/sidebar.html` (stale duplicate of live `templates/includes/sidebar.html`) — found during IM-01's audit, not yet removed.
- **`ProblemService`/`ProblemSelector` unused:** implemented (PM-02.2) but no view/URL calls them yet — Phase 2 work.

## Recent ADRs

- **ADR-009 — Problem Management Architecture** *(ACCEPTED)*: Problem Management lives inside `apps/service_desk`; one Problem owns exactly one RCA via `problem.rca`. Implemented in `8d30023`/`4c7a37c`.

## Next Recommended Tasks

Highest priority first — see [ROADMAP.md](ROADMAP.md) for full detail and status tracking:

1. IM-02 — fix `IncidentDashboardView`'s missing template and invalid status/priority filter values.
2. IM-03 — wire `TicketService`/`TicketSelector` into the actual ticket views (currently unused).
3. Get an explicit answer on the three IM-04 sub-decisions (work notes, attachments, requester confirmation) before implementing them.
4. Resolve Requester-visibility into Problems before starting Phase 2 UI work.
5. Stand up real CI (`django-tests.yml` at minimum) — cheap, prevents a repeat of FIX-01.
6. Resolve the `models.py`/`views.py` collision hazards as their own isolated change.
7. Move `SECRET_KEY`/`DEBUG` to environment configuration.
8. Get a scope decision on the ~59 unregistered scaffold apps.

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

**Last session summary (this update):** IM-01 — fixed `templates/tickets/create.html` (removed nonexistent
`category`/`requester_email`/`attachment` fields, added missing `urgency`/`request_type`/`tags`; swapped
unloaded Bootstrap Icons for Font Awesome) and `templates/tickets/detail.html` (fixed uppercase-vs-lowercase
status/priority badge comparisons that were silently dead, removed dead `ticket.attachment` block, swapped
icon library). Added `apps/service_desk/test_suite/test_ticket_templates.py` (4 new tests, 16/16 total
passing). Updated `ADR-009` to ACCEPTED and caught `ROADMAP.md` up to match already-committed work
(PM-00.1 doc update, ADR-009, PM-02.1, PM-02.2 — committed and pushed by the repo owner directly, outside
any AI session, verified via `git log` rather than assumed). Committed locally under the standing
per-milestone authorization; not pushed. Next: IM-02 (fix `IncidentDashboardView`'s template/filter
defects) or IM-03 (wire `TicketService`/`TicketSelector` into views) — see Next Recommended Tasks above.
