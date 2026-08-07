# Engineering Roadmap

Current as of milestone **IM-02**. Update item status in place as work lands; don't leave completed
items undated. See [ARCHITECTURE.md](ARCHITECTURE.md) for the factual basis behind each item, and
[SESSION_STATE.md](SESSION_STATE.md) for the live snapshot of exactly where the repository is right now.

## Status legend
`OPEN` — not started · `DONE` — completed and verified · `PROPOSED` — designed, not implemented ·
`ACCEPTED` — decided, implementation may proceed · `BLOCKED` — cannot start until a dependency is resolved

---

## Completed

| Milestone | Description | Commit(s) |
|---|---|---|
| **RC-12** | Recovery baseline — validated release candidate; the `main` baseline this branch builds on | `a21b3ca` |
| **FE-01** | Enterprise sidebar integration, styling, and accessibility fixes | `8fd7b1d`, `d2bafee` |
| **FIX-01** | Restored the four ticket views (`DashboardView`, `TicketListView`, `TicketCreateView`, `TicketDetailView`) deleted by FE-01's final commit; recovered application startup and the test suite (12/12 passing). Full root cause in [INCIDENT_LOG.md](INCIDENT_LOG.md), INC-001. | `7180078` |
| **DOC-01** | Established the engineering knowledge base — README, ARCHITECTURE, ROADMAP, INCIDENT_LOG, PM-02 design, WORKFLOW under `docs/engineering/` | `83f9182` |
| **PM-00.1 / DOC-01 update** | Added `SESSION_STATE.md` and `ADR-009`; restructured `ROADMAP.md`/`WORKFLOW.md` around milestone tracking and the permanent AI workflow sequence | `311c913` |
| **ADR-009** | Problem Management architecture decision — **ACCEPTED**. Build inside `apps/service_desk`, not `apps/problem_management`; one Problem owns exactly one RCA via `problem.rca`. See [ADR/ADR-009-Problem-Management-Architecture.md](ADR/ADR-009-Problem-Management-Architecture.md) | decision recorded in `311c913`; implemented in `8d30023`, `4c7a37c` |
| **PM-02.1** | Problem Management domain models — `Problem`, `ProblemHistory`, `RootCauseAnalysis` (+ `FiveWhys`, `FishboneFactor`, `Evidence`, `Action`, `Approval`), migrations `0004`–`0005`, `RootCauseAnalysis.problem` as `OneToOneField` per ADR-009 | `8d30023` |
| **PM-02.2** | `ProblemService` and `ProblemSelector` — full business logic and query layer for Problem Management, mirroring the `TicketService`/`TicketSelector` pattern; not yet wired to any view | `4c7a37c` |
| **IM-01** | Fixed Create/Detail ticket template defects found during frontend audit: `create.html` rendered a nonexistent `category` field and omitted real `urgency`/`request_type`/`tags` fields; `detail.html` compared status/priority against uppercase literals that never matched the real lowercase `Ticket` choices (status/priority badge coloring was silently dead), referenced a nonexistent `ticket.attachment`, and used unloaded Bootstrap Icons classes. 4 new regression tests added. | `23a2e8d` |
| **IM-02** | Incident Dashboard stabilization. `IncidentDashboardView` had **no URL route at all** (fully unreachable, beyond the previously-known missing template) and used an **unscoped queryset** (`Ticket.objects`, bypassing RBAC — a Requester would have seen every ticket system-wide). Fixed: added `service_desk:incident_dashboard` route, created `service_desk/incidents.html`, scoped the base queryset through `get_ticket_queryset(user)`, corrected `status__in`/`priority__in` to real lowercase choices (`"UNASSIGNED"`/`"CRITICAL"` were never valid), and moved the categorization queries into 3 new `TicketSelector` methods (`get_active_tickets`, `get_resolved_or_closed_tickets`, `get_high_priority_tickets`) instead of inlining ORM filters in the view. 6 new regression tests (RBAC scoping + correct categorization + reachability). | *(this commit)* |

## Current

- **Enterprise ITSM Master Development Program** — multi-milestone effort per the accepted execution
  authority: Phase 1 Incident Management completion, Phase 2 Problem Management UI, Phase 3 architecture
  prep for Change/Knowledge/CMDB/Asset/Reporting/Automation modules. Worked milestone-by-milestone, each
  fully inspected/designed/implemented/tested/documented/committed locally per
  [WORKFLOW.md](WORKFLOW.md); pushes remain gated on explicit approval regardless of local commit cadence.

## Next — Phase 1: Incident Management completion

Ticket *is* the Incident record in this codebase (`IncidentDashboardView` already filters `Ticket`
directly rather than a separate model) — Phase 1 extends the existing `Ticket`/`TicketService` machinery,
it does not introduce a parallel Incident model.

1. **IM-03** — `OPEN`. Wire `TicketService` into the mutation-side views (`TicketCreateView` and any
   future assign/status-change views still bypass it, calling the ORM/security policies directly) — the
   read side of this is now partially established: IM-02 already composes `TicketSelector` methods with
   the RBAC-scoped `get_ticket_queryset(user)` queryset in `IncidentDashboardView`, which is the pattern
   IM-03 should extend to `TicketService` on the write side.
