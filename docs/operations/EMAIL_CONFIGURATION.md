# Email Configuration

The service desk writes an in-app `Notification` row for **every** notifiable event
regardless of email configuration — email is an optional mirror, never the primary
channel (see `services/notification_service.py`). A deployment with no SMTP
configuration at all is fully usable; nothing is lost, only the email copy.

## Required environment variables

All SMTP configuration comes exclusively from environment variables — no credential is
ever committed to this repository. See `.env.example` for the full list with inline
documentation; summarised here:

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_EMAIL_NOTIFICATIONS` | Master on/off switch. | `false` |
| `DJANGO_EMAIL_BACKEND` | Django email backend path. | `django.core.mail.backends.console.EmailBackend` |
| `DJANGO_EMAIL_HOST` | SMTP server hostname. | *(empty)* |
| `DJANGO_EMAIL_PORT` | SMTP port. | `587` |
| `DJANGO_EMAIL_HOST_USER` | SMTP auth username. | *(empty)* |
| `DJANGO_EMAIL_HOST_PASSWORD` | SMTP auth password/app-password. | *(empty)* |
| `DJANGO_EMAIL_USE_TLS` | Use STARTTLS. | `true` |
| `DJANGO_EMAIL_TIMEOUT` | Seconds before giving up on a hung connection. | `10` |
| `DJANGO_DEFAULT_FROM_EMAIL` | `From:` address for outgoing mail. | `service-desk@example.com` |

Leaving `DJANGO_EMAIL_NOTIFICATIONS` unset (or `false`) means no SMTP connection is ever
attempted — this is the correct state for local development and CI, and is what this
repository's test suite and `ticketing.settings` both default to.

## Backend suitable for tests

- **Local development / CI**: `django.core.mail.backends.console.EmailBackend` (the
  default) prints outgoing mail to stdout instead of sending it — no network access, no
  credentials needed.
- **Automated tests**: Django's test runner (`manage.py test`) automatically substitutes
  `django.core.mail.backends.locmem.EmailBackend` for the duration of the test run
  regardless of what `EMAIL_BACKEND` is configured to, capturing sent messages in
  `django.core.mail.outbox` — this is Django's own behaviour, not something this
  repository configures, and it applies even if `DJANGO_EMAIL_NOTIFICATIONS=true` were
  set in a test environment by mistake. `test_notifications.py` and the other
  notification-touching test modules assert against `mail.outbox` on this basis.
- **Production**: `django.core.mail.backends.smtp.EmailBackend`, configured via the
  variables above, pointed at a real provider (Microsoft 365, SES, SendGrid, an internal
  relay, ...).

## Safe failure

`NotificationService._send_email` wraps every send in `try/except Exception`, logs the
failure (`logger.exception`, notification ID and recipient address only — never the
subject, body, or any credential), and returns `False` rather than raising. The
in-app `Notification` row this wraps has already been committed by the time email is
attempted, so a broken or unreachable mail server can never roll back the business
transaction (ticket assignment, status change, etc.) that produced the notification —
verified by `test_notifications.py`'s failure-path tests.

## Verification procedure

1. Set the environment variables above for the target environment (never commit them —
   `.env` is gitignored; only `.env.example` is tracked).
2. Confirm Django can reach the SMTP server and authenticate, without touching any
   application data, using Django's built-in command:
   ```
   python manage.py sendtestemail you@example.com
   ```
   This sends one plain-text test message through whatever `EMAIL_BACKEND`/`EMAIL_HOST`/
   credentials are currently configured — success here means the service desk's own
   `NotificationService` will also be able to send.
3. Trigger one real in-app event (e.g. assign a ticket to yourself) with
   `DJANGO_EMAIL_NOTIFICATIONS=true` and confirm both:
   - the `Notification` row exists with `emailed=True`, and
   - the email actually arrived.
4. If step 3 shows `emailed=False`, check the application logs for the
   `Failed to email notification <id> to <address>` line (see "Safe failure" above) —
   the log line never contains the message body or SMTP credentials, only the
   notification ID and recipient, safe to paste into a support ticket.

## What is intentionally not built

No email templates beyond plain-text `subject`/`body` strings, no digest/batching, no
per-user notification preferences (subscribe/unsubscribe), no bounce handling. The
in-app `Notification` list is authoritative and always complete; email is a
best-effort convenience layer on top of it.
