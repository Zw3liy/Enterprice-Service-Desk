# ITSM Roadmap — Capability Matrix & Prioritization

Produced by a full repository audit on 2026-08-07, branch `feature/incident-management-dashboard`
(HEAD `c173415`). Every claim below was verified directly against the filesystem/git history in this
pass — not carried forward from memory of earlier sessions. See [ARCHITECTURE.md](ARCHITECTURE.md) for
the general "what's registered vs. dead scaffolding" ground truth this matrix builds on, and
[ROADMAP.md](ROADMAP.md) for the milestone-by-milestone execution log this document prioritizes against.

**Standing fact that shapes everything below:** `INSTALLED_APPS` registers exactly one app,
`apps.service_desk`. Every other directory under `apps/` — roughly 60 of them, one per ITSM capability
area you'd expect from the folder names — is unregistered, unmigrated, and in every case checked during
this audit, contains either a 0-byte `models.py` or an empty `models/` package. They are not "partially
built and disconnected"; they are empty. This audit does not re-litigate that (ARCHITECTURE.md §2 already
established it) — it evaluates each ITSM capability on what's *actually reachable*, and only mentions the
matching dead scaffold directory as a "does not count as evidence" note where someone might otherwise
assume it does.

---

## Capability Matrix

| Capability | Status | Evidence | Missing Work |
|---|---|---|---|
| **Incident Management** | **PARTIAL** (core lifecycle complete, enterprise controls absent) | `apps/service_desk/models/ticket.py`, `ticket_history.py`; `services/ticket_service.py` (create/assign/reassign/status-flow/comment/close/reopen, all transaction-safe, full history); `selectors/ticket_selector.py`; 9 views incl. `IncidentDashboardView` + 5 workflow action views; `templates/tickets/*`, `service_desk/incidents.html`; RBAC via `get_ticket_queryset`; 44 tests total, ~28 incident-specific | No SLA/due-date field on `Ticket` at all (grep-verified). No escalation. No priority *calculation* (priority is a manual field, not derived from impact×urgency or similar). No notifications (zero `send_mail`/`EmailMessage` usage anywhere, no `EMAIL_BACKEND` configured). No reporting beyond the incidents dashboard's raw counts. IM-04 (work notes visibility, attachments, requester confirmation) still blocked on unanswered questions. |
| **Problem Management** | **PARTIAL** (data + business logic complete, zero UI) | `apps/service_desk/models/problem.py`, `problem_history.py`, `root_cause_analysis.py` (`RootCauseAnalysis`, `FiveWhys`, `FishboneFactor`, `Evidence`, `Action`, `Approval`); `services/problem_service.py`, `selectors/problem_selector.py` — full parity with the Ticket service/selector pattern, including RCA auto-creation, known-error gating, ticket linking; migrations `0004`–`0005` | **Zero views, URLs, forms, or templates.** Grep-confirmed: no reference to "Problem" anywhere in `urls.py`, `views.py`, `forms/`, or `security/`. No `get_problem_queryset` — Requester-visibility into Problems is still an open, asked-and-unanswered question (blocks writing that policy function at all). This is the single largest "fully-designed, zero-risk-to-build" gap in the platform — same shape as what IM-03 did for Incident Management. |
| **Service Request Management** | **MISSING** as a distinct capability | `RequestType` model exists (`Incident`/`Service Request`/`Access Request`/`Change Request` per its docstring) — but it is only a categorization `ForeignKey` on `Ticket`, not a separate workflow. `apps/service_catalog/` exists, `models.py` is 0 bytes. | No request catalog, no approval workflow, no fulfillment process distinct from the generic ticket lifecycle, no request templates. Today, a "service request" is just a `Ticket` with a particular `RequestType` — indistinguishable in workflow from an incident. |
| **Change Management** | **MISSING** entirely | `apps/change_management/models.py` is 0 bytes. `templates/itil/changes.html` exists but is unreferenced by any view. | No change record model, no risk assessment, no approval/CAB workflow, no scheduling. Nothing to evaluate — this hasn't been started. |
| **CMDB / Asset Management** | **MISSING** entirely | `apps/cmdb/`, `apps/inventory/`, `apps/warranty/` all confirmed empty (no model content). `apps/service_desk/cmdb/` subpackage (`models.py`) is also 0 bytes — this is the dead in-app scaffolding noted in ARCHITECTURE.md §3, not real capability. `templates/cmdb/*` (11 files) exist, unreferenced. | No Configuration Item model, no relationships, no ownership, no asset lifecycle. `Ticket`/`Problem` have no CI linkage field. The earlier PM-02 selector work (`repeat_incident_detection`) explicitly had to substitute department/text-overlap matching *because* no CI concept exists — documented at the time, still true. |
| **SLA Management** | **MISSING** entirely | `apps/sla_engine/models.py` is 0 bytes. `apps/service_desk/sla/` subpackage is also 0 bytes (dead in-app scaffolding, ARCHITECTURE.md §3). `Ticket` has no due-date/response-time/resolution-time field (grep-verified against `models/ticket.py`). `templates/sla/*` (5 files) exist, unreferenced. | No SLA policy model, no timers, no breach detection, no escalation triggers. This is a prerequisite for real "escalation" in Incident Management — there's currently nothing to escalate *against*. |
| **Knowledge Management** | **MISSING** entirely | `apps/knowledge_management/` and `apps/service_desk/knowledge/` subpackage both confirmed empty. `templates/knowledge/*` (6 files) exist, unreferenced. | No article model, no search, no linkage from incidents/problems to knowledge articles (would naturally attach to `Problem.workaround`/`root_cause` once this exists), no approval workflow for articles. |
| **Reporting and Analytics** | **MISSING** beyond raw dashboard counts | `IncidentDashboardView`/`TicketSelector.dashboard_statistics()` produce simple counts (open/resolved/priority breakdown). `ProblemSelector.dashboard_statistics()` similarly built but unreachable (no view). `apps/analytics_engine/`, `apps/analytics_platform/`, `apps/service_desk/reporting/` subpackage all confirmed empty. `templates/reports/*`, `templates/reporting/*` (11 files total) exist, unreferenced. | No scheduled/exportable reports, no cross-module analytics (e.g. problem-to-incident ratio, SLA compliance — SLA doesn't exist yet either), no executive dashboard. The data layer for *ticket* stats exists and is tested; nothing else does. |
| **AI Features** | **MISSING**, extensive dead scaffolding | `apps/ai_engine/`, `ai_gateway/`, `ai_knowledge/`, `ai_search/`, `ai_automation/`, `ai_assistant/` — six separate directories, every one confirmed empty at the model level. `templates/ai/*`, `templates/ai_operations/*` exist, unreferenced. | Nothing built. Given Incident/Problem Management's own build order (models → services → views), and that even SLA/Notifications/Knowledge — arguably prerequisite context for anything AI would classify or recommend against — don't exist yet, this is correctly last-priority. |
| **Notification Features** | **MISSING** | `apps/service_desk/notifications/` subpackage confirmed empty (dead in-app scaffolding). Zero `send_mail`/`EmailMessage` calls anywhere in the live codebase; no `EMAIL_BACKEND` configured in `ticketing/settings.py`. `TicketHistory`/`ProblemHistory` provide a complete in-app audit trail, but nothing pushes that information anywhere — no email, no webhook, no external channel. | No notification model, no delivery mechanism, no user preference/subscription model, no email backend configuration. This blocks meaningful escalation (an escalation nobody is told about isn't an escalation) and requester confirmation (IM-04) in their most natural form. |
| **Security Features (RBAC/authN)** | **COMPLETE** for what exists; distinct from the dead "Security" module scaffolding | `security/policies.py` (role functions, `get_ticket_queryset` object-level scoping), `security/mixins.py` (permission mixins used consistently across every Ticket view), `management/commands/create_roles.py` (RBAC bootstrap), `test_authorization.py` + `test_permission_boundaries.py` (16 tests). SEC-01 hardened `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`/cookie-SSL settings, verified with a live `manage.py check --deploy` run. | Two known, documented gaps: (1) Technician cannot see unassigned tickets at all — asked, unanswered. (2) Requester-visibility into Problems — asked, unanswered. Note: `apps/security_engine/`, `apps/soc_center/`, `apps/vulnerability_management/` (a *different*, larger "security module" — audit logs, SOC dashboard, vulnerability tracking) are separately confirmed empty; don't conflate with the RBAC layer above, which is real and tested. |
| **Deployment Readiness** | **MISSING** beyond CI | `ticketing/settings.py` is env-var-driven (SEC-01). `.github/workflows/django-tests.yml` + `security-scan.yml` now run on every push/PR (CI-01). `deployment/modules/*.ps1` (Build/Package/Repair/Validate/Test/etc.) contain real PowerShell content (259–700 lines each) — a parallel, non-CI deployment tooling attempt. | **No dependency manifest anywhere** (`requirements.txt`/`pyproject.toml`/`Pipfile` all absent, confirmed exhaustively during CI-01) — a fresh clone has no documented way to know what to install. `Dockerfile`, all `docker-compose*.yml`, `deployment/docker/*`, `deployment/kubernetes/*.yaml`, `deployment/nginx/*.conf`, `deployment/ci_cd/pipeline.yml` are **all confirmed 0 bytes** — none of the containerization/orchestration scaffolding is functional. No production checklist exists as a document. |

---

## Core ITSM Modules — Detail

### 1. Incident Management
**Completed:** creation (routed through `TicketService.create_ticket`), full lifecycle (`open → in_progress → pending → resolved → closed`, validated transitions, reopen), dashboard (`IncidentDashboardView`, RBAC-scoped), assign/reassign/comment/close/reopen as real user-facing actions with full audit history.
**Remaining, evaluated:**
- *Escalation* — no mechanism exists; would need SLA Management (below) as a prerequisite to have something to escalate against.
- *SLA timers* — completely absent; no due-date field on `Ticket`.
- *Priority calculation* — `priority` is a plain manual field; no impact×urgency derivation logic exists (though `urgency` and `priority` are both already separate fields on `Ticket`, so the *inputs* for a calculation exist — the calculation itself doesn't).
- *Assignment workflows* — the mechanics exist (`TicketAssignView`, full history) but there's no auto-assignment/routing logic, and the Technician-visibility RBAC question (above) affects how this should work.
- *Notifications* — none, see Notification Features row above.
- *Reporting* — only raw dashboard counts, no trend/SLA/exportable reporting.

### 2. Problem Management
**Completed:** problem records, root cause analysis (Five Whys + Fishbone, evidence, CAPA actions, approvals), known-error workflow (gated on RCA + root cause populated), knowledge linkage is *structurally* present (`related_tickets` M2M) even though Knowledge Management itself doesn't exist yet.
**Remaining:** entirely the UI layer — views, URLs, templates, forms, and the one blocked security policy function. Zero new architectural decisions needed beyond the already-outstanding Requester-visibility question.

### 3. Service Request Management
**Remaining, evaluated:** request catalog (nothing — `RequestType` is a flat category list, not a catalog with descriptions/SLAs/forms per type), approval workflow (nothing), fulfillment process (nothing — fulfillment is identical to closing any other ticket today), request templates (nothing). This would likely reuse `Ticket`+`RequestType` as its foundation rather than a parallel model, following the same "Ticket is the base record" pattern Incident Management uses — but that's a design decision for when this is prioritized, not decided here.

### 4. Change Management
**Remaining, evaluated:** change records (nothing), risk assessment (nothing), approvals (nothing — though the `Approval` model built for Problem Management's RCA could plausibly generalize), scheduling (nothing), CAB workflow (nothing). Not started.

### 5. CMDB / Asset Management
**Remaining, evaluated:** configuration items (nothing), relationships (nothing), ownership (nothing), asset lifecycle (nothing). Not started. This is a dependency several other gaps implicitly want (repeat-incident detection, change impact analysis) but none of them are blocked *waiting* on it — they've each independently substituted a workaround (e.g. PM-02's text/department matching).

### 6. SLA Management
**Remaining, evaluated:** SLA definitions (nothing), timers (nothing), breach detection (nothing), escalation (nothing — and blocks Incident Management's escalation, above). Not started.

### 7. Knowledge Management
**Remaining, evaluated:** articles (nothing), search (nothing), linking incidents/problems (nothing at the Knowledge end, though `Problem.related_tickets` already provides the incident-side half of that link), approvals (nothing). Not started.

### 8. Reporting and Analytics
**Remaining, evaluated:** dashboards (only the two raw-count incident/problem dashboard-statistics selectors, one of which — Problem's — is unreachable), metrics (ticket-only, no cross-module), operational reports (nothing exportable/scheduled).

### 9. Deployment Readiness
**Remaining, evaluated:** environment configuration (**done** — SEC-01), dependency management (**missing** — no manifest anywhere), deployment workflow (**missing** — all containerization/orchestration files are 0 bytes; the PowerShell `deployment/modules/` scripts have real content but were not exercised or verified as part of this audit and are a second, CI-independent deployment path whose relationship to the new GitHub Actions CI hasn't been reconciled), production checklist (**missing** — no such document exists; this ITSM_ROADMAP.md plus SESSION_STATE.md's "Required Checks Before Push" are the closest things to one today, and they're process checklists, not a deployment runbook).

---

## Dependencies Between Modules

- **SLA Management → Incident Management (escalation)**: escalation cannot be built meaningfully until there's an SLA timer to breach.
- **Notification Features → Incident Management (escalation, requester confirmation) and SLA Management (breach alerts)**: an escalation or breach that notifies no one isn't functional. This is a shared prerequisite for two different gaps above, which raises its priority.
- **CMDB/Asset Management → Change Management (impact assessment) and Problem Management (repeat-incident-by-CI detection)**: both would be substantively better with a real CI model, but neither is currently *blocked* by its absence — both have working substitutes.
- **Knowledge Management → Problem Management (known-error articles)**: `Problem.is_known_error` + `root_cause`/`workaround` already model the *content* a Known Error Database needs; Knowledge Management would mostly need to expose/search that content rather than duplicate it.
- **Problem Management UI → nothing else**: this is the one gap in the entire matrix with zero unresolved dependencies on another missing module. Everything it needs (models, services, selectors, the accepted ADR-009 architecture) already exists.
- **Service Request Management → Incident Management's `Ticket` foundation**: whatever gets built here will almost certainly extend `Ticket`/`RequestType` rather than introduce a parallel record type, for the same reasons ADR-009 chose to extend `apps/service_desk` over standing up a new app.

---

## Prioritization

### P0 — Critical platform gaps
Reasoning: these aren't new ITSM features — they're standing risks to correctness, reproducibility, or already-blocked work. Each has already caused a concrete problem or is actively blocking approved-architecture work from proceeding.

1. **IM-04 decisions** (work notes visibility, attachments, requester confirmation) — asked twice, unanswered, blocking further Incident Management work.
2. **Technician-unassigned-ticket RBAC decision** — a real usability gap in the RBAC model, found by a failing test, not yet decided either way.
3. **Requester-visibility into Problems decision** — the single blocker preventing Problem Management UI (a fully-designed, zero-new-architecture piece of work) from starting.
4. **Dependency manifest** (`requirements.txt`/`pyproject.toml`) — CI-01 worked around its absence, but a fresh clone of this repository still cannot be reliably set up today.
5. **`models.py`/`views.py` dead-file collision cleanup** — this exact class of problem already caused INC-001 (FIX-01's regression); the second instance (`models.py`) hasn't caused an incident yet only because nobody has edited it expecting it to take effect.

### P1 — Enterprise ITSM functionality
Reasoning: real, expected ITSM capability that a platform calling itself "enterprise ITSM" doesn't yet have, but that doesn't require new architectural decisions to start — same shape as IM-03's schema-free wins.

1. **Problem Management UI** — the highest-value, lowest-risk item on this entire roadmap once its one P0 blocker (Requester-visibility) is resolved.
2. **SLA Management** (models + basic timer/breach detection) — prerequisite for real escalation.
3. **Notification Features** (at minimum: email on assignment/status-change/comment) — prerequisite for escalation and requester confirmation to be meaningful, and shared across two other gaps.
4. **Service Request Management** — extends existing `Ticket`/`RequestType`, not a from-scratch build.

### P2 — Enhancements
Reasoning: valuable, but each depends on P1 items to be genuinely useful (reporting is thin without SLA data; knowledge linking is thin without Problem UI to link *from*), or is cleanup rather than capability.

1. **Reporting and Analytics** expansion (cross-module, exportable).
2. **Knowledge Management** (articles, search, linking).
3. **CMDB / Asset Management** basics (Configuration Item model + Ticket/Problem linkage).
4. Dead duplicate template cleanup, scaffold-apps scope decision (housekeeping, not capability).

### P3 — Future features
Reasoning: largest scope, most dependencies on things that don't exist yet, or lowest immediate ROI given the platform hasn't finished its two core ITIL processes.

1. **Change Management** (full CAB workflow) — not started, and change *risk assessment* is more meaningful once CMDB exists.
2. **AI Features** — every one of six scaffolded AI sub-apps is empty; building any of them before there's SLA/Notification/Knowledge data to reason over would mean building on nothing.
3. **Full deployment automation** (Docker/K8s/nginx, CI/CD beyond current GitHub Actions) — CI-01 covers the "does it work" gate; production deployment automation is a distinct, larger effort.
4. **Security/SOC module** (distinct from RBAC, which is already solid) — audit logs, vulnerability tracking, SOC dashboard.

---

## Sprint Roadmap

| Sprint | Feature | Files affected | Tests required | Dependencies | Acceptance criteria |
|---|---|---|---|---|---|
| **PM-03** | Problem Management UI | `apps/service_desk/views.py` (new Problem views), `urls.py`, new `templates/service_desk/problems/*.html` (dashboard/list/detail/RCA forms), `security/policies.py` (`get_problem_queryset`), `security/mixins.py` (Problem permission mixins), new `test_suite/test_problem_*.py` | RBAC scoping per role (mirroring `test_authorization.py`), view reachability, RCA/known-error workflow end-to-end via the UI, ticket-linking UI | **Requester-visibility decision (P0)** | All roles see the correct problem set per an approved visibility policy; RCA/known-error/ticket-linking usable end-to-end through templates, not just the service layer; `check`/`test`/`makemigrations --check` all clean; zero new model changes (models already exist). |
| **IM-04** | Work notes / attachments / requester confirmation | Depends entirely on which options are chosen — likely `models/ticket.py` or `models/ticket_history.py` (schema change), `services/ticket_service.py`, `views.py`, `templates/tickets/*`, `security/` | New tests per chosen design; must not regress the existing 44 | **Three-way decision (P0)**, not yet made | Matches whichever design is approved; migration generated and reviewed before merge; existing test suite still green. |
| **RBAC-01** | Technician unassigned-ticket visibility | `security/policies.py` (`get_ticket_queryset`), possibly `templates/service_desk/incidents.html` (a "claim" action) | Update/extend `test_authorization.py`'s Technician-role tests | **RBAC decision (P0)**, not yet made | Matches the approved visibility rule; every existing authorization test still passes; if visibility widens, a corresponding "claim ticket" action should probably ship alongside it (not assumed — would need its own confirmation). |
| **DEP-01** | Dependency manifest | New `requirements.txt` (or `pyproject.toml`) at repo root | CI-01's workflows updated to `pip install -r requirements.txt` instead of the current pinned inline install | None | Fresh clone + `pip install` reproduces a working environment; CI still green; documents that Django is (as verified) the only real runtime dependency, or corrects that finding if something else turns out to be needed. |
| **ARCH-01** | Delete dead `models.py`/`views/` files | Delete `apps/service_desk/models.py`, `apps/service_desk/views/` (both confirmed dead in ARCHITECTURE.md §4) | Full existing suite as regression check | None | `check`/`test`/`makemigrations --check` all clean after deletion; confirms via `python -c "import ...; print(m.__file__)"` that nothing's import resolution changes. |
| **SLA-01** | SLA Management foundation | New `apps/service_desk/models/sla_policy.py` (or similar — needs its own design pass), migration, `services/sla_service.py`, `selectors/sla_selector.py` | New test module for timer/breach logic | None architecturally, but needs its own inspect→design pass (this roadmap does not pre-decide the SLA data model) | SLA policy attachable to a Ticket (by priority/department); breach detection computable; no UI required yet — mirrors how Problem Management shipped models+services before UI. |
| **NOTIFY-01** | Notification Features foundation | New `apps/service_desk/models/notification.py` or similar, `EMAIL_BACKEND` configuration (env-driven, per SEC-01's pattern), `services/notification_service.py`, signal or explicit call sites in `TicketService` | New test module using Django's test email backend (`django.core.mail.outbox`) | None architecturally, needs its own design pass (in-app only vs. email vs. both is a real decision, not assumed here) | At minimum, assignment/status-change/comment on a ticket triggers a real, testable notification event. |

---

## Notes on scope discipline

This document is analysis and planning only — no code was changed to produce it. Every "Missing Work" and
"Remaining" entry above was verified by inspection (grep for imports/usages, file-size checks, `git log`
where relevant), not inferred from directory names. Where this audit found something not yet in
[SESSION_STATE.md](SESSION_STATE.md)'s Open Decisions/Known Blockers (e.g. the CI/deployment-tooling
duplication between `deployment/modules/*.ps1` and the new GitHub Actions workflows), it's called out
above rather than silently folded into a priority ranking as if it were already understood.
