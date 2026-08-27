# Production Deployment

## Required infrastructure

- PostgreSQL 14 or newer
- HTTPS reverse proxy or managed TLS termination
- Persistent private media storage
- SMTP provider when email notifications are enabled
- Centralized application logs and uptime monitoring
- Scheduled execution of `python manage.py process_sla`
- Encrypted database and media backups

## Release procedure

1. Back up PostgreSQL and verify the backup can be read.
2. Build the immutable application image.
3. Run the full CI pipeline against PostgreSQL.
4. Run migrations as a dedicated release operation.
5. Run `collectstatic`.
6. Deploy the application image.
7. Verify `/health/live/` and `/health/ready/`.
8. Perform authenticated ticket, attachment and RBAC smoke tests.

## Rollback

1. Stop further deployment.
2. Restore the previous application image.
3. Do not reverse a migration until its reversibility and data impact have
   been tested on a disposable database.
4. Restore the verified database backup when application rollback alone
   cannot restore compatibility.
5. Verify health endpoints and RBAC workflows.

## SLA scheduler

Run `python manage.py process_sla` using cron, systemd or the hosting
platform scheduler. Configure only one active scheduler instance or use
an external lock to prevent overlapping runs. Test first with
`python manage.py process_sla --dry-run`.

## Protected media

Ticket attachments must be downloaded through the authenticated,
RBAC-scoped Django view. Do not configure the reverse proxy to expose
MEDIA_ROOT directly.

## HSTS

Keep `DJANGO_SECURE_HSTS_SECONDS=0` until HTTPS and all required
subdomains have been verified. Increase it gradually. Enable preload
only after confirming preload requirements and organizational approval.
