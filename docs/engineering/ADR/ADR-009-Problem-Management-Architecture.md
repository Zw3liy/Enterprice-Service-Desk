# ADR-009: Problem Management Architecture

**Status:** PROPOSED
**Date:** 2026-08-07
**Related:** [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](../DESIGN_PM-02_PROBLEM_MANAGEMENT.md), [ARCHITECTURE.md](../ARCHITECTURE.md) §2

Do not implement Problem Management from this document. This ADR settles *where the code would live*;
[DESIGN_PM-02_PROBLEM_MANAGEMENT.md](../DESIGN_PM-02_PROBLEM_MANAGEMENT.md) settles *what the code would
be*. Both must be approved before implementation begins.

## Context

PM-02 (Problem Management / Root Cause Analysis) requires a `Problem` model plus supporting
services/selectors/security/views. No `Problem` model exists anywhere in the active codebase today. Two
plausible locations exist:

1. **`apps/service_desk`** — the only registered, migrated, tested Django app in this project
   (`INSTALLED_APPS` contains exactly this one app — see ARCHITECTURE.md §1).
2. **`apps/problem_management`** — an already-present directory at the top level of `apps/`, with
   `models.py`, `known_errors.py`, `rca.py`, and a `migrations/` directory. **All three Python files are
   0 bytes.** The app is not in `INSTALLED_APPS` and has never been part of the running project.

This is one instance of a repository-wide pattern: ~59 of ~60 directories under `apps/` are unregistered
scaffolding (ARCHITECTURE.md §2). The decision made here should be treated as the template for how future
milestones decide between "extend `service_desk`" and "stand up one of the dormant scaffold apps."

## Option A — Build inside `apps/service_desk`

New models in `apps/service_desk/models/problem.py` and `problem_history.py`; services, selectors,
security, views, and tests follow the exact patterns already established for `Ticket`. Full detail in the
PM-02 design doc.

**Advantages**
- Zero registration risk — the app is already in `INSTALLED_APPS`, already migrated, already has a
  working test runner path. No settings changes needed.
- Reuses proven, tested infrastructure directly: `security/policies.py` role functions
  (`is_administrator`, `is_manager`, `is_technician`, `is_requester`), `security/mixins.py` permission
  mixins, the `TicketService`/`TicketSelector` code style, the `test_suite/` pattern — all copy-pasteable
  with no adaptation layer.
- `Problem.related_tickets` as a same-app `ManyToManyField` to `Ticket` is a same-app FK/M2M — no
  cross-app dependency, no import ordering concerns, no risk of circular app dependencies.
- Every engineer who already understands `service_desk` (the only app anyone has had to understand so
  far) can read Problem Management code without learning a second app's conventions.
- Matches the actual scale of the project today: one working domain, incrementally extended.

**Disadvantages**
- `apps/service_desk` keeps growing as a single app — it already has internal subpackages for tickets,
  and unused scaffolding for `sla/`, `cmdb/`, `automation/`, `knowledge/`, `notifications/`, `reporting/`,
  `workflow/`, `identity/` (ARCHITECTURE.md §3). Adding Problem Management as another subpackage continues
  a trend toward one large app rather than bounded contexts.
- If Problem Management later needs to be extracted into its own deployable/versioned unit (e.g. a
  separate team owns it, or it needs independent scaling), that extraction is a real migration later,
  not a non-event.

**Maintenance:** Low overhead now — one app to run migrations against, one test command, one admin
registration point. Engineers maintaining `service_desk` already own this code by default.

**Scalability:** Fine at current project scale (one deployable Django project, one database). Would need
revisiting if Problem Management volume/complexity grows to justify independent deployment — not a
near-term concern given the project has exactly one registered app total today.

