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
| **Current Milestone** | IM-04 — Work Notes, Attachments, Requester Confirmation (DONE) |
| **Current Sprint** | All approved milestones complete. The execution order (record → PM-03 → IM-04) is fully delivered. |
| **Current Objective** | All items in the repository owner's explicit execution order are complete. Next priorities should be drawn from ITSM_ROADMAP.md P1/P2. |
| **Overall Repository Health** | **Improving, still mixed.** Core `service_desk` app is healthy (`manage.py check` clean, 80/80 tests passing, migrations in sync, zero drift). `ticketing/settings.py` no longer hardcodes secrets/DEBUG/hosts (SEC-01). CI runs on every push/PR (CI-01) from a real `requirements.txt` (DEP-01). The `models.py`/`views.py` file-collision hazard is resolved (ARCH-01). RBAC has `get_problem_queryset` (Requester: none) and Technicians see unassigned tickets too (ADR-010, RBAC-01). Problem Management is fully reachable end-to-end (PM-03). Incident Management is fully complete including work notes, attachments, and requester confirmation (IM-04). Surrounding repository still has scaffolding debt (~59 unregistered apps, unchanged — a separate, larger scope decision). Full detail: [ARCHITECTURE.md](ARCHITECTURE.md). |

## Git Status

| | |
|---|---|
| **Current Branch** | `feature/incident-management-dashboard` |
| **Working Tree Status** | PM-03 changes about to be committed locally as of this update (see Unpushed Commits) |
| **Ahead / Behind Origin** | 10 / 0 before this session's PM-03 commit, verified via `git rev-list --left-right --count` |
| **Latest Commit prior to this update** | `98ea39b` — "ADR-010 record and implement Problem/Technician visibility decisions" |

