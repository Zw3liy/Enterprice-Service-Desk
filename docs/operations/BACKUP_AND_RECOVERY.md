# Backup and Recovery

## What is backed up

`python manage.py backup_database` writes a timestamped JSON fixture containing every
`auth.User`, every `auth.Group` (and their membership), and everything in the
`service_desk` app — every ticket, problem, supplier, SLA policy/clock/escalation,
notification, service catalogue item and request, change, release, configuration item
and relationship, and knowledge article, with their full history/audit tables. This is
the complete application state a restore needs to reconstruct the desk.

**Not included, and backed up separately:**

- **Uploaded ticket attachments** (`MEDIA_ROOT`) are files on disk, not database rows —
  back up the media volume/directory itself (a filesystem or object-storage snapshot,
  depending on deployment) on the same schedule as the database.
- **`auth.Permission` and `contenttypes`** are deliberately excluded — both are
  regenerated deterministically by `migrate` and `create_roles`/`bootstrap_service_desk`
  on the restore target, and restoring their old primary keys onto a freshly migrated
  schema is a well-known `loaddata` integrity-error source, not a real backup need.
- **Sessions** are excluded — they are short-lived and regenerate on next login.

## Two backup formats, two purposes

| | JSON (`backup_database`) | `pg_dump` (native PostgreSQL) |
|---|---|---|
| Portable across SQLite/PostgreSQL | Yes | No (PostgreSQL only) |
| Automatically restore-verifiable by this repo's tooling | Yes (`verify_backup`) | No — verify with a real `pg_restore` into a disposable instance |
| Captures exact binary state, sequences, indexes | No | Yes |
| Recommended for | CI, cross-environment migration, the automated restore check below | Production disaster recovery |

Run **both** in production: the JSON backup for automated, tooling-verified
restorability (see below), and a native `pg_dump` for full-fidelity disaster recovery.

```bash
# Native PostgreSQL backup (run wherever DATABASE_URL is reachable)
pg_dump "$DATABASE_URL" --format=custom --file="service_desk_$(date -u +%Y%m%dT%H%M%SZ).pgdump"

# Restore into a *disposable* verification database — never the live one
createdb service_desk_restore_check
pg_restore --dbname=service_desk_restore_check service_desk_20260828T120000Z.pgdump
psql service_desk_restore_check -c "SELECT count(*) FROM service_desk_ticket;"
dropdb service_desk_restore_check
```

## Backups are timestamped and verified non-empty

`backup_database` names every file `service_desk_backup_<UTC-timestamp>.json`
(`20260828T140000Z` format — sortable, unambiguous, no timezone confusion) and refuses
to leave behind a zero-byte file: if `dumpdata` fails outright, or the file is 0 bytes
after writing, the command raises `CommandError` and deletes the partial file rather
than reporting success. (An empty-but-legitimate database still serializes to a valid,
non-zero-byte `[]` — that is a successful backup of an empty database, not a failure;
the two are deliberately not confused.)

## Restorability is automatically verified — into a disposable database, never the live one

```bash
python manage.py backup_database
python manage.py verify_backup backups/service_desk_backup_20260828T140000Z.json
```

`verify_backup` restores the named backup into a brand-new SQLite file inside a
temporary directory it creates and deletes itself — it never touches
`settings.DATABASES["default"]` (SQLite in development, PostgreSQL in production) and
never modifies any file outside that temporary directory. It reports how many users,
groups, tickets and changes were restored, then discards the disposable database. This
is what "restorable" means as an automated, repeatable check rather than a claim taken
on faith — run it immediately after every `backup_database` call, including in a
scheduled backup job (a backup that fails `verify_backup` should alert exactly like a
failed backup would).

**This tooling never deletes or modifies a production volume.** Every database it
creates lives in a `tempfile.TemporaryDirectory()` and is destroyed when the command
exits; the only file `backup_database` writes outside a temp directory is the backup
itself, and it never writes to or deletes an existing file.

## Scheduling

Same infrastructure-layer principle as `process_sla` (see
[SLA_SCHEDULING.md](SLA_SCHEDULING.md)): this is a one-shot command with no background
thread of its own, triggered externally.

**cron / systemd timer (Linux):**
```cron
0 2 * * * cd /opt/service-desk && /opt/service-desk/.venv/bin/python manage.py backup_database && /opt/service-desk/.venv/bin/python manage.py verify_backup "$(ls -t backups/*.json | head -1)"
```

**Windows Task Scheduler:** a daily Basic Task at 02:00, action "Start a program"
pointing at the venv's `python.exe` with arguments `manage.py backup_database`, "Start
in" set to the project root — same setup pattern as `process_sla` in
[SLA_SCHEDULING.md](SLA_SCHEDULING.md)'s Windows section, including the same
environment-variable caveat (Task Scheduler does not read `.env`).

**Containers:** run as a Kubernetes CronJob or host-cron `docker run`/`docker compose
run` against the application image, exactly like the `process_sla` container pattern in
SLA_SCHEDULING.md — never as a second loop inside the long-running web container.

## Retention

Documented default (adjust to actual compliance/regulatory requirements for the
deployment):

- Daily backups retained for 14 days.
- One backup per week retained for 3 months.
- One backup per month retained for 1 year.

A simple retention pass (delete files matching `service_desk_backup_*.json` older than
the policy above) can run immediately after a successful `verify_backup` in the same
scheduled job — never delete a backup that has not yet been verified restorable.

## Recovery objectives

Documented defaults — set these to the organization's actual requirements before
relying on this schedule:

- **RPO (Recovery Point Objective): 24 hours** — matches the daily backup schedule
  above. Reduce by increasing backup frequency (e.g. every 4 hours) if a shorter RPO is
  required; the same `backup_database`/`verify_backup` pair scales to any interval.
- **RTO (Recovery Time Objective): a few hours** — dominated by provisioning a
  replacement database/environment and running the restore, not by the restore
  operation itself (which, per `verify_backup`'s own timing, is fast even for a
  realistically sized dataset).

## Production restore procedure

The commands in this repository restore-*verify* into a disposable database; they are
deliberately **not** a "restore into production" command, because that action is
inherently destructive to whatever is currently in the target database and must never
be automatic. To actually recover a production environment:

1. Stop the application from writing further data (maintenance mode, or scale the web
   deployment to zero).
2. Provision or identify the target PostgreSQL instance.
3. Restore the most recent **verified** backup:
   - Native path (preferred for production): `pg_restore` from the matching `pg_dump`
     file, per the commands above, against the real target database.
   - JSON path: `python manage.py loaddata service_desk_backup_<timestamp>.json`
     against the target database, after `python manage.py migrate` has been run against
     it.
4. Restore the media volume/directory from its own backup, into the path
   `DJANGO_MEDIA_ROOT` points at.
5. Run `python manage.py check` and hit `/health/ready/` before resuming traffic.
6. Perform an authenticated smoke test (log in, open a ticket, confirm an attachment
   downloads) before declaring recovery complete.
7. Resume the application.

Never perform steps 2-4 against the live LAN deployment's database or media volume as
part of routine testing or verification — those steps are the actual recovery
procedure, exercised only during a genuine incident or a deliberately scheduled DR
drill against a separate, disposable target explicitly provisioned for that drill.
