# Engineering Roadmap

Current as of milestone **ARCH-01**. Update item status in place as work lands; don't leave completed
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
| **IM-02** | Incident Dashboard stabilization. `IncidentDashboardView` had **no URL route at all** (fully unreachable, beyond the previously-known missing template) and used an **unscoped queryset** (`Ticket.objects`, bypassing RBAC — a Requester would have seen every ticket system-wide). Fixed: added `service_desk:incident_dashboard` route, created `service_desk/incidents.html`, scoped the base queryset through `get_ticket_queryset(user)`, corrected `status__in`/`priority__in` to real lowercase choices (`"UNASSIGNED"`/`"CRITICAL"` were never valid), and moved the categorization queries into 3 new `TicketSelector` methods (`get_active_tickets`, `get_resolved_or_closed_tickets`, `get_high_priority_tickets`) instead of inlining ORM filters in the view. 6 new regression tests (RBAC scoping + correct categorization + reachability). | `1aed27d` |
| **IM-03** | Incident Lifecycle Completion (schema-free portion only — see "Next" for the 3 deferred, decision-blocked items). `TicketService` — fully built since before this milestone but entirely unused by any view — is now wired into 5 new views: `TicketAssignView`, `TicketStatusChangeView`, `TicketCommentView`, `TicketCloseView`, `TicketReopenView`, plus `TicketCreateView` now creates through `TicketService.create_ticket` instead of `ModelForm.save()`. `TicketDetailView` now renders real `TicketHistory` (previously a hardcoded "No updates yet" stub) and exposes an assignment/status-change/close/reopen control panel gated on `perms.service_desk.change_ticket`. Fixed a real audit gap: `TicketService.assign_ticket` recorded the new assignee on reassignment but never the previous one (unlike `unassign_ticket`, which did). Every new view resolves its ticket through `get_ticket_queryset(request.user)`, not a raw pk lookup — confirmed this also surfaces a pre-existing RBAC property worth knowing: a Technician cannot see an *unassigned* ticket at all (`get_ticket_queryset`'s Technician branch is `assigned_to=user`-only, by design) — initial assignment can only be performed by a Manager (department-scoped) or Administrator. 11 new regression tests. | `ea82610` |
| **SEC-01** | Production security hardening of `ticketing/settings.py` — `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` moved to env vars (stdlib `os.environ` only, no new dependency) with defaults that exactly reproduce the previous hardcoded local-dev behavior when unset; **`SECRET_KEY` refuses to fall back to the (permanently git-history-exposed) dev key when `DJANGO_DEBUG` is false — raises `ImproperlyConfigured` instead**, verified empirically by actually running `manage.py check` both ways. Added always-on hardening (`X_FRAME_OPTIONS=DENY`, `SECURE_CONTENT_TYPE_NOSNIFF`), production-only cookie/SSL hardening gated on `not DEBUG`, opt-in `SECURE_HSTS_SECONDS` (default 0, deliberately not auto-enabled — misconfigured HSTS can lock out a domain for a long time), and a minimal `LOGGING` config so security-relevant events aren't silently swallowed. Added `.env.example` (documents every new variable) plus a `!.env.example` negation in `.gitignore`, since the existing `.env.*` glob would otherwise have ignored it too. 11 new regression tests (env-parsing helpers + confirming resolved defaults are unchanged). Explicitly **not done**: no dependency added for `.env` autoloading, no DB backend change, no email/SMTP alerting config, no `requirements.txt` — each flagged as its own separate, larger decision rather than folded in silently. Committed by the repository owner directly (matches this session's built content). A small immediate follow-up, also owner-committed, added `.gitignore` entries (`deployment/releases/AI_Agentina/.env`, `AI_Agentina/*Key*`, `*API key*`) preventing accidental commit of unrelated local credential material — verified during CI-01 inspection that none of it was ever actually present in git history or the working tree. | `bf89826`, `56c98bc` |
| **CI-01** | GitHub Actions CI pipeline. All three workflow files were 0 bytes. `django-tests.yml`: checkout → `setup-python` (3.14) → install Django (pinned to the exact local version, `5.2.16`) → `manage.py check` → `makemigrations --check --dry-run` → `manage.py test`, on every push/PR. `security-scan.yml`: same setup, runs `manage.py check --deploy` (Django's built-in production-readiness check — flags exactly what SEC-01 hardened; confirmed locally it exits 0 with warnings-only under default dev settings, so it reports without blocking on expected dev-mode findings). `deployment.yml` left as a documented no-op per explicit instruction — comment-only, no `on`/`jobs` keys, will show as an invalid/skipped workflow in the Actions UI by design. **No `requirements.txt`/`pyproject.toml`/`Pipfile` exists anywhere in this repository** (confirmed exhaustively) — every first-party import under `apps/service_desk/`/`ticketing/` was scanned and only uses stdlib + Django, so both real workflows install Django directly, pinned, rather than inventing a dependency manifest. | `c173415` |
| **ITSM-ROADMAP** | Full repository audit across all 9 core ITSM capability areas plus AI/Notification/Security cross-cutting concerns — see [ITSM_ROADMAP.md](ITSM_ROADMAP.md). Confirms Incident and Problem Management are the only areas with real implementation; every other capability's scaffold is empty at the model level (verified, not assumed). P0–P3 prioritization with reasoning, module dependency map, sprint-level plan. Approved by the repository owner; this document is the standing execution order going forward. | `073f7f9` |
| **DEP-01** | Dependency manifest. Added `requirements.txt` at repo root (`Django==5.2.16` — the one verified runtime dependency). Updated both CI workflows to `pip install -r requirements.txt` (with `cache: pip`, now viable since a lockfile-equivalent exists) instead of the CI-01-era inline pinned install. Verified locally: `pip install -r requirements.txt` reproduces a working environment, `check`/`makemigrations --check`/`test` (44/44) all still pass, both workflow YAML files re-validated as syntactically correct. Deliberately did **not** add a dependency-audit tool (e.g. `pip-audit`) even though one is now technically possible — that's a new package/tool addition, out of this item's scope, needs its own approval. | `c140d25` |
| **ARCH-01** | Resolved the `models.py`/`models/` and `views.py`/`views/` file-collision hazard (ARCHITECTURE.md §4) that already caused INC-001. Re-verified which side was live (unchanged from the original finding — `models/` package live, `views.py` flat file live), grepped for any direct reference to the dead paths (none found), then deleted `apps/service_desk/models.py` (the dead flat file) and `apps/service_desk/views/` (the dead directory). Verified both before and after: import resolution unchanged, `manage.py check` clean, zero migration drift, 44/44 tests pass. | *(this commit)* |

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

1. **IM-04** — `OPEN` — **blocked on 3 unanswered decisions, asked directly and not yet answered.**
   "Work notes", "Attachments", and "Requester confirmation" from the Phase 1 feature list each imply a
   real schema/behavior choice:
   - Work notes: does this reuse `TicketHistory.EVENT_COMMENT` (already implemented via
     `TicketService.add_comment`, now exposed via `TicketCommentView` as of IM-03) with a visibility flag
     added, or stay undifferentiated (current state — every comment visible to anyone who can see the
     ticket)?
   - Attachments: `Ticket` has no file field today (`MEDIA_ROOT`/`MEDIA_URL` are already configured in
     `ticketing/settings.py`, unused). Needs a decision on a single `FileField` vs. a related
     `TicketAttachment` model. **Do not wire in `templates/tickets/edit.html`'s existing attachment UI** —
     confirmed during IM-03 inspection to be dead Arena-era scaffolding: it uses `esd-*` CSS classes that
     don't exist in the loaded stylesheet, and references `ticket.ticket_number`/`form.requester_name`/
     `form.work_email`, none of which exist on the real `Ticket` model or `TicketCreateForm`.
   - Requester confirmation: hard workflow gate (new field, `close_ticket` precondition change) or
     advisory only (no schema change)?

   These were asked directly (three-question prompt) during IM-03 and went unanswered — still open, not
   decided by default. Do not guess at them.
2. **`OPEN` — possible RBAC gap, needs a decision, not a silent fix.** `get_ticket_queryset`'s Technician
   branch (`security/policies.py`) is `Ticket.objects.filter(assigned_to=user)` — a Technician cannot see
   an unassigned ticket at all, confirmed during IM-03. This may be intentional (triage/routing is a
   Manager/Administrator responsibility) or a gap (technicians usually need to see and claim an unassigned
   department queue in ITSM tooling). Not touched — changing RBAC visibility rules deserves the same
   explicit-decision treatment as the IM-04 items, not a silent expansion.

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