2. **IM-04** — `OPEN` — **needs an architecture decision before implementation, not a guess.** "Work
   notes", "Attachments", and "Requester confirmation" from the Phase 1 feature list each imply a real
   schema/behavior choice not yet made:
   - Work notes: does this reuse `TicketHistory.EVENT_COMMENT` (already implemented via
     `TicketService.add_comment`) with a visibility flag added, or is it a distinct concept from
     requester-facing comments?
   - Attachments: `Ticket` has no file field today. Needs a decision on storage backend, size/type limits,
     and whether it's a single `FileField` or a related `TicketAttachment` model (multiple files).
   - Requester confirmation: does closing require the requester to confirm resolution (a real workflow
     gate), or is it advisory only? This changes `TicketService.close_ticket`'s preconditions.

   Flagging these now rather than inventing model/behavior changes silently.
3. **CI-01** — `OPEN`. Populate the three empty GitHub Actions workflow files
   (`.github/workflows/django-tests.yml` at minimum) to run `manage.py check` and `manage.py test` on
   every push/PR — exactly what would have caught the FIX-01 regression (INC-001) automatically.
4. **SEC-01** — `OPEN`. Move `SECRET_KEY` out of `ticketing/settings.py` into an environment variable;
   gate `DEBUG` behind an env flag; add a `.env.example`.

## Next — Phase 2: Problem Management UI

Blocked on nothing architecturally (ADR-009 accepted, PM-02.1/PM-02.2 done) — next concrete step is
views/urls/templates/forms wiring `ProblemService`/`ProblemSelector` into a Problem dashboard, RCA
interface, known-error workflow, and incident-linking UI, per
[DESIGN_PM-02_PROBLEM_MANAGEMENT.md](DESIGN_PM-02_PROBLEM_MANAGEMENT.md). One open item carried over:
Requester-role visibility into Problems (§7 of that doc) still needs an explicit answer before
`security/policies.py` gets a `get_problem_queryset`.

## Future — Phase 3: Enterprise modules

Large capability areas, not yet scoped into concrete design work. Several correspond to directories that
already exist under `apps/` as dead scaffolding (ARCHITECTURE.md §2) — "future" here means *design and
build properly*, not "the files already exist so it's in progress." None of these have an ADR, a design
doc, or a target milestone number yet.

- Deployment
- Monitoring
- Reporting
- CMDB
- Knowledge Base
- Asset Management
- Change Management
- Release Management

## Backlog / Technical Debt

Tracked, unscheduled. Pull into "Next" when prioritized. (The `IncidentDashboardView` template/filter/
routing/RBAC defects that used to be listed here were fixed in **IM-02** — see Completed, above.)

- **`OPEN`** — `DashboardView` (the plain one at `service_desk:dashboard`, not `IncidentDashboardView`)
  has no `get_context_data` at all, but its template (`service_desk/dashboard.html`) expects
  `total_tickets`/`open_tickets`/`resolved_tickets`/`recent_tickets` — every one of those renders as the
  template's `|default:"0"` fallback or an empty state today. Found during IM-02 inspection; left
  out of scope since IM-02 was specifically about `IncidentDashboardView`. Same fix shape as IM-02: base
  on `get_ticket_queryset(user)`, use `TicketSelector`/`dashboard_statistics()`.
- **`OPEN`** — Delete the dead duplicate template files found during the IM-01 frontend audit:
  `templates/navbar.html` (byte-identical to the live `templates/includes/navbar.html`) and
  `templates/sidebar.html` (a stale, diverged duplicate of the live `templates/includes/sidebar.html`).
  Neither is referenced by `base.html` or any other live template — confirmed by diff, not assumed.
- **`OPEN`** — Resolve the `models.py`/`models/` and `views.py`/`views/` collisions in
  `apps/service_desk/` (ARCHITECTURE.md §4) by deleting the dead side of each. Low risk since the dead
  files are already confirmed unreachable — do it as its own isolated change, verified with `manage.py
  check` + full test run.
- **`OPEN` — scope decision needed from repo owner** — Decide the fate of the ~59 unregistered scaffolded
  apps under `apps/` (ARCHITECTURE.md §2): commit to building specific ones out properly, or remove them
  to cut noise and reduce the risk of someone wiring one in without realizing it has no tests. Several of
  the "Future" items above will draw on specific ones of these once scoped.
- **`OPEN`** — Add test coverage for `TicketService`, `TicketSelector`, and `DashboardSelector`/
  `dashboard_service` business logic — currently only RBAC authorization is tested. Note
  `dashboard_service.py` and `dashboard_selector.py` are currently empty files; decide whether to
  implement or delete them before writing tests against them.
- **`OPEN`** — Reconcile or formally deprecate the `develop` branch (ARCHITECTURE.md §7) — missing ~130
  files present on `main`/this branch, diverged since the second commit in repository history.
- **`OPEN`** — Clean up stale rollback tags and merged `origin/arena/*` remote branches once confirmed
  unneeded.