**Note on process continuity:** this session was interrupted mid-write while finishing SEC-01's documentation
(caught mid-edit of this file's own predecessor state). The repository owner committed the SEC-01 code
directly during that gap (`bf89826`) and added one follow-up commit (`56c98bc`) that this session did not
write. Both were verified against the actual repository before continuing — not assumed from the CI-01
prompt's claimed baseline — per this file's own "never assume, always verify" rule.

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
| **IM-01** | Fixed `create.html`/`detail.html` template defects (wrong field set, dead uppercase status/priority comparisons, unloaded icon library, dead `ticket.attachment` reference); added 4 regression tests | `23a2e8d` |
| **IM-02** | Incident Dashboard stabilization: added the missing `service_desk:incident_dashboard` URL route (view was previously 100% unreachable), created `service_desk/incidents.html`, scoped the base queryset through `get_ticket_queryset(user)` (previously unscoped — an RBAC gap), corrected `status__in`/`priority__in` to real lowercase `Ticket` choices, added 3 new `TicketSelector` methods (`get_active_tickets`, `get_resolved_or_closed_tickets`, `get_high_priority_tickets`); added 6 regression tests | `1aed27d` |
| **IM-03** | Incident Lifecycle Completion, schema-free portion: wired `TicketService` into 5 new views (`TicketAssignView`, `TicketStatusChangeView`, `TicketCommentView`, `TicketCloseView`, `TicketReopenView`) plus `TicketCreateView` now creates through `TicketService.create_ticket`; `TicketDetailView` renders real `TicketHistory` and a workflow control panel instead of a hardcoded stub; fixed `assign_ticket` losing the previous assignee on reassignment; added 11 regression tests. The 3 schema-dependent items (work notes visibility, attachments, requester confirmation) were asked about directly and went unanswered — deliberately not implemented, not guessed at. | `ea82610` |
| **SEC-01** | `ticketing/settings.py` hardened: `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` moved to env vars (stdlib only), production refuses to start without a real `DJANGO_SECRET_KEY`, `.env.example` added. Full detail: ROADMAP.md. Code was written this session but committed by the repository owner directly during a process interruption (see note above) — content matches what this session built. | `bf89826` |
| *(follow-up, not a numbered milestone)* | `.gitignore` hardened against accidental credential commits (`AI_Agentina` paths) — verified nothing was ever actually exposed in history or the working tree. | `56c98bc` |
| **CI-01** | GitHub Actions CI pipeline — see Completed table in ROADMAP.md for full detail. `django-tests.yml` and `security-scan.yml` now actually run; `deployment.yml` stays a documented no-op per explicit instruction. | `c173415` |
| **ITSM-ROADMAP** | Full 9-module ITSM capability audit, P0–P3 prioritization, sprint plan — see [ITSM_ROADMAP.md](ITSM_ROADMAP.md). Approved by the repository owner; now the standing execution order. | `073f7f9` |
| **DEP-01** | Dependency manifest: `requirements.txt` (`Django==5.2.16`) added; both CI workflows switched from an inline pinned install to `pip install -r requirements.txt` with pip caching. See ROADMAP.md for full detail. | `c140d25` |
| **ARCH-01** | Resolved the `models.py`/`models/` and `views.py`/`views/` file-collision hazard (the exact class of bug that caused INC-001). Re-verified which side was live before touching anything, grepped for direct references to the dead paths (none found), deleted `apps/service_desk/models.py` and `apps/service_desk/views/`. Verified before and after: import resolution unchanged, `check` clean, zero migration drift, 44/44 tests pass. | `14f36e6` |
| **ADR-010** | Recorded the three ITSM_ROADMAP.md P0-item-3 decisions, given directly by the repository owner. See [ADR/ADR-010-Visibility-and-IM-04-Scope-Decisions.md](ADR/ADR-010-Visibility-and-IM-04-Scope-Decisions.md). | `98ea39b` |
| **RBAC-01** | Implemented ADR-010 Decisions 1 & 2: `get_problem_queryset` added (Requester → none); `get_ticket_queryset`'s Technician branch widened to assigned-or-unassigned; `Problem*PermissionMixin` set added; `create_roles.py` grants Technician/Manager/Admin the new `*_problem` permissions. Updated 2 tests whose assertions encoded the old Technician rule (not regressions) plus added 1 new self-assignment test. 45/45 tests pass. | `98ea39b` |
| **PM-03** | Problem Management UI — see the full entry in ROADMAP.md's Completed table. 13 new views, 13 URL routes, 1 form, 3 templates. Verified twice: a rollback-wrapped manual transaction exercising every view end-to-end, then 9 automated tests. 54/54 tests pass. Problem Management is now fully reachable, matching Incident Management's shape. | *(this session, see Unpushed Commits)* |
| **IM-04** | Incident Management Completion — Work Notes, Attachments, Requester Confirmation (ADR-010, Decision 3). **Work Notes:** new `EVENT_WORK_NOTE` event type, `TicketService.add_work_note()`, `TicketWorkNoteView` (change_ticket-gated), filtered from Requester's history view. **Attachments:** new `TicketAttachment` model, `TicketService.add_attachment()` with extension allowlist + size cap, upload/download views scoped through RBAC, `EVENT_ATTACHMENT` audit trail. **Requester Confirmation:** new `awaiting_confirmation` status in `STATUS_FLOW` (`resolved → awaiting_confirmation → closed`), service-layer enforcement that only `created_by` may close, `TicketRequestConfirmationView` for Technician/Manager, separate confirmation card on detail page visible to Requester. 2 migrations (0006, 0007), 4 new views, 4 new URL routes, 25 new automated tests (80/80 total passing). | *(this session)* |

## Unpushed Commits

Commits through `311c913` were committed **and pushed** by the repository owner directly (outside any AI
session) — confirmed via `git log --oneline origin/...` matching local, author
`Zw3liy <goodwill00765@gmail.com>`. `23a2e8d` (IM-01), `1aed27d` (IM-02), `ea82610` (IM-03), `bf89826`
(SEC-01), `56c98bc` (credential-cleanup follow-up), `c173415` (CI-01), `073f7f9` (ITSM-ROADMAP), `c140d25`
(DEP-01), `14f36e6` (ARCH-01), and `98ea39b` (ADR-010 + RBAC-01) are all local-only, unpushed — two of
them were committed by the repository owner directly, not by this session, but remain unpushed same as
the rest. As of this update, **PM-03's changes are about to be committed locally** under the standing
local-commit authorization for this program (push still requires separate explicit approval — see
[WORKFLOW.md](WORKFLOW.md)). Re-run `git status` /
`git rev-list --left-right --count origin/feature/incident-management-dashboard...HEAD` rather than
trusting this section once further commits land — it will go stale the moment the next milestone starts.

## Current Roadmap Item

- **Priority:** IM-04 — Work Notes, Attachments, Requester Confirmation (DONE).
- **Reason:** Last item in the repository owner's explicit execution order (record → PM-03 → IM-04). All three features implemented per ADR-010 Decision 3.
- **Dependencies:** None remaining.
- **Expected completion:** **Complete.** 80/80 tests pass, `check` clean, migrations applied, zero drift.

## Open Decisions

### Problem Management location — `apps/service_desk` vs. `apps/problem_management`

- **Status:** **RESOLVED.** ADR-009 accepted. Implemented inside `apps/service_desk` (`8d30023`, `4c7a37c`).

### Requester-role visibility into Problems (PM-02 design)

- **Status:** **RESOLVED** — ADR-010, Decision 1. Requesters cannot access Problem records at all;
  `get_problem_queryset` implemented in RBAC-01, mirroring `get_ticket_queryset`'s shape for the other
  three roles.

### IM-04 — Work notes / Attachments / Requester confirmation semantics (Phase 1)

- **Status:** **RESOLVED and IMPLEMENTED.** ADR-010, Decision 3. All three features built in IM-04.
  See the IM-04 entry in the Completed table.

### Technician visibility of unassigned tickets (found during IM-03)

- **Status:** **RESOLVED** — ADR-010, Decision 2. Technicians see assigned tickets plus *all* unassigned
  tickets (not scoped to a department/queue — no such field exists on the data model to scope narrower,
  and inventing one wasn't authorized). Implemented in RBAC-01. Flagged as worth revisiting if
  system-wide unassigned visibility proves too broad in practice.

## Known Blockers

- **Scaffolding debt:** ~59 of ~60 apps under `apps/` are unregistered, untested dead code (ARCHITECTURE.md §2). Not a blocker to current work, but a standing risk that someone wires one in without realizing it has no tests or service-layer discipline.
- **`develop` branch divergence:** diverged since the second commit in repository history, missing ~130 files present on `main`. Not a blocker to this branch's work, but unresolved.
- **Dead duplicate templates:** `templates/navbar.html` (identical to live `templates/includes/navbar.html`) and `templates/sidebar.html` (stale duplicate of live `templates/includes/sidebar.html`) — found during IM-01's audit, not yet removed.
- **RCA sub-model creation UI missing:** `FiveWhys`/`FishboneFactor`/`Evidence`/`Action`/`Approval` render read-only on the Problem detail page (PM-03) but have no creation UI — `ProblemService` has no methods to create them. Flagged as a follow-up, not scheduled in P0–P3.
- **`DashboardView` (plain, not Incident) has no context data:** its template expects ticket stats that are never supplied — found during IM-02 inspection, left out of scope since IM-02 was specifically about `IncidentDashboardView`. Same fix shape applies (`get_ticket_queryset` + `TicketSelector`).
- **`templates/tickets/edit.html` is dead, incompatible scaffolding:** uses `esd-*` CSS classes not defined anywhere in the loaded stylesheet, references `ticket.ticket_number`/`form.requester_name`/`form.work_email`/`form.attachment`, none of which exist on the real `Ticket` model or `TicketCreateForm`. Not wired to any view. Confirmed during IM-03 inspection — do not resurrect as-is when IM-04's attachments get built.

## Recent ADRs

- **ADR-009 — Problem Management Architecture** *(ACCEPTED)*: Problem Management lives inside `apps/service_desk`; one Problem owns exactly one RCA via `problem.rca`. Implemented in `8d30023`/`4c7a37c`.
- **ADR-010 — Visibility and IM-04 Scope Decisions** *(ACCEPTED)*: Requesters cannot access Problems; Technicians see assigned + unassigned tickets; IM-04 (Work Notes, Attachments, Requester Confirmation) all approved for implementation, with technical shape recorded for each. See [ADR/ADR-010-Visibility-and-IM-04-Scope-Decisions.md](ADR/ADR-010-Visibility-and-IM-04-Scope-Decisions.md).

## Next Recommended Tasks

Highest priority first, following the repository owner's explicit execution order — see
[ROADMAP.md](ROADMAP.md) for full detail and status tracking:

1. **IM-04 is DONE.** No further items in the approved execution order.
2. Fix `DashboardView`'s missing context data (same shape as IM-02) — opportunistic cleanup, not in the approved execution order.
3. Get a scope decision on the ~59 unregistered scaffold apps (ITSM_ROADMAP.md P2/P3 territory).
4. Consider a service + UI pass for RCA sub-model creation (`FiveWhys`/`FishboneFactor`/`Evidence`/`Action`/`Approval`) — currently read-only, flagged in PM-03 as an explicit gap, not scheduled.
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

**Previous session summary:** IM-03 — inspected the full incident lifecycle surface first
(`TicketService`, `TicketHistory`, security mixins, `MEDIA_ROOT` config, `templates/tickets/edit.html`)
and produced design findings before writing code, per the milestone's own instruction. Asked three direct
questions (work notes visibility, attachments model shape, requester confirmation) via a structured
prompt — **none were answered**, so none of the three were implemented or guessed at; they remain open
(see Open Decisions). Implemented only the unambiguous, no-new-decision part: wired the fully-built but
previously-unused `TicketService` into 5 new views (`TicketAssignView`, `TicketStatusChangeView`,
`TicketCommentView`, `TicketCloseView`, `TicketReopenView`) plus routed `TicketCreateView` through
`TicketService.create_ticket`; `TicketDetailView` now renders real `TicketHistory` and an
assignment/status/close/reopen control panel (gated on `perms.service_desk.change_ticket`) instead of a
hardcoded "No updates yet" stub. Fixed a real audit bug: `assign_ticket` recorded the new assignee on
reassignment but never the previous one. Discovered and documented (not fixed) two further items: a
Technician cannot see an unassigned ticket at all under the current RBAC policy (by design or gap — asked,
not decided), and `templates/tickets/edit.html` is dead Arena-era scaffolding using an unloaded CSS system
and nonexistent form fields — flagged so it isn't mistaken for a starting point when attachments get built.
Added `apps/service_desk/test_suite/test_ticket_workflow.py` (11 new tests) — 33/33 total passing. That
session was interrupted mid-write while finishing SEC-01's documentation; the repository owner committed
the SEC-01 code directly (`bf89826`) plus one credential-hygiene follow-up (`56c98bc`) during the gap.

**Previous session summary:** CI-01 — verified the interruption's aftermath against the actual
repository first (didn't just trust the next prompt's claimed baseline): confirmed `bf89826`/`56c98bc`
were real, authored by the repository owner, and that the `AI_Agentina` credential material referenced in
`56c98bc` was never actually present in git history or the working tree (preventive `.gitignore` entry,
not a live leak). Inspected `.github/workflows/` (all three files 0 bytes), confirmed no
`requirements.txt`/`pyproject.toml`/`Pipfile` exists anywhere, and scanned every first-party import under
`apps/service_desk/`/`ticketing/` to confirm the tested codebase only needs Django itself (this dev
machine has dozens of unrelated globally-installed packages — anthropic, fastapi, celery, playwright,
etc. — none of them used). Wrote `django-tests.yml` (checkout → setup-python 3.14 → install Django
5.2.16, pinned → `check` → `makemigrations --check --dry-run` → `test`) and `security-scan.yml` (same
setup → `manage.py check --deploy`, Django's built-in production-readiness check; confirmed locally it
exits 0 with warnings-only under default dev settings, so it's informational, not build-blocking, on
expected dev-mode findings). Left `deployment.yml` as a documented no-op per explicit instruction.
Validated all three YAML files parse correctly (`pyyaml` installed transiently for this check only, not
added to the repo). Caught `ROADMAP.md`/`SESSION_STATE.md` up to reflect SEC-01/the credential follow-up/
CI-01 together, since the interruption had left them stale. Committed locally under the standing
per-milestone authorization; not pushed.

**Previous session summary:** ITSM-ROADMAP + DEP-01 — performed a full 9-module ITSM capability
audit (`docs/engineering/ITSM_ROADMAP.md`), verifying every claim by inspection (grep for actual usages,
file-size checks) rather than assuming from directory names; confirmed Incident and Problem Management are
the only areas with real implementation, every other capability's scaffold is empty. Roadmap approved by
the repository owner with an explicit P0→P1→P2→P3 execution order. Started P0: added `requirements.txt`
(`Django==5.2.16`, the one verified runtime dependency) and switched both CI workflows from an inline
pinned install to `pip install -r requirements.txt` with pip caching. Verified locally: the manifest
installs cleanly, `check`/`makemigrations --check`/`test` (44/44) all still pass, both workflow YAML files
re-validated. Committed locally under the standing per-milestone authorization; not pushed.

**Previous session summary:** ARCH-01 — re-verified (didn't trust the earlier finding blindly)
which side of each collision was live: `import apps.service_desk.models`/`views` confirmed unchanged
resolution (`models/__init__.py`, `views.py`), grepped the whole `apps/service_desk/` tree for any direct
reference to the dead paths by name (none found beyond the expected package-level import), then deleted
`apps/service_desk/models.py` (dead flat file, ~315 lines) and `apps/service_desk/views/` (dead directory,
two 0-byte files, no `__init__.py`). Verified again after deletion: import resolution unchanged,
`manage.py check` clean, zero migration drift, 44/44 tests still pass. Updated `ARCHITECTURE.md` §4
(marked the hazard RESOLVED with what was actually done, corrected a stale "three migrations" claim to
five while already in that section) and `ROADMAP.md`/`SESSION_STATE.md` accordingly. Committed locally
under the standing per-milestone authorization; not pushed. P0 items 1 and 2 done; item 3 (the three
decisions) had been asked for twice and gone unanswered both times.

**Previous session summary:** ADR-010 + RBAC-01 — the repository owner gave the three decisions
directly (Requesters cannot access Problems; Technicians see assigned + unassigned tickets; build all
three IM-04 features). Recorded them in `ADR/ADR-010-Visibility-and-IM-04-Scope-Decisions.md`, including
the technical shape chosen for each since the request specified behavior, not schema, and flagged one real
gap along the way: "permitted queues" for Technician visibility has no data-model equivalent to scope
against, so the implementation is unscoped (all unassigned tickets) rather than inventing a new field
without authorization. Implemented the two RBAC-only decisions immediately: `get_problem_queryset` added
to `security/policies.py` (Requester → none, others mirror `get_ticket_queryset`'s shape);
`get_ticket_queryset`'s Technician branch widened to `Q(assigned_to=user) | Q(assigned_to__isnull=True)`;
`Problem*PermissionMixin` set added to `security/mixins.py`; `create_roles.py` updated to grant the new
`*_problem` permissions to Technician/Manager/Administrator only. Fixed 2 tests whose assertions encoded
the *old* Technician rule (not regressions), and added a new self-assignment test. 45/45 tests pass.
Committed locally under the standing per-milestone authorization; not pushed.

**Last session summary (this update):** PM-03 — built the complete Problem Management UI on top of the
models/services/selectors/RBAC that already existed. Inspected `ProblemService`/`ProblemSelector` first to
confirm exactly what was already supported (full lifecycle, RCA auto-creation, known-error gating, ticket
linking, repeat-incident detection) and, just as importantly, what wasn't (no methods to create
`FiveWhys`/`FishboneFactor`/`Evidence`/`Action`/`Approval` records) — scoped PM-03 to match reality rather
than inventing new service methods mid-UI-build. Added `ProblemCreateForm`, 13 views (3 CRUD + 10 workflow
actions mirroring the Ticket action-view pattern exactly), 13 URL routes, and 3 templates. Verified the
whole flow twice before calling it done: first a rollback-wrapped manual transaction hitting every view in
sequence (create → assign → investigate → RCA auto-created → root cause → known-error → link ticket →
comment → resolve → close → reopen → unlink → confirmed Requester gets 403) with the transaction rolled
back afterward so nothing touched the real dev database, then a proper automated test module (9 tests:
RBAC visibility for all four roles, the same full lifecycle, template rendering checks). Along the way,
caught and fixed two of my own manual-test setup bugs (a `Group.name` collision, then a role-name mismatch
where I'd used a differently-named test group than what the RBAC check actually looks for) rather than
mistaking either for a real bug in the code under test. 54/54 tests pass, `check` clean, zero migration
drift (no schema change — the models existed since PM-02.1). Updated `DESIGN_PM-02_PROBLEM_MANAGEMENT.md`
to IMPLEMENTED. Deliberately did not add a `Problems` sidebar nav link (consistent with earlier caution
about that file) or creation UI for the RCA sub-models (no service methods exist for them — flagged as a
follow-up, not built speculatively). Committed locally under the standing per-milestone authorization; not
pushed.

**IM-04 is the last item in the given execution order** (record → PM-03 → IM-04) — that's next: Work
Notes, Attachments, and Requester Confirmation, per the technical shape already recorded in ADR-010,
Decision 3.
