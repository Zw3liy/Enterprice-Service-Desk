# Engineering Roadmap

Prioritized as of this milestone (PM-00). Update item status in place as work lands; don't leave completed
items undated. See [ARCHITECTURE.md](ARCHITECTURE.md) for the factual basis behind each item.

## Status legend
`OPEN` — not started · `DONE` — completed and verified · `PROPOSED` — designed, not implemented

---

1. **`DONE`** — Restore the four ticket views deleted by commit `d2bafee`. Fixed by restoring
   `DashboardView`, `TicketListView`, `TicketCreateView`, `TicketDetailView` in `apps/service_desk/views.py`
   alongside the new `IncidentDashboardView`. `manage.py check` and all 12 tests pass. Uncommitted as of
   this milestone — see INCIDENT_LOG.md for full detail. **Action needed: commit this fix.**

2. **`OPEN`** — Create the missing template `templates/service_desk/incidents.html` that
   `IncidentDashboardView` requires (`template_name`), and correct its `status__in`/`priority__in` filter
   values, which currently use `"OPEN"/"IN_PROGRESS"/"UNASSIGNED"` and `"HIGH"/"CRITICAL"` — none of which
   match the real lowercase `Ticket.STATUS_CHOICES`/`PRIORITY_CHOICES` (`"UNASSIGNED"` and `"CRITICAL"`
   aren't valid choices at all). These querysets currently return zero rows even when the view is
   reachable.

3. **`OPEN`** — Populate the three empty GitHub Actions workflow files
   (`.github/workflows/django-tests.yml` at minimum) to run `manage.py check` and `manage.py test` on
   every push/PR. This is what would have caught item 1 automatically instead of requiring manual
   discovery.

4. **`OPEN`** — Resolve the `models.py`/`models/` and `views.py`/`views/` collisions in
   `apps/service_desk/` (see ARCHITECTURE.md §4) by deleting the dead side of each. Low risk since the
   dead files are already confirmed unreachable, but do it as its own change with `manage.py check` +
   full test run as verification, not bundled into unrelated work.

5. **`OPEN`** — Move `SECRET_KEY` out of `ticketing/settings.py` into an environment variable; gate
   `DEBUG` behind an env flag; add a `.env.example`.

6. **`OPEN` — scope decision needed from repo owner** — Decide the fate of the ~59 unregistered scaffolded
   apps under `apps/` (see ARCHITECTURE.md §2): either commit to building specific ones out properly
   (registered, migrated, tested) or remove them from this branch to cut noise and reduce the risk of
   someone wiring one in without realizing it has no tests or service-layer discipline. This is a scope
   call, not something to decide unilaterally in a future session.

7. **`OPEN`** — Add test coverage for `TicketService`, `TicketSelector`, and `DashboardSelector`/
   `dashboard_service` business logic — currently only RBAC authorization is tested (`test_suite/`), not
   the service/selector layer itself. Note `dashboard_service.py` and `dashboard_selector.py` are
   currently empty files (item 1's discovery); decide whether to implement or delete them before writing
   tests against them.

8. **`OPEN`** — Reconcile or formally deprecate the `develop` branch (see ARCHITECTURE.md §7). It's missing
   ~130 files of work present on `main`/this branch and has diverged since the second commit in the
   repository's history.

9. **`OPEN`** — Clean up stale rollback tags and merged `origin/arena/*` remote branches once confirmed
   unneeded.

10. **`PROPOSED`** — PM-02 Problem Management / Root Cause Analysis. Full design in
    [DESIGN_PM-02_PROBLEM_MANAGEMENT.md](DESIGN_PM-02_PROBLEM_MANAGEMENT.md). Not implemented — awaiting
    approval and one open design decision (Requester-role visibility into problems).
