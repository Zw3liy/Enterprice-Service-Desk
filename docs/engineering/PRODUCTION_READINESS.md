# Production Readiness

**Status: the application layer is complete and verified; deployment is not.**

This document is deliberately honest about the line between "the code is finished" and "this is
running in production". Everything under *Ready* has been implemented and is covered by automated
tests. Everything under *External requirements* is a deployment-environment input that no amount of
repository work can satisfy.

Last verified: Enterprise Completion Program, Phase 1, branch
`feature/service-desk-enterprise-completion-20260828-170022`, on top of `main` at `f5aeccf` (PR #7 merged).

---

## Verification commands and results

Run from the repository root against the declared dependencies only (`pip install -r requirements.txt`,
`Django==5.2.16`). Test runs use `DJANGO_SETTINGS_MODULE=ticketing.test_settings` — see
[ADR-011](ADR/ADR-011-Completion-Program-Foundations.md) — which changes only password-hashing speed for
throwaway test-database users; every other setting is inherited unchanged from `ticketing.settings`.

| Command | Result |
|---|---|
| `python manage.py check` | exit 0 — "System check identified no issues (0 silenced)" |
| `python manage.py makemigrations --check --dry-run` | exit 0 — "No changes detected" |
| `python manage.py showmigrations --plan` | exit 0 — `service_desk` `0001`–`0011` |
| `python manage.py test --parallel auto` (`ticketing.test_settings`) | exit 0 — **296 tests, OK**, ~8-11s |
| `python manage.py check --deploy` | exit 0 — **1 warning** (`security.W004`) when run with a real `DJANGO_SECRET_KEY` and `DJANGO_DEBUG=0`; a second warning (`security.W009`) appears only if the check is run with the development fallback key |

### `check --deploy` warnings, explained

| Warning | Why it is not a defect |
|---|---|
| `security.W004` (HSTS not set) | `SECURE_HSTS_SECONDS` is opt-in via `DJANGO_SECURE_HSTS_SECONDS` and defaults to 0. Enabling HSTS before HTTPS works end-to-end can lock a domain out for the length of the max-age; this is a deliberate deployment decision, documented in `.env.example`, not an oversight. |
| `security.W009` (weak `SECRET_KEY`) | Only raised when the check is run with the development fallback key or a throwaway value; it disappears once a real key is supplied (verified). In any non-DEBUG environment the application **refuses to start** without a real `DJANGO_SECRET_KEY` (see `ticketing/settings.py`). |

Everything else `check --deploy` inspects — `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS`, `DEBUG` — is already correct
and switches on automatically as soon as `DJANGO_DEBUG` is false.

---

## Ready

- **Incident Management** — lifecycle, work notes, secure attachments, requester confirmation.
- **Problem Management** — records, RCA authoring (Five Whys, Fishbone, Evidence, CAPA, Approvals),
  known errors, ticket linking, repeat-incident candidates.
- **Supplier Management** — list, create, detail, update, active/inactive lifecycle, department
  scoping, scoped search and filtering.
- **SLA Management** — priority/department policies, frozen per-ticket deadlines, warning and breach
  detection, idempotent escalation records, `process_sla` command, scoped dashboard.
- **Notifications** — in-app records for assignment, status change, confirmation request and
  confirmation, SLA warnings and breaches, and Problem sign-off events. Email is an optional,
  fail-safe mirror.
- **RBAC** — Requester / Technician / Manager / Administrator, enforced by policies + mixins, with
  regression tests on every boundary this session touched.
- **Security posture** — env-driven secrets, CSRF on every state-changing POST, attachment
  allowlist and size cap, scoped downloads, no credential-shaped strings in the tree (asserted by a
  test that scans the repository).
- **CI** — `django-tests.yml` runs `check`, the migration drift check and the full suite on every
  push and pull request.

---

## Database

**Corrected this session (2026-08-28):** the two paragraphs below describing `DATABASES` as hardcoded to
SQLite with no env-driven path were true when originally written but are now stale — verified directly
against the current files rather than left uncorrected. `ticketing/production_settings.py` (env-driven,
`dj_database_url.parse(DATABASE_URL, ...)`, refuses to start without `DATABASE_URL`) and
`ticketing/postgres_test_settings.py` (CI-safe layer over it) both already exist, `psycopg[binary]` and
`dj-database-url` are already in `requirements.txt`, and `.github/workflows/deployment.yml` already runs
the full migration/rollback/reapply/test cycle against a real PostgreSQL 16 service container on every
push/PR. `ticketing/settings.py` (local dev default, used when no `DJANGO_SETTINGS_MODULE` override is
set) intentionally still hardcodes SQLite — that default is correct for zero-setup local development, not
a gap.

Development defaults to SQLite (`db.sqlite3`) when `ticketing.settings` is used directly; every migration
in this repository applies cleanly there. Production uses PostgreSQL through `ticketing.production_settings`:

- **SQLite is not suitable for production.** It serialises writes, which the SLA processor and
  concurrent ticket updates will contend on, and it offers no network access for multiple app
  processes. This is why `ticketing.production_settings` requires `DATABASE_URL` and refuses to start
  without it.
- **Production database: PostgreSQL 14+** (`postgres:16-alpine` in `compose.yaml`/CI). The schema uses
  only portable field types (`JSONField`, `DurationField` arithmetic, partial-free unique constraints and
  indexes) — no migration rewrite was needed. Exercised in CI (`deployment.yml`
  `postgres-verification` job): migrate from empty, full test suite, rollback `0011`/`0010` to `0009`,
  reapply, confirm zero drift.

Rollback: **verified, not assumed.** Against a disposable SQLite database this session ran
`migrate` (forward, clean), `migrate service_desk 0008` (rolls `0010` and `0009` back, clean) and
`migrate service_desk` again (re-applies, clean), confirming the four new tables
(`service_desk_slapolicy`, `service_desk_ticketsla`, `service_desk_slaescalation`,
`service_desk_notification`) are created and dropped correctly. Every migration in `0001`–`0010` is a
plain `CreateModel`/`AlterField` set with no data migration, and `0009`/`0010` only *add* tables, so
reversing them cannot lose ticket, problem or supplier data.

---

## External requirements (cannot be satisfied in this repository)

| Requirement | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | Long random value. The app refuses to start without one when `DJANGO_DEBUG` is false. |
| `DJANGO_ALLOWED_HOSTS` | Real hostnames for the deployment. |
| TLS termination | `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` turn on with `DEBUG=false` and assume HTTPS is actually terminated in front of the app. |
| `DJANGO_SECURE_HSTS_SECONDS` | Raise gradually once HTTPS is proven end-to-end. |
| SMTP credentials | Only needed if `DJANGO_EMAIL_NOTIFICATIONS` is turned on. Everything works without them. |
| PostgreSQL instance | See above. |
| A scheduler for `process_sla` | cron, systemd timer or equivalent. The command is idempotent and safe to run every minute. No broker or worker dependency is introduced. |
| Static file serving | `collectstatic` into `STATIC_ROOT`, served by the web server or a CDN. |
| Media storage for attachments | `MEDIA_ROOT` must be persistent and **must not** be served directly by the web server: downloads are deliberately proxied through `TicketAttachmentDownloadView` so RBAC applies. |
| Backups | No backup strategy is defined in this repository. |

---

## Known remaining code-side work

1. `templates/tickets/ticket-*.html`, `tickets/dashboard.html`, `tickets/list.html` and
   `tickets/timeline.html` are unreferenced. Reference-count evidence suggests they are dead, but
   they were not covered by prior inspection, so they were left in place rather than deleted on a
   guess.
2. ~128 unregistered scaffold app directories remain outside `apps/service_desk` (re-counted
   2026-08-28; includes the now-superseded empty `apps/service_desk/{sla,notifications,cmdb,knowledge,
   reporting,automation,identity,api,filters}/` packages). Their removal is a scope decision, not a
   defect — this program's new modules do not write into any of them (ADR-011).
3. ~~`DATABASES` is not yet env-driven~~ — **done**, see Database above (corrected 2026-08-28; this item
   was stale).
4. Service Request Management, Change Management, Release Management, CMDB and Knowledge Management are
   the Enterprise Completion Program's remaining scope — see `ITSM_ROADMAP.md` and
   [SESSION_STATE.md](SESSION_STATE.md) for live status.