**Complexity:** Lowest of the two options. No new `INSTALLED_APPS` entry, no new app-level `apps.py`, no
new migration state to initialize from zero, no decision about whether `Problem` needs to reference models
in a different app (it doesn't, under this option).

## Option B — Dedicated app: `apps/problem_management`

Register the existing (currently empty, unregistered) `apps/problem_management` in `INSTALLED_APPS`,
populate its `models.py`, and build services/selectors/security/views as a self-contained app that
imports `Ticket` from `apps.service_desk.models` as a cross-app dependency.

**Advantages**
- Clean bounded-context separation — Problem Management becomes its own app boundary from day one,
  matching ITIL's conceptual separation of Incident Management and Problem Management as distinct
  processes.
- If the project ever does grow into the ~60-app structure the scaffolding implies, this is the "correct"
  long-term shape, and starting here avoids a later extraction.
- Reuses the directory that's already sitting in the repo with a plausible name, rather than leaving it
  as permanent dead weight (though see Disadvantages — reuse isn't free here).

**Disadvantages**
- Requires a `INSTALLED_APPS` change to `ticketing/settings.py` — the one file this project has flagged as
  already carrying configuration debt (hardcoded `SECRET_KEY`, ungated `DEBUG`). Any settings change here
  should be deliberate and reviewed, not incidental to a feature build.
- Requires a **cross-app FK/M2M** from `Problem` to `Ticket` (`apps.service_desk.models.Ticket`). This is
  ordinary Django, but it's new territory for this codebase — no existing code today has a cross-app model
  relationship to validate the pattern against, migration-dependency-wise or import-cycle-wise.
- The existing `apps/problem_management` scaffold cannot simply be "filled in" — its three Python files
  are empty and its `migrations/` directory has no real migration history. In practice this option means
  building from scratch inside that directory, gaining nothing from the scaffold except the name and
  location. It does **not** save implementation effort over Option A.
- New app means a new test-discovery path, a new admin registration surface, and a second place
  (`apps/problem_management/security/` or similar) that would need to duplicate or import
  `service_desk`'s role-check functions (`is_administrator`, `is_manager`, etc.) — either via cross-app
  import (coupling) or duplication (drift risk).
- This project has exactly one other precedent for "register a new app" — and that precedent is the
  ~59 apps that were scaffolded and then never finished or registered (ARCHITECTURE.md §2). Choosing this
  path repeats the exact shape of the problem the repository is currently trying to recover from.

**Maintenance:** Higher overhead — two apps to keep in sync (permission bootstrap in
`create_roles.py` would need to handle a cross-app content type; migrations for two apps instead of one;
two admin registration points).

**Scalability:** Better positioned *if* the project actually grows into a true multi-app platform. But
that's speculative — today there is one deployable unit, one database, and one registered app total.
Designing for a scale the project hasn't reached yet is exactly the kind of premature structure that
produced the ~59-app scaffolding graveyard this repository already carries.

**Complexity:** Highest of the two options, for no functional gain over Option A given the scaffold is
empty. Adds a settings change, a cross-app dependency, and a second security/permission surface — for a
feature whose actual requirements (per the PM-02 design) are fully satisfiable inside the existing app.

## Recommendation

**Option A — build Problem Management inside `apps/service_desk`.**

### Justification

1. **The scaffold provides no head start.** `apps/problem_management`'s three files are empty. Choosing
   Option B does not mean "finishing" existing work — it means starting from zero in a location that
   additionally requires a settings change and a cross-app dependency, for zero implementation savings.
2. **The project's actual current scale is one app.** Every piece of working infrastructure this project
   has — tested RBAC, service/selector conventions, CI-relevant checks, the one app anyone has had to
   learn — lives in `apps/service_desk`. Option A reuses all of it directly; Option B requires either
   duplicating it or coupling a new app to it.
3. **Option B repeats a known failure pattern.** This repository's biggest structural problem, documented
   in ARCHITECTURE.md §2, is ~59 apps that were registered-in-spirit but never actually wired in, tested,
   or finished. Registering `apps/problem_management` now — for a feature that doesn't need app-level
   isolation — adds one more entry to exactly that pattern instead of reducing it.
4. **Extraction later is cheaper than premature separation now.** If Problem Management genuinely
   outgrows `service_desk` in the future (independent scaling, independent team ownership), that's a
   deliberate, well-scoped migration at the point it's actually justified — not a default to design around
   today, on a project with one deployable app and one database.
5. **Lower blast radius.** Option A touches zero settings, zero new app registration, zero cross-app
   migration ordering. Every file it touches is inside `apps/service_desk`, consistent with this
   project's current pattern of high-risk, hard-to-verify changes being the ones that break `manage.py
   check` (see INCIDENT_LOG.md, INC-001) — minimizing surface area matters here.

### What this decision does not do

It does not delete or otherwise resolve `apps/problem_management`. That empty scaffold remains exactly
as-is, tracked under the general scaffolding cleanup item in ROADMAP.md. This ADR only decides where *new*
Problem Management code goes if/when PM-02 is approved for implementation.

## Consequences

- PM-02 implementation, once approved, follows the file plan in
  [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](../DESIGN_PM-02_PROBLEM_MANAGEMENT.md) §12 unchanged — that design
  already assumed Option A.
- `apps/problem_management` stays dormant and unregistered; no action taken on it by this ADR.
- Future ADRs facing the same "extend `service_desk` vs. stand up a scaffold app" choice for a different
  feature should reference this ADR's reasoning rather than re-deriving it from scratch, unless the
  circumstances genuinely differ (e.g. a feature that actually needs independent deployment).

## Approval

**Status: PROPOSED.** Not yet approved. Do not begin PM-02 implementation on the strength of this document
alone — it requires explicit sign-off, recorded here once given.
