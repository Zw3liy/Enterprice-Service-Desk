# ADR-011: Enterprise Completion Program — Foundations

**Status:** ACCEPTED
**Date:** 2026-08-28
**Related:** ADR-009 (Problem Management architecture), ADR-010 (visibility decisions), ITSM_ROADMAP.md P2/P3
(Service Request, Change, Release, CMDB, Knowledge, Reporting)

This session starts the "Enterprise Service Desk — Enterprise Completion Program": building Service Request
Management, Change Management, Release Management, CMDB, Knowledge Management, Reporting/Analytics, SLA
scheduler monitoring, email/notification completion, and audit/RBAC/operations hardening on top of the
verified baseline this ADR records. Two foundational decisions are made before any new capability lands, so
every later module follows the same shape rather than each improvising its own.

## Decision 1 — Test performance infrastructure (`ticketing/test_settings.py`)

**Problem found:** on this development machine, a single Django PBKDF2 password hash measured ~0.6s
(`django.contrib.auth.hashers.make_password`). The existing suite creates many `User` fixtures per test
across four RBAC roles, repeated per test module — `python manage.py test` (no `--settings`, the CI-01
default) took over 19 minutes without finishing a full pass, verified by watching incremental
`--verbosity 2` output rather than assumed from a hang.

**Decision:** added `ticketing/test_settings.py`, layered over `ticketing.settings` exactly like
`production_settings.py` layers production config, changing only `PASSWORD_HASHERS` to
`MD5PasswordHasher` — a pattern Django's own documentation recommends
(`Speeding up the tests`, "topics/testing/overview"). Applied the identical override to
`ticketing/postgres_test_settings.py`, since that module is what the PostgreSQL CI job actually runs
under. Neither `ticketing.settings` (local dev default) nor `ticketing.production_settings` (deployed) is
touched — this changes test *run time* only, never test *coverage* or any deployed security posture.

**Verified effect:** full suite (296 tests as of this session's baseline) went from a run that did not
complete a single pass in 19+ minutes to **8-11 seconds** using `DJANGO_SETTINGS_MODULE=ticketing.test_settings
python manage.py test --parallel auto` on this machine's 8 logical cores. `.github/workflows/django-tests.yml`
and `.github/workflows/deployment.yml` (the PostgreSQL job) were updated to use the same settings module and
`--parallel auto`, so CI gets the same speed and cost benefit.

**How to re-check:** `DJANGO_SETTINGS_MODULE=ticketing.test_settings python manage.py test --parallel auto`.

## Decision 2 — New-capability module layout

**Context:** `apps/service_desk` is the sole registered app (ARCHITECTURE.md §1). Its internal layout
splits `models/`, `services/`, `selectors/`, `forms/` into one file per capability
(`ticket_service.py`, `sla_service.py`, `problem_service.py`, …), each re-exported from a package
`__init__.py`. `views.py` and `urls.py`, by contrast, are single flat files — a deliberate outcome of
ARCH-01, which deleted a same-named `views/` package after it caused a production regression (INC-001).
`views.py` is already 2243 lines carrying Ticket, Problem, Supplier, SLA and Notification views combined.

Six more capabilities are about to land (Service Request/Catalogue, Change Management, Release Management,
CMDB, Knowledge Management, Reporting). Appending all of their views to the one existing `views.py` would
put a single file at an estimated 6000+ lines and mixes unrelated capabilities' review history together;
splitting into a `views/` package would recreate exactly the flat-file/package collision ARCH-01 removed.

**Decision:** new capabilities get their own flat, single-purpose view module —
`catalog_views.py`, `change_views.py`, `release_views.py`, `cmdb_views.py`, `knowledge_views.py`,
`reporting_views.py` — each imported into `urls.py` alongside the existing `from . import views`. This is
not a new pattern; it is the same one-file-per-capability shape already used for `services/`/`selectors/`/
`forms/`, extended to `views.py`'s sole remaining monolith, and it introduces no `<name>.py`/`<name>/`
naming collision since no `views/` package exists to collide with. The original `views.py` is left
untouched — existing Ticket/Problem/Supplier/SLA/Notification views are not moved or refactored as part of
this program, since that would be pure churn against working, tested code with no functional benefit.

Models/services/selectors/forms for new capabilities follow the existing per-capability-file convention
unchanged (e.g. `models/change.py`, `services/change_service.py`, `selectors/change_selector.py`,
`forms/change_forms.py`). `security/policies.py` gains one `get_<capability>_queryset(user)` function per
new object type, matching `get_ticket_queryset`/`get_problem_queryset`/`get_supplier_queryset` exactly.
`security/mixins.py` gains one `<Capability>{View,Create,Change,Delete}PermissionMixin` set per new model,
matching the existing `Ticket*`/`Problem*`/`Supplier*`/`SLAPolicy*` mixins exactly.

**Scaffolding not reused:** `apps/service_desk/{cmdb,knowledge,reporting,sla,notifications,automation,
identity,api,filters}/` and the ~128 unregistered top-level `apps/*` directories, plus every template
under `templates/{cmdb,knowledge,reporting,reports,itil,self_service,customer_portal,workflow}/`, were
inspected this session and confirmed still 0-byte/empty (same finding as ARCHITECTURE.md §2-3 and
ITSM_ROADMAP.md, re-verified rather than assumed). None of this program's new code writes into those
directories — doing so would either duplicate the real implementation living in `models/`/`services/`/
`selectors/` or resurrect the exact flat/package collision hazard ARCH-01 eliminated. New templates are
written into the existing (currently-empty) top-level `templates/<capability>/` directories, since those
paths are already the ones a template lookup by capability name would resolve to and nothing references
the dead 0-byte files there today.

## Consequences

- Every new-capability checkpoint in this program follows the shape above; deviations must be justified in
  their own ADR addendum, not silently improvised.
- `urls.py` grows one `from . import <capability>_views` import and its `path()` entries per module,
  keeping the route table centralized (matching the existing single-`urls.py` pattern) while view code
  stays partitioned by capability.
- Existing Ticket/Problem/Supplier/SLA/Notification code, tests, and URLs are unaffected by either decision
  in this ADR.

## Approval

Made under this session's standing engineering authority for the Enterprise Completion Program (explicit
mission instruction to continue autonomously through implementation, pausing only for genuine
credential/authorization blockers or safety-critical ambiguity — neither applies to either decision here).
