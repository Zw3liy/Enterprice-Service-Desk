# Master Data Bootstrap

Idempotent initialisation of Service Desk master data for empty or
partially-seeded environments.

## Command

```bash
python manage.py bootstrap_service_desk [options]
```

### Options

| Option | Purpose |
|---|---|
| `--dry-run` | Report what would change; write nothing |
| `--update-existing` | Refresh descriptions/targets on existing rows |
| `--skip-users` | Do not create or update seed users |
| `--create-seed-users` | Create the four default seed users |
| `--admin-username` / `--admin-email` | Administrator seed identity |
| `--manager-username` / `--manager-email` | Manager seed identity |
| `--technician-username` / `--technician-email` | Technician seed identity |
| `--requester-username` / `--requester-email` | Requester seed identity |

### Password input (never committed)

Passwords are read from the environment and hashed by Django. They are
never written to logs or command output.

| Variable | Scope |
|---|---|
| `BOOTSTRAP_ADMIN_PASSWORD` | Administrator only |
| `BOOTSTRAP_MANAGER_PASSWORD` | Manager only |
| `BOOTSTRAP_TECHNICIAN_PASSWORD` | Technician only |
| `BOOTSTRAP_REQUESTER_PASSWORD` | Requester only |
| `BOOTSTRAP_INITIAL_PASSWORD` | Shared fallback for any seed user |

Interactive `getpass` is used only when stdin is a TTY, `--create-seed-users`
is set, and no password environment variable is present.

## What is created

### Departments

Information Technology, Human Resources, Finance, Operations, Facilities,
Procurement, Security, Customer Support.

### Request types (all active)

Incident, Service Request, Access Request, Hardware Request, Software
Request, Network Request, Security Incident, General Enquiry.

Request types are global in the current schema (no department FK). The
bootstrap records the intended default department as documentation only.

### SLA policies (organisation-wide defaults)

| Name | Priority (stored) | Response | Resolution |
|---|---|---|---|
| Critical Priority Default | `urgent` | 15 min | 4 h |
| High Priority Default | `high` | 1 h | 8 h |
| Medium Priority Default | `medium` | 4 h | 24 h |
| Low Priority Default | `low` | 8 h | 72 h |

Uses the existing `SLAPolicy` model and `SLAService` — no competing SLA
package is introduced.

### Roles

Reuses `create_roles` so permission matrices stay single-sourced:

- **Requester** — `view_ticket`, `add_ticket`
- **Technician** — ticket view/add/change + problem view/add/change
- **Manager** — technician powers + supplier + SLA policy administration
- **Administrator** — full model permissions including delete

### Seed users (optional)

When `--create-seed-users` (or an explicit username option) is supplied:

| Username default | Role | Notes |
|---|---|---|
| `sd_admin` | Administrator | `is_staff` + `is_superuser` |
| `sd_manager` | Manager | Linked as manager of Information Technology |
| `sd_technician` | Technician | |
| `sd_requester` | Requester | |

## Safety guarantees

- Entire run is wrapped in `transaction.atomic()`; any failure rolls back.
- `--dry-run` forces a rollback even after a successful simulated apply.
- Repeat runs without `--update-existing` are no-ops for existing rows.
- Passwords never appear in structured results or stdout.

## Recommended first-boot sequence

```bash
python manage.py migrate --noinput
export BOOTSTRAP_INITIAL_PASSWORD='<strong unique secret>'
python manage.py bootstrap_service_desk --create-seed-users
# or, for master data only:
python manage.py bootstrap_service_desk --skip-users
```

## Upgrade / re-seed

```bash
python manage.py bootstrap_service_desk --dry-run
python manage.py bootstrap_service_desk --update-existing --skip-users
```
