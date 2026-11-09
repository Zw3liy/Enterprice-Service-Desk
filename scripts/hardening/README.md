# Server Hardening Kit

Idempotent, non-destructive scripts that harden and then *verify* the Linux
host that runs this platform (Docker + Nginx Proxy Manager + Portainer +
Uptime Kuma + PostgreSQL + Cloudflare Tunnel).

Read `docs/operations/SERVER_HARDENING.md` first — it is the runbook these
scripts implement, including the gap analysis of what is already in place.

## The scripts

| Script | What it does | Changes |
|---|---|---|
| `harden_ssh.sh` | sshd drop-in: key-only auth, modern crypto, no forwarding, brute-force limits, VERBOSE logging | writes `/etc/ssh/sshd_config.d/90-enterprise-service-desk.conf`, validates with `sshd -t`, reloads |
| `harden_kernel.sh` | sysctl anti-spoofing/redirect/TCP hardening, core-dump off, ASLR, blacklists rare kernel protocols | writes drop-ins under `/etc/sysctl.d/`, `/etc/security/limits.d/`, `/etc/modprobe.d/` |
| `harden_docker.sh` | daemon.json: `no-new-privileges`, `live-restore`, log rotation. Then audits privileged containers, docker.sock mounts, published ports, docker group | merges `/etc/docker/daemon.json` (never clobbers existing keys) |
| `harden_postgres.sh` | exposure audit (5432 binding, pg_hba, weak container passwords); native mode can apply scram-sha-256 + logging via `ALTER SYSTEM` | nothing unless `PG_APPLY=1` |
| `audit_hardening.sh` | **read-only** full posture audit — SSH, accounts, UFW, Fail2Ban, CrowdSec, auditd, rkhunter, sysctl, Docker, PostgreSQL, admin UIs, tunnel type, updates, backups, NTP. Scores PASS/WARN/FAIL, exit 1 on any FAIL | nothing, ever |

All file changes are backed up as `<file>.bak.<UTC-timestamp>` first. Every
config is validated before its service is reloaded. Tag `90-enterprise-service-desk`
marks everything this kit installs.

## Usage

```bash
# 0. Put the repo on the server (git clone), then:
cd Enterprice-Service-Desk/scripts/hardening

# 1. See what would happen first (all scripts honour this):
sudo DRY_RUN=1 ./harden_ssh.sh
sudo DRY_RUN=1 ./harden_kernel.sh
sudo DRY_RUN=1 ./harden_docker.sh
sudo DRY_RUN=1 ./harden_postgres.sh

# 2. Apply, one at a time, verifying after each:
sudo ./harden_ssh.sh          # keep your current SSH session open and
                              # open a SECOND terminal to verify login!
sudo ./harden_kernel.sh
sudo ./harden_docker.sh
sudo ./harden_postgres.sh

# 3. Score the result:
sudo ./audit_hardening.sh            # full audit (incl. rkhunter/SMART)
sudo ./audit_hardening.sh --quick    # fast version for cron
```

Recommended: schedule the audit and mail/ship the result off-host.

```cron
# /etc/cron.d/hardening-audit — weekly, root only
17 4 * * 1  root  /opt/Enterprice-Service-Desk/scripts/hardening/audit_hardening.sh --quick >> /var/log/hardening-audit.log 2>&1
```

## Safety notes

* **Never run `harden_ssh.sh` with `SSH_ALLOW_GROUPS`/`SSH_ALLOW_USERS` set
  until the group/user exists and you have verified key login as that user
  in a second session.** The defaults restrict nothing on *who* may log in —
  only *how* (public key only).
* `harden_docker.sh` restarts/reloads the engine unless
  `DOCKER_NO_RESTART=1`. With `live-restore` containers keep running, but
  expect a 1–2 s network blip.
* `harden_postgres.sh` changes nothing unless `PG_APPLY=1` (native) —
  container mode only prints the recommended compose snippet.
* The audit script is safe everywhere: it reads state and prints findings.

## Removing everything this kit installed

```bash
sudo rm /etc/ssh/sshd_config.d/90-enterprise-service-desk.conf \
        /etc/sysctl.d/90-enterprise-service-desk.conf \
        /etc/security/limits.d/90-enterprise-service-desk.conf \
        /etc/systemd/coredump.conf.d/90-enterprise-service-desk.conf \
        /etc/modprobe.d/90-enterprise-service-desk.conf
sudo systemctl reload ssh && sudo sysctl --system
# daemon.json keys are additive and safe to keep; remove them manually if you must.
```
