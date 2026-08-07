# Incident Log

Durable record of production-breaking regressions found in this repository, their root cause, and the fix
applied. Keep entries even after the fix is committed — this is a history, not a TODO list (see
ROADMAP.md for open work).

---

## INC-001 — `apps.service_desk.views` missing `DashboardView` (P0)

**Status:** Fixed in working tree, **not yet committed** as of this milestone.
**Detected:** 2026-08-07, via `python manage.py check` and `python manage.py test`.
**Branch:** `feature/incident-management-dashboard`.

### Symptom

Both `manage.py check` and `manage.py test` failed immediately with:

```
AttributeError: module 'apps.service_desk.views' has no attribute 'DashboardView'
```

Root import chain: `manage.py` → Django's URL system check → `ticketing/urls.py:17`
(`include("apps.service_desk.urls")`) → `apps/service_desk/urls.py:7`
(`views.DashboardView.as_view()`) → fails, because `DashboardView` doesn't exist on the module.

Because `manage.py test` runs the same system check as a pre-flight step before executing any test, **all
12 tests in `test_suite/` were blocked from running at all** — not failing, just never executed.

### Root cause

`apps/service_desk/urls.py` references four view classes: `DashboardView`, `TicketListView`,
`TicketCreateView`, `TicketDetailView`. Commit **`d2bafee` — "FE-01 finalize sidebar styling and layout
integration"** (the branch tip at time of detection, authored by Forest Valentine) rewrote
`apps/service_desk/views.py`, deleting all four of those classes (222 lines removed) and replacing them
with a new `IncidentDashboardView`. `urls.py` was not updated to match — confirmed via
`git log main..feature/incident-management-dashboard -- apps/service_desk/urls.py`, which shows zero
commits touching that file anywhere in this branch's history.

The commit's stated scope ("sidebar styling and layout integration") does not match this change — the
view-layer rewrite appears to be an unintentional or leaked edit, not deliberate scope for that commit.

Confirmed via `git log main..feature/incident-management-dashboard --oneline -- apps/service_desk/views.py`
that `d2bafee` is the only commit on this branch touching `views.py`; the four deleted classes existed
intact on `main` prior to this branch.

### Fix applied

Restored `DashboardView`, `TicketListView`, `TicketCreateView`, `TicketDetailView` in
`apps/service_desk/views.py` verbatim from `main` (including their `TicketPermissionMixin`/
`get_ticket_queryset()` RBAC wiring), appended after the existing `IncidentDashboardView` — which was kept,
not removed. No change to `urls.py` was required, since it already expected the four restored names.
No changes to `models/`, `forms/`, `services/`, `selectors/`, `security/`, `migrations/`, `templates/`, or
`settings.py`.

**Verification after fix:**
```
$ python manage.py check
System check identified no issues (0 silenced).

$ python manage.py test
Creating test database for alias 'default'...
............
----------------------------------------------------------------------
Ran 12 tests in 46.577s

OK
```

**Outstanding:** the fix is applied in the working tree but not committed as of this milestone (see
ROADMAP.md item 1).

### Known follow-on defects (not part of this fix — tracked separately)

`IncidentDashboardView` itself, kept as-is per instruction, has two pre-existing defects unrelated to the
regression above:
1. `template_name = "service_desk/incidents.html"` — this template does not exist anywhere in the repo.
2. Its `status__in`/`priority__in` filters use values (`"UNASSIGNED"`, `"CRITICAL"`, uppercase generally)
   that don't match `Ticket`'s real lowercase choices — these querysets return zero rows even once the
   view is reachable.

See ROADMAP.md item 2.

### Lesson

This is the specific failure mode CI would have caught for free (ROADMAP.md item 3) — the break was
detectable by the cheapest possible check (`manage.py check`) and would have failed a PR gate
automatically instead of requiring manual investigation.
