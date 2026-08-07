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

## 4. File-collision hazard: flat module vs. same-named package

Two places in `apps/service_desk/` have **both** a flat `<name>.py` file and a `<name>/` directory sitting
next to each other with the same import name. Python resolves this ambiguously, and the two cases resolve
**in opposite directions**, which has already caused one production-breaking regression (see
INCIDENT_LOG.md).

### `models.py` vs `models/` — the package wins

- `apps/service_desk/models.py` (flat file, ~315 lines) defines its own `Department`, `RequestType`,
  `Ticket` classes.
- `apps/service_desk/models/` (package, has `__init__.py`) defines the same class names across separate
  files and re-exports them.
- **The package wins**, because it's a real Python package (`__init__.py` present) and CPython's import
  machinery prefers a real package over a same-named module in the same directory.
- Verified empirically: `Ticket.__module__ == "apps.service_desk.models.ticket"`, and
  `Ticket._meta.get_field("priority").db_index is True` — that `db_index=True` only exists in the
  package's version of the field, not the flat file's.
- **Consequence: `apps/service_desk/models.py` is dead code.** It is never imported by the running
  application. Every other module (`services/`, `selectors/`, `security/`, `admin.py`, `views.py`) imports
  from `apps.service_desk.models` and gets the package version.
- Do not edit `models.py` expecting it to take effect. Model changes belong in `models/`.

### `views.py` vs `views/` — the flat file wins

- `apps/service_desk/views.py` (flat file) defines the actual view classes.
- `apps/service_desk/views/` (directory: `dashboard.py`, `ticket_views.py`) has **no `__init__.py`** —
  it is not a regular package, only a namespace-package candidate, which import resolution checks last.
- **The flat file wins**, and both files in the `views/` directory are empty (0 bytes) anyway.
- **Consequence: `apps/service_desk/views/` is dead code`,** in the opposite direction from the `models`
  case. This asymmetry is exactly why this collision pattern is dangerous — you cannot infer "package
  wins" or "flat file wins" from one case and apply it to the other; it depends on whether `__init__.py`
  is present.

**Recommendation:** delete one side of each collision once confirmed safe (tracked in ROADMAP.md). Until
then, always verify which file is live before editing — see the re-check command below.

**How to re-check which one is live for any ambiguous module:**
```
python -c "import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','ticketing.settings'); django.setup(); import apps.service_desk.<module> as m; print(m.__file__)"
```

## 5. Migrations

`apps/service_desk/migrations/` has three migrations (0001–0003), and they are **in sync** with the
active `models/` package — `python manage.py makemigrations --check --dry-run service_desk` reports no
changes as of this milestone. This is one of the healthy parts of the codebase.

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
