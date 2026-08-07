# Design: PM-02 — Problem Management / Root Cause Analysis

**Status: PROPOSED — not implemented.** No code from this design exists in the repository yet. This
document captures the design as presented for approval; implementation is blocked on the open question
in §7 and explicit go-ahead (feature development was paused in favor of PM-00 documentation before this
was built).

## 1. Precondition check

No `Problem` model exists anywhere in the active codebase (`grep -rln "class Problem" apps/` → no
matches). There is an unregistered, empty scaffold at `apps/problem_management/` (`models.py`,
`known_errors.py`, `rca.py` are all 0 bytes; the app is not in `INSTALLED_APPS` — see
[ARCHITECTURE.md](ARCHITECTURE.md) §2). This design does **not** build on that scaffold — it treats it as
dead and builds fresh inside `apps/service_desk`, the only registered, migrated, tested app.

## 2. New models — new files under `apps/service_desk/models/`

`apps/service_desk/models.py` (the dead flat file, see ARCHITECTURE.md §4) is **not** touched by this
design. New models go in the active `models/` package.

### `models/problem.py` — `Problem`

| Field | Type | Notes |
|---|---|---|
| `title` | `CharField(200)` | |
| `description` | `TextField` | |
| `status` | `CharField`, choices | `open` / `investigating` / `known_error` / `resolved` / `closed` — lowercase, mirrors `Ticket.STATUS_CHOICES` |
| `priority` | `CharField`, choices | `low`/`medium`/`high`/`urgent` — mirrors `Ticket.PRIORITY_CHOICES` |
| `root_cause` | `TextField`, blank | populated during investigation |
| `workaround` | `TextField`, blank | interim mitigation while unresolved |
| `is_known_error` | `BooleanField`, default `False` | ITIL "Known Error" flag |
| `department` | FK → `Department`, `SET_NULL`, `related_name="problems"` | |
| `created_by` | FK → user, `CASCADE`, `related_name="created_problems"` | |
| `assigned_to` | FK → user, `SET_NULL`, `related_name="assigned_problems"` | investigator/owner |
| `related_tickets` | `ManyToManyField(Ticket, blank=True, related_name="problems")` | see §3 |
| `created_at` / `updated_at` | auto | |

`Meta`: indexes on `status`, `priority`, `department`, `assigned_to`, matching `Ticket`'s indexing style.

### `models/problem_history.py` — `ProblemHistory`

Structural mirror of `TicketHistory`: FK to `Problem` (`related_name="history"`), `event_type` choices
(`created`, `updated`, `status_changed`, `assigned`, `unassigned`, `root_cause_updated`,
`workaround_updated`, `known_error_declared`, `ticket_linked`, `ticket_unlinked`, `comment`, `closed`,
`reopened`), `performed_by`, `old_value`/`new_value`, `comment`, `metadata` (`JSONField`), `created_at`,
classmethod `record(...)`.

### Edit required: `models/__init__.py`

Append `Problem`, `ProblemHistory` to the existing imports/`__all__` — additive only, same pattern already
used for `Ticket`/`Department`/`RequestType`/`TicketHistory`.

## 3. Relationship to `Ticket` — deliberately non-invasive

`related_tickets` is a `ManyToManyField` declared on `Problem`, pointed at `Ticket`. This was chosen
specifically so **`Ticket` requires zero changes** — no new column, no migration touching the
already-fragile `Ticket` model. The M2M also matches ITIL reality better than a FK would: one problem can
explain many incidents, and (less commonly but validly) an incident can eventually be linked under more
than one candidate problem during investigation before narrowing down.

## 4. Migration

One new migration: `apps/service_desk/migrations/0004_problem_problemhistory.py`, generated via
`manage.py makemigrations service_desk` — creates `Problem`, `ProblemHistory`, and the `related_tickets`
M2M through-table. No manual SQL. No changes to migrations 0001–0003.

## 5. Services — new file `apps/service_desk/services/problem_service.py`

Mirrors `TicketService`'s static-method / `@transaction.atomic` style:

- `create_problem(**data)`, `update_problem(problem, user=None, **fields)` (diff-tracked, same pattern as
  `update_ticket`)
- `assign_problem` / `unassign_problem`
- `change_status(problem, status, user=None)` with a `STATUS_FLOW` map:
  `open → investigating`, `investigating → known_error | resolved`, `resolved → closed`, `closed → open`
