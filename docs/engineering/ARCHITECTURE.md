# Architecture — Ground Truth

Verified 2026-08-07 against branch `feature/incident-management-dashboard`. This document distinguishes
what is **actually running** from what merely **exists as a file in the repository** — in this codebase
those are frequently not the same thing.

## 1. Registered application

`ticketing/settings.py` → `INSTALLED_APPS` registers exactly one project app:

```
apps.service_desk
```

Everything the running Django project can serve — models, migrations, views, URLs, admin, permissions —
comes from `apps/service_desk/`. No other app under `apps/` is registered, migrated as a distinct app, or
reachable through the root URLconf (`ticketing/urls.py` only includes `apps.service_desk.urls`).

## 2. Unregistered scaffolding (~59 apps)

`apps/` contains roughly 60 directories that look like Django apps (`ai_engine`, `cmdb`, `problem_management`,
`sla_engine`, `workflow_engine`, `identity_management`, `security_engine`, and many more) — most have
`models.py`, some have `migrations/`, a few have `services/`. **None of them are in `INSTALLED_APPS`.**
Their models are not part of the Django app registry, are not migrated, and cannot be imported the normal
way in a request/response cycle. Several of these files are literally empty (0 bytes) — e.g.
`apps/problem_management/models.py`, `known_errors.py`, `rca.py`.

Treat this tree as **inert scaffolding**, not working code, until an app is explicitly registered and
verified. Do not assume a model "exists" in the running system just because a `.py` file defines a class
with that name somewhere under `apps/`.

**How to re-check:** `grep -n "INSTALLED_APPS" -A 15 ticketing/settings.py`

## 3. `apps/service_desk` internal layout

The active app is itself organized as a set of subpackages, not all of which are wired in:

| Subpackage | Status |
|---|---|
| `models/` (package: `department.py`, `request_type.py`, `ticket.py`, `ticket_history.py`, `__init__.py`) | **Active.** This is the real model source — see §4. |
| `services/`, `selectors/` | `ticket_service.py` and `ticket_selector.py` are real, in-use business/data logic. `dashboard_service.py` and `dashboard_selector.py` are **0-byte empty files** — dead. |
| `security/` (`policies.py`, `mixins.py`) | Active — RBAC queryset scoping and permission mixins, used by `views.py` and covered by tests. |
| `forms/ticket_forms.py` | Active — used by `TicketCreateView`. |
| `test_suite/` | Active — 12 tests (`test_authorization.py`, `test_permission_boundaries.py`), all passing as of this milestone. |
| `sla/`, `cmdb/`, `automation/`, `knowledge/`, `notifications/`, `reporting/`, `workflow/`, `identity/` (subpackages under `apps/service_desk/`) | **Scaffolding, not wired in.** Their `models.py` files are empty; nothing imports them; they exist for future modules that haven't landed. |
| `views.py` vs `views/` | Collision — see §4. |
| `models.py` vs `models/` | Collision — see §4. |

## 4. File-collision hazard: flat module vs. same-named package — RESOLVED (ARCH-01)

**Status: fixed.** Two places in `apps/service_desk/` used to have **both** a flat `<name>.py` file and a
`<name>/` directory sitting next to each other with the same import name, resolving **in opposite
directions** — which caused one production-breaking regression (see INCIDENT_LOG.md, INC-001). Both dead
sides were deleted in ARCH-01 after confirming (again) which side was live and that nothing referenced the
dead one directly:

- **`models.py` vs `models/`** — the package (`apps/service_desk/models/`, with `__init__.py`) was always
  the live one; the flat `apps/service_desk/models.py` (~315 lines) was dead and has been deleted.
- **`views.py` vs `views/`** — the flat file (`apps/service_desk/views.py`) was always the live one; the
  `apps/service_desk/views/` directory (`dashboard.py`, `ticket_views.py`, both 0 bytes, no `__init__.py`)
  was dead and has been deleted.

Verified before deletion (import resolution unchanged), and again after (44/44 tests still pass,
`manage.py check` clean, zero migration drift):
```
python -c "import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','ticketing.settings'); django.setup(); import apps.service_desk.<module> as m; print(m.__file__)"
```

## 5. Migrations

`apps/service_desk/migrations/` has five migrations (0001–0005, the last two added by PM-02.1 for the
Problem Management models), and they are **in sync** with the active `models/` package —
`python manage.py makemigrations --check --dry-run` reports no changes as of this milestone. This is one
of the healthy parts of the codebase.

The ~59 unregistered apps' `migrations/` directories are not meaningful — they were never run against any
database, since their apps aren't installed.

## 6. Configuration state

`ticketing/settings.py`:
- `SECRET_KEY` is a hardcoded plaintext literal committed to version control.
- `DEBUG = True`, not gated by an environment variable.
- No `.env` mechanism in use despite `.gitignore` expecting one (`.env`, `.env.*` are ignored but no
  `.env.example` exists).

`.github/workflows/deployment.yml`, `django-tests.yml`, `security-scan.yml` are all **0 bytes**. CI is a
placeholder — nothing runs automatically on push or PR. This is why the regression in INCIDENT_LOG.md
shipped to a branch undetected.

## 7. Git topology (as of this milestone)

- `main` (`a21b3ca`, "RC-12: Recovery baseline") is a direct ancestor of this branch — no divergence, safe
  fast-forward relationship.
- `develop` diverged immediately after the first commit and was never reconciled — it's missing ~130 files
  of work that landed on `main`/this branch (deployment tooling, Phase 2.2 authorization, ticket UI), and
  has its own unrelated `autosync` module that never made it the other way. Treat `develop` as a stale,
  divergent line, not a merge target, until someone deliberately reconciles it.
- Stale rollback tags exist (`ops01-rollback`, `fe14-step5-rollback`, `fe14-step4-rollback`,
  `fe12-rollback`) pointing at old commits, plus two `origin/arena/*` branches already merged via PR #1.

**How to re-check:** `git log --oneline --graph --decorate --all -50`, `git merge-base main develop`
