# Engineering Roadmap

Current as of milestone **PM-00.1**. Update item status in place as work lands; don't leave completed
items undated. See [ARCHITECTURE.md](ARCHITECTURE.md) for the factual basis behind each item, and
[SESSION_STATE.md](SESSION_STATE.md) for the live snapshot of exactly where the repository is right now.

## Status legend
`OPEN` — not started · `DONE` — completed and verified · `PROPOSED` — designed, not implemented ·
`BLOCKED` — cannot start until a dependency is resolved

---

## Completed

| Milestone | Description | Commit(s) |
|---|---|---|
| **RC-12** | Recovery baseline — validated release candidate; the `main` baseline this branch builds on | `a21b3ca` |
| **FE-01** | Enterprise sidebar integration, styling, and accessibility fixes | `8fd7b1d`, `d2bafee` |
| **FIX-01** | Restored the four ticket views (`DashboardView`, `TicketListView`, `TicketCreateView`, `TicketDetailView`) deleted by FE-01's final commit; recovered application startup and the test suite (12/12 passing). Full root cause in [INCIDENT_LOG.md](INCIDENT_LOG.md), INC-001. | `7180078` |
| **DOC-01** | Established the engineering knowledge base — README, ARCHITECTURE, ROADMAP, INCIDENT_LOG, PM-02 design, WORKFLOW under `docs/engineering/` | `83f9182` |

## Current

- **PM-00.1** — Engineering Knowledge Base Enhancement (this milestone). Adds
  [SESSION_STATE.md](SESSION_STATE.md) as the permanent AI/engineer handoff document, ADR-009 for the
  Problem Management placement decision, and restructures this roadmap and `WORKFLOW.md` so a future
  session can start from documentation alone. Documentation only — no application code touched.

## Next

1. **ADR-009** — `PROPOSED`. Architecture decision for where Problem Management code lives
   (`apps/service_desk` vs. reviving `apps/problem_management`). Recommends `apps/service_desk`. See
   [ADR/ADR-009-Problem-Management-Architecture.md](ADR/ADR-009-Problem-Management-Architecture.md).
   Awaiting approval — nothing implemented.

2. **PM-02** — `BLOCKED` on ADR-009 approval and one open design decision (Requester-role visibility into
   problems — see [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](DESIGN_PM-02_PROBLEM_MANAGEMENT.md) §7). Problem
   Management / Root Cause Analysis feature. Full design already written; not implemented.

3. **CI-01** — `OPEN`. Populate the three empty GitHub Actions workflow files
   (`.github/workflows/django-tests.yml` at minimum) to run `manage.py check` and `manage.py test` on
   every push/PR. This is exactly what would have caught the FIX-01 regression (INC-001) automatically
   instead of requiring manual discovery — highest-leverage low-effort item outstanding.

4. **SEC-01** — `OPEN`. Move `SECRET_KEY` out of `ticketing/settings.py` into an environment variable;
   gate `DEBUG` behind an env flag; add a `.env.example`. Configuration debt flagged in
   [ARCHITECTURE.md](ARCHITECTURE.md) §6.

## Future

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

Tracked, unscheduled. Pull into "Next" when prioritized.

- **`OPEN`** — Create the missing template `templates/service_desk/incidents.html` that
  `IncidentDashboardView` requires, and correct its `status__in`/`priority__in` filter values (currently
  `"OPEN"/"IN_PROGRESS"/"UNASSIGNED"` and `"HIGH"/"CRITICAL"` — none match the real lowercase `Ticket`
  choices; `"UNASSIGNED"` and `"CRITICAL"` aren't valid choices at all). See INCIDENT_LOG.md, "Known
  follow-on defects."
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