- `record_root_cause`, `record_workaround`
- `mark_known_error(problem, user=None)` — raises `ValidationError` if `root_cause` is empty (enforces
  that RCA actually happened before declaring a known error)
- `link_ticket` / `unlink_ticket` — manage the M2M and log `ProblemHistory`
- `add_comment`, `close_problem`, `reopen_problem`, `delete_problem`

Every mutation writes a `ProblemHistory` row, same discipline as `TicketService`.

## 6. Selectors — new file `apps/service_desk/selectors/problem_selector.py`

Mirrors `TicketSelector`: `_base_queryset()`, `get_by_id`, `get_by_status`, `get_by_priority`,
`get_by_department`, `get_by_assignee`, `get_open_problems`, `get_known_errors`, `get_recent_problems`,
`search`, `dashboard_statistics`, plus `get_problems_for_ticket(ticket)` (reverse M2M — powers a "linked
problems" panel on the ticket detail page in a later milestone).

## 7. Security — open decision required before implementation

Edits (append-only) to two existing files:

- **`security/policies.py`**: add `get_problem_queryset(user)`, structurally identical to
  `get_ticket_queryset` — Administrator → all, Manager → `department__in=managed_departments`,
  Technician → `assigned_to=user`.

  **Open question, unresolved:** should `Requester` see any problems? `get_ticket_queryset` gives
  requesters their own tickets; Problem Management is normally an internal ITIL process the requester
  role doesn't touch directly. Default proposed here is **Requester → `Problem.objects.none()`**, but this
  needs an explicit decision — implementation should not proceed with a silent default on this point.

- **`security/mixins.py`**: add `ProblemPermissionMixin`, `ProblemViewPermissionMixin`,
  `ProblemCreatePermissionMixin` (`service_desk.add_problem`), `ProblemChangePermissionMixin`,
  `ProblemDeletePermissionMixin` — same shape as the existing `Ticket*PermissionMixin` set. No custom
  permission model needed: Django auto-creates `view_problem`/`add_problem`/`change_problem`/
  `delete_problem` once `Problem` is migrated.

- **`management/commands/create_roles.py`**: needs editing (append, not rewrite) to grant the new
  `Problem` permissions per role, mirroring how it already grants `Ticket` permissions.

## 8. Views / URLs

New CBVs appended to `apps/service_desk/views.py`: `ProblemListView`, `ProblemDetailView`,
`ProblemCreateView`, `ProblemRootCauseUpdateView`. New routes appended to `apps/service_desk/urls.py`:
`/problems/`, `/problems/new/`, `/problems/<pk>/`, `/problems/<pk>/root-cause/`. Existing routes
untouched.

## 9. Templates

New files under `templates/problems/` (mirrors `templates/tickets/`): `list.html`, `detail.html`,
`create.html`, `edit.html` (RCA fields: root cause / workaround / known-error toggle). This design
deliberately does **not** touch `templates/sidebar.html` or `templates/includes/sidebar.html` to add
navigation — those were just stabilized in the FE-01 commits; adding a nav link needs its own explicit
approval, separate from this feature.

## 10. Admin

Append to `apps/service_desk/admin.py`: `ProblemAdmin` (list/filter/search mirroring `TicketAdmin`),
`ProblemHistoryAdmin` (read-only, audit-trail style).

## 11. Tests

New file `apps/service_desk/test_suite/test_problem_management.py`, same `TestCase` +
Users/Groups/Departments setup pattern as `test_authorization.py`:
- RBAC visibility per role for `get_problem_queryset` (mirrors the four existing authorization tests)
- Status-flow enforcement (invalid transition raises `ValidationError`)
- `mark_known_error` requires non-empty `root_cause`
- `link_ticket`/`unlink_ticket` correctness + history logging
- `ProblemSelector.dashboard_statistics` counts

## 12. Full file inventory

| New files | Existing files edited (append only) |
|---|---|
| `models/problem.py`, `models/problem_history.py` | `models/__init__.py` (2 exports) |
| `services/problem_service.py` | `admin.py` (register 2 models) |
| `selectors/problem_selector.py` | `security/policies.py` (1 function) |
| `test_suite/test_problem_management.py` | `security/mixins.py` (5 mixins) |
| `templates/problems/*.html` (3–4 files) | `views.py` (4 CBVs) |
| 1 new migration file | `urls.py` (4 routes) |
| | `management/commands/create_roles.py` (grant new perms) |

`models.py` (dead file), `forms/`, existing templates, existing migrations, and `settings.py` are not
touched by this design.
