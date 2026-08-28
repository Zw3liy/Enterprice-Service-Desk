# SLA Scheduler Setup

`python manage.py process_sla` evaluates every live SLA clock, raises warning/breach
`SLAEscalation` records (idempotent — see below), and writes one `SLARunLog` row per
execution. It is a plain Django management command: it runs once, does its work, and
exits. **It deliberately starts no thread, timer, or loop of its own** — running it on a
schedule is an external, infrastructure-layer responsibility, not something the Django
process manages for itself. This matters operationally: an unmanaged background thread
started inside a web worker process is invisible to process supervisors, gets duplicated
across every worker/replica, and silently dies on a worker restart with no alert. A
command triggered by cron/systemd/Task Scheduler/Kubernetes CronJob is visible to those
tools, has its own exit code, and scales correctly (each scheduler tick runs exactly once,
regardless of how many web workers are running).

## Idempotency and duplicate-notification prevention

Safe to run every minute, or after a missed run, or twice in quick succession:

- `SLAEscalation` has `UniqueConstraint(fields=["ticket_sla", "kind"])` — the same warning
  or breach for the same ticket is written at most once, ever, enforced at the database
  level (not just application logic that a race condition could slip past).
- `SLAService.evaluate()` only notifies for escalations it just created
  (`get_or_create`'s `was_created` flag) — a clock that already has its warning recorded
  produces no further notification on subsequent runs.
- Running the command with no due clocks is a no-op: it still writes an `SLARunLog` row
  (`processed_count` reflecting how many active clocks it checked, `warnings_count`/
  `breaches_count` at 0) so "the scheduler is alive but nothing was due" is
  distinguishable from "the scheduler did not run".

Verify with `python manage.py process_sla --dry-run` first in any new environment — it
reports what *would* be escalated without writing anything.

## Monitoring

Every non-dry-run execution writes one `SLARunLog` row: `started_at`, `finished_at`,
`processed_count`, `warnings_count`, `breaches_count`, `succeeded`, and — on failure —
`error_message` (the command re-raises after recording the failure, so the external
scheduler still sees a non-zero exit code and can alert on it independently). The 10 most
recent runs are shown on the SLA dashboard (`/sla/`) to anyone who can manage SLA policies
(Manager/Administrator). Query directly for alerting:

```python
from apps.service_desk.models import SLARunLog
from django.utils import timezone
from datetime import timedelta

last = SLARunLog.objects.filter(succeeded=True).order_by("-started_at").first()
stale = last is None or last.started_at < timezone.now() - timedelta(minutes=10)
```

("No successful run in the last N minutes, where N is a small multiple of your scheduled
interval" is the standard health check for this kind of job.)

## Windows Task Scheduler

Run from the project's virtual environment so the correct interpreter and installed
packages are used. Adjust paths for the actual deployment location.

```powershell
schtasks /Create /TN "ServiceDesk-ProcessSLA" /SC MINUTE /MO 1 /RL LIMITED `
  /TR "'C:\ServiceDesk\.venv\Scripts\python.exe' 'C:\ServiceDesk\manage.py' process_sla" `
  /RU "DOMAIN\svc-servicedesk"
```

Or via Task Scheduler's GUI: create a Basic Task, trigger "Repeat task every: 1 minute,
for a duration of: Indefinitely", action "Start a program" pointing at the venv's
`python.exe` with arguments `manage.py process_sla` and "Start in" set to the project
root (`manage.py` resolves settings relative to its own directory). Run whether or not
the user is logged on, using a dedicated service account — not an interactive user
session, which Task Scheduler can suspend.

Required environment variables (`DJANGO_SETTINGS_MODULE`, `DATABASE_URL`, etc. — see
`.env.example`) must be available to the task's process. Task Scheduler does not read a
`.env` file; either set them as system/user environment variables for the service
account, or wrap the command in a small `.bat`/`.ps1` launcher that sets them explicitly
before invoking `python.exe`.

## cron / systemd (Linux hosts)

```cron
* * * * * cd /opt/service-desk && /opt/service-desk/.venv/bin/python manage.py process_sla >> /var/log/service-desk/sla.log 2>&1
```

Or a systemd timer (preferred on systemd hosts — gives you `systemctl status`,
`journalctl`, and automatic restart-on-failure semantics cron lacks):

```ini
# /etc/systemd/system/service-desk-sla.service
[Unit]
Description=Enterprise Service Desk SLA processing

[Service]
Type=oneshot
WorkingDirectory=/opt/service-desk
EnvironmentFile=/opt/service-desk/.env
ExecStart=/opt/service-desk/.venv/bin/python manage.py process_sla
```

```ini
# /etc/systemd/system/service-desk-sla.timer
[Unit]
Description=Run Enterprise Service Desk SLA processing every minute

[Timer]
OnCalendar=*-*-* *:*:00
AccuracySec=1s
Persistent=true

[Install]
WantedBy=timers.target
```

`Persistent=true` means a run missed while the host was down (maintenance, reboot) fires
once on the next boot rather than being silently skipped — safe because of the
idempotency guarantees above.

## Containers (Docker / Kubernetes)

The application container (`Dockerfile` at the repo root) runs the web process only —
`process_sla` is **not** started inside it, deliberately, so scaling the web deployment
horizontally never multiplies scheduler runs. Run it as a separate, single-replica
scheduled workload against the same image:

**Kubernetes CronJob:**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: service-desk-process-sla
spec:
  schedule: "* * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: process-sla
              image: service-desk:<tag>
              command: ["python", "manage.py", "process_sla"]
              envFrom:
                - secretRef:
                    name: service-desk-env
          restartPolicy: OnFailure
```

`concurrencyPolicy: Forbid` prevents overlapping runs if one execution runs long — belt
and braces on top of the command's own idempotency.

**Docker Compose / plain Docker host**, using the same image as the web service, via the
host's own cron calling `docker run`/`docker compose run`:

```cron
* * * * * docker compose -f /opt/service-desk/compose.yaml run --rm web python manage.py process_sla
```

Never add a second `command:` entry to the long-running `web` service in `compose.yaml`
to "also" run `process_sla` in a loop inside that container — that reintroduces exactly
the unmanaged-background-thread problem this design avoids, just moved into a shell
script instead of a Python thread.
