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
| `harden_firewall.sh` | UFW zero-public-ports posture: default deny in/routed, rate-limited SSH from your management IP only, optional egress allowlist | `ufw` policies + rules, with lockout guards (SSH allow rule created **before** enable) |
| `harden_kernel.sh` | sysctl anti-spoofing/redirect/TCP hardening, core-dump off, ASLR, blacklists rare kernel protocols | writes drop-ins under `/etc/sysctl.d/`, `/etc/security/limits.d/`, `/etc/modprobe.d/` |
| `harden_updates.sh` | unattended security updates (no auto-reboot), needrestart auto-restart, bounded journald | `/etc/apt/apt.conf.d/*`, `/etc/needrestart/conf.d/`, `/etc/systemd/journald.conf.d/` |
| `harden_login.sh` | password quality (14+ mixed chars), lockout policy (5 fails → 15 min, incl. root), login.defs aging/umask for new accounts | `/etc/security/pwquality.conf`, `/etc/security/faillock.conf`, edited `/etc/login.defs` (backed up) |
| `harden_fail2ban.sh` | hardened jails: sshd (aggressive), recidive (4-week bans), exponential bantime, UFW ban action, NPM auth filter (ships disabled pending log verification) | `/etc/fail2ban/jail.d/`, `/etc/fail2ban/filter.d/`, validated with `fail2ban-client -t` |
| `harden_auditd.sh` | forensic ruleset: identity/sudoers/sshd/cron/docker/kernel-modules/time/mounts/deletes/perm changes, all `ausearch -k` tagged | `/etc/audit/rules.d/`, loaded via `augenrules --load` |
| `harden_monitoring.sh` | SMART disk warnings, rkhunter daily scans, weekly posture-audit cron (path-substituted to this checkout) | `/etc/smartd.conf`, `/etc/rkhunter.conf.local`, `/etc/cron.d/*` |
| `harden_docker.sh` | daemon.json: `no-new-privileges`, `live-restore`, log rotation. Then audits privileged containers, docker.sock mounts, published ports, docker group | merges `/etc/docker/daemon.json` (never clobbers existing keys) |
| `harden_postgres.sh` | exposure audit (5432 binding, pg_hba, weak container passwords); native mode can apply scram-sha-256 + logging via `ALTER SYSTEM` | nothing unless `PG_APPLY=1` |
| `harden_edge.sh` | NPM/nginx edge snippets (Cloudflare real-IP, rate-limit zones, security headers, TLS profile) + cloudflared named-tunnel template; prints paste/mount instructions with `nginx -t` verification steps | native nginx: `/etc/nginx/snippets/`; NPM/cloudflared: instructions + `/etc/cloudflared/config.yml.example` |
| `harden_all.sh` | runs everything above in a safe order, then scores the result | — |
| `audit_hardening.sh` | **read-only** full posture audit — SSH, accounts, UFW, Fail2Ban, CrowdSec, auditd, rkhunter, sysctl, Docker, PostgreSQL, admin UIs, tunnel type, updates, backups, NTP. Scores PASS/WARN/FAIL, exit 1 on any FAIL | nothing, ever |

Every script honours `DRY_RUN=1`. All file changes are backed up as
`<file>.bak.<UTC-timestamp>` first. Every config is validated before its
service is reloaded. Tag `90-enterprise-service-desk` marks everything
this kit installs. The raw config templates live in `configs/` (see
`configs/README.md` for the install map).

## Usage

```bash
# 0. Put the repo on the server (git clone), then:
cd Enterprice-Service-Desk/scripts/hardening

# 1. See what would happen first (every script honours this):
sudo DRY_RUN=1 ./harden_all.sh

# 2. Apply everything (or run scripts one at a time):
sudo ./harden_all.sh

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

* **`harden_firewall.sh` can lock you out if misconfigured.** It
  creates the SSH allow rule *before* enabling UFW, from
  `SSH_MGMT_CIDR` (preferred) or your current SSH client IP. Pin a
  permanent management IP; keep the session open; verify a second
  login. Use `UFW_EGRESS=deny` only when you are ready to maintain an
  egress allowlist.
* **Never run `harden_ssh.sh` with `SSH_ALLOW_GROUPS`/`SSH_ALLOW_USERS`
  set until the group/user exists and you have verified key login as
  that user in a second session.** The defaults restrict nothing on
  *who* may log in — only *how* (public key only).
* `harden_login.sh` installs the faillock *policy* but activating
  `pam_faillock` (via `pam-auth-update`) is a manual step — PAM stack
  changes can lock you out; do it with a second session open.
* `harden_fail2ban.sh` warns about `ignoreip`: add your management IP
  to the jail before pointing fail2ban at a live SSH surface.
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
        /etc/modprobe.d/90-enterprise-service-desk.conf \
        /etc/systemd/journald.conf.d/90-enterprise-service-desk-retention.conf \
        /etc/audit/rules.d/90-enterprise-service-desk.rules \
        /etc/fail2ban/jail.d/90-enterprise-service-desk.local \
        /etc/fail2ban/filter.d/npm-auth.conf \
        /etc/apt/apt.conf.d/51-enterprise-service-desk \
        /etc/needrestart/conf.d/90-auto.conf \
        /etc/security/faillock.conf \
        /etc/rkhunter.conf.local \
        /etc/cron.d/rkhunter /etc/cron.d/hardening-audit
sudo systemctl reload ssh && sudo sysctl --system && sudo augenrules --load
# Replaced originals are kept as <file>.bak.<timestamp> next to each target.
# /etc/security/pwquality.conf, /etc/smartd.conf, /etc/login.defs and
# /etc/apt/apt.conf.d/20auto-upgrades: restore the newest .bak copy.
# daemon.json keys are additive and safe to keep; remove them manually if you must.
```
