# Server Hardening — Assessment & Runbook

This is the security runbook for the Linux host that runs the Enterprise
Service Desk platform (Docker, Nginx Proxy Manager, Portainer, Uptime Kuma,
PostgreSQL, Cloudflare Tunnel). It records what is already in place, the
residual gaps that matter, and the exact steps to close them. The executable
part of this runbook lives in `scripts/hardening/` (see its README).

> **An honest word first.** No server is "non-penetrable". Anyone promising
> that is selling something. The realistic goal is three-fold:
> 1. **Raise the cost** of an attack far above the value of what is on the box
>    (defence in depth — every layer assumes the one before it fails).
> 2. **Detect early** — assume breach, make sure nothing happens silently.
> 3. **Recover fast** — tested, off-host, encrypted backups make most
>    attackers economically pointless.
>
> Every section below serves one of those three goals.

---

## 1. Current posture (what is already done — and what each control still leaves open)

| Control | Status | What it gives you | Residual gap |
|---|---|---|---|
| SSH key-only auth, root login off, password auth off | ✅ | Kills the #1 brute-force vector | Old ciphers still offered; no `AuthenticationMethods publickey`; forwarding/tunnelling still allowed; log level not VERBOSE (weakens fail2ban/crowdsec/forensics) |
| UFW firewall | ✅ | Blocks stray ports | Verify **default deny incoming** and that 80/443/5432/9443/81/3001/8000 are not open "Anywhere". With a tunnel you need **zero** public inbound ports |
| Fail2Ban + CrowdSec | ✅ | Reactive IP banning | Confirm crowdsec has a **bouncer actually registered** (decisions without a bouncer enforce nothing). Confirm sshd jail exists in fail2ban. Add alerting on bans |
| Auditd | ✅ | Forensic trail | Confirm rules watch `/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/sudoers`, sshd config, and the Docker binary. Ship audit logs **off this host** |
| RKHunter + SMART + auto-updates | ✅ | Rootkit/disk/patch hygiene | RKHunter only helps if it **runs on a schedule and someone reads the report**; schedule it and alert on warnings. Auto-updates need a **reboot policy** (`needrestart`/reboot-required checks) |
| Docker + PostgreSQL + GitHub deployment | ✅ | Modern app stack | Containers default to more privilege than needed; Postgres may be published on the host; `docker.sock` access = root |
| Cloudflare Tunnel (**Quick** Tunnel) | ✅ | Origin hidden, DDoS-scrubbed | **This is the biggest gap** — see §3.1. Quick tunnels are ephemeral, unsigned, and support **no Access policies** |
| Backups + cron (Postgres & Docker) | ✅ | Recovery capability | Backups that live on the same box die with it. They must be **off-host, encrypted, and restore-tested** — see §3.4 |
| Nginx Proxy Manager / Portainer / Uptime Kuma | ✅ | Convenient ops surface | Every one of these admin panels is a full-control or high-value target. Each must be behind Access/VPN, MFA-protected, and never internet-exposed |

---

## 2. The hardening kit (executable controls)

`scripts/hardening/` implements the host-level layer. After running
`sudo ./harden_all.sh` (or each `harden_*.sh` individually) and
`sudo ./audit_hardening.sh`, the host profile is:

* **SSH**: public-key-only (`AuthenticationMethods publickey`), root denied,
  brute-force surface capped (`MaxAuthTries 3`, `MaxStartups 10:30:60`,
  `LoginGraceTime 30`), all forwarding disabled, modern KEX/ciphers/MACs
  only, `LogLevel VERBOSE`.
* **Firewall (UFW)**: default deny incoming + deny routed, **zero public
  inbound ports** (the tunnel dials out), rate-limited SSH from a pinned
  management IP only, optional egress allowlist (`UFW_EGRESS=deny`).
* **Kernel/network**: anti-spoofing (`rp_filter`), no ICMP redirects,
  SYN cookies + RFC1337, martian logging, ASLR full, kernel pointers
  hidden (`kptr_restrict=2`), `dmesg` restricted, ptrace restricted,
  unprivileged BPF off, core dumps off, SUID dumpable off, rare kernel
  protocols (dccp/sctp/rds/tipc + unused filesystems) blacklisted.
* **Updates & logging**: unattended security updates (never auto-reboot —
  the audit flags reboots on your timeline), needrestart auto-restart,
  journald bounded to 250 MB / 2 weeks.
* **Login policy**: pwquality 14+ mixed chars + dictionary check,
  pam_faillock policy (5 fails → 15 min lockout incl. root; activation
  is a deliberate manual `pam-auth-update` step), login.defs aging
  (90/1/7) and `UMASK 027` for new accounts.
* **Fail2Ban**: sshd jail in aggressive mode with exponential recidivist
  bans (up to 4 weeks), bans enforced through UFW on all ports.
* **Auditd forensics**: identity/sudoers/sshd/cron/docker/kernel-module/
  time/mount/delete/perm-change watches, all `ausearch -k` tagged;
  tamper-evident mode (`-e 2`) ready to enable once the set is final.
* **Docker**: `no-new-privileges` daemon-wide, `live-restore`, log
  rotation (10 MB × 3), plus an audit of privileged containers,
  `docker.sock` mounts, and published ports.
* **PostgreSQL**: exposure audit (must be loopback/internal only),
  `pg_hba` trust/ident scan, optional `ALTER SYSTEM` hardening
  (scram-sha-256, connection logging, slow-query log, ssl).
* **Edge (NPM / Cloudflare)**: Cloudflare real-IP restoration (so bans
  and logs see real clients), rate-limit zones + per-host activation,
  security-header and TLS-1.2+ snippets for each proxy host, and a
  named-tunnel config template to replace the Quick Tunnel.
* **Schedules**: daily rkhunter scans, continuous SMART disk warnings,
  weekly posture audit into `/var/log/hardening-audit.log`.
* **Verification**: `audit_hardening.sh` scores all of the above plus UFW,
  fail2ban, crowdsec, auditd, rkhunter, updates, backups, NTP, admin-UI
  exposure and tunnel type. Exit code 1 on any FAIL → wire it into cron.

Raw config templates live in `scripts/hardening/configs/` (install map in
its README). Run order and safety notes are in `scripts/hardening/README.md`.

---

## 3. The gap list — ranked, with concrete steps

### 3.1 P1 — Move from Quick Tunnel to a Named Tunnel + Cloudflare Access

A *Quick* Tunnel (`trycloudflare.com`) is a development convenience: the URL
is random and ephemeral, there is **no persistent identity**, and **Cloudflare
Access cannot be attached to it**. For a production service desk it is the
weakest link in the chain.

1. Create a **Zero Trust named tunnel** (Cloudflare dashboard → Zero Trust →
   Networks → Tunnels) and run it as a service:

   ```bash
   sudo cloudflared service install <TUNNEL-TOKEN>
   sudo systemctl enable --now cloudflared
   ```

2. Route only the hostnames you need (`service-desk.example.com`, maybe the
   proxy manager) to `http://127.0.0.1:<port>`. Nothing else.
3. Put **Cloudflare Access** (SSO + MFA via Google/One-time-pin) in front of:
   * every admin UI (NPM, Portainer, Uptime Kuma),
   * the customer portal can stay public but the **technician/admin** routes
     should be Access-gated if feasible.
4. Now close the firewall completely:

   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing   # or deny + allowlist if you want strict egress
   sudo ufw allow from <YOUR-IP-or-VPN-subnet> to any port 22 proto tcp
   sudo ufw enable
   # NO 80/443 rule needed — the tunnel is an outbound connection.
   ```

   Result: the host has **no listening service reachable from the internet
   at all**. That single change eliminates most scanner/brute-force/botnet
   traffic outright.

### 3.2 P1 — Admin UI lockdown (Portainer, Nginx Proxy Manager, Uptime Kuma)

* **Portainer** (`9443`): bind to `127.0.0.1:9443:9443` (or LAN/VPN only).
  Whoever controls Portainer controls every container and can mount the
  Docker socket = root on the host. Enable Portainer RBAC, create a non-admin
  daily account, and change the admin password to a long random one stored
  in a password manager. Consider **Edge agents** instead of a published port.
* **Nginx Proxy Manager** (admin on `81`): same treatment — only reachable
  through Cloudflare Access or VPN. Disable the default admin account,
  enable 2FA (NPM supports TOTP), and keep NPM updated (it has had auth
  bypass CVEs before; it is internet-adjacent software).
* **Uptime Kuma** (`3001`): behind Access too. It reveals your full internal
  service map — a recon gift if exposed.
* For all three: set `restart: unless-stopped`, keep them on an **internal
  compose network** where possible, and never mount `docker.sock` into
  anything except Portainer.

### 3.3 P1 — Docker socket & container privilege hygiene

* `docker` group membership is **root-equivalent**. Keep the group empty;
  use `sudo docker` or a root-owned management UI.
* `harden_docker.sh` sets `no-new-privileges` daemon-wide. Also apply per
  container: `security_opt: ["no-new-privileges:true"]`, `cap_drop: [ALL]`,
  `pids_limit` — already done for this repo's `compose.yaml`.
* Only one container (Portainer) may mount `/var/run/docker.sock`.
  The audit script flags any other.

### 3.4 P2 — PostgreSQL

* The web container reaches `db` over the internal compose network. Remove
  any `ports: 5432` publishing entirely (or bind `127.0.0.1:5432:5432` for
  local tooling). `harden_postgres.sh` audits this.
* `password_encryption = scram-sha-256`, `POSTGRES_HOST_AUTH_METHOD: scram-sha-256`.
* Rotate the `service_desk` role password away from any default
  (`development-only` etc.) — a long random value in the untracked `.env`.
* Application accounts should be least-privilege; the app does not need
  superuser.

### 3.5 P2 — Backups: off-host, encrypted, restore-tested

A backup on the same box is not a backup — it is what ransomware encrypts
second. Per `docs/operations/BACKUP_AND_RECOVERY.md`, run **both** the JSON
fixture backup and `pg_dump`. Then:

* **3-2-1**: 3 copies, 2 media types, 1 off-site (e.g. an S3-compatible
  bucket with object lock, or at minimum another machine).
* **Encrypt** archives before they leave the host (`age`/`gpg`/`restic`);
  the encryption key must NOT sit on the server.
* **Immutable/offline copy** on a weekly rotation — the copy an attacker
  cannot reach.
* **Restore-test monthly** into a disposable database (`verify_backup` +
  `pg_restore`, per the backup doc). A backup you have never restored is a
  hope, not a plan.
* Backup script failure must **alert** (cron mail → real mailbox, or a
  dead-man's-switch such as healthchecks.io ping after each successful run).

### 3.6 P2 — Host-level (done by the kit)

SSH + kernel + Docker + Postgres hardening as in §2. Reboot once for the
modprobe blacklist and limits to fully apply, then re-run the audit.

### 3.7 P3 — Detection & alerting (you have collectors — add *alerting*)

* Fail2Ban/CrowdSec/auditd only help if a human hears about it. Wire
  notifications: CrowdSec scenarios → Slack/email webhook; fail2ban `action`
  → email; auditd `audisp` → syslog → Uptime Kuma or a notification channel.
* Alert on: repeated SSH auth failures, new sudoers/UID-0 change,
  `docker group` membership change, auditd/rkhunter stops, backup failure,
  disk SMART degradation, reboot-required > 3 days.
* Ship logs off-box (even a simple daily `journalctl --since -24h` upload to
  the same immutable storage). If an attacker gets root, the first thing they
  do is clean local logs.

### 3.8 P3 — Application & proxy edge (this repo)

* Django's `manage.py check --deploy` is already enforced in CI and the
  production settings enforce `DEBUG=false`, secure cookies, HSTS ramp plan
  (`docs/operations/PRODUCTION_DEPLOYMENT.md`).
* At NPM: enable HSTS **only** per the ramp plan, add rate limiting on
  `/accounts/login/` and API routes, add security headers (CSP, X-Content-
  Type-Options, Referrer-Policy — the app sets most; NPM should mirror),
  and use Cloudflare "Full (strict)" SSL.
* Keep the app image immutable (built in CI), keep `requirements.txt`
  pinned (it is), and schedule a dependency-audit step when a scanner is
  approved (`pip-audit`/`piprot` — noted in `security-scan.yml` as a
  deliberate future addition).

### 3.9 P4 — Operational discipline (the boring stuff that actually works)

* **One admin machine** for SSH + admin UIs, itself patched, with FIDO2/passkey
  where possible.
* **Password manager** for every credential; never reuse; rotate on staff change.
* **Change log**: date, what changed, why, rollback. Keep it in this repo
  (`docs/operations/`).
* **Monthly**: re-run `audit_hardening.sh`, review WARNs, test a restore,
  review CrowdSec/Fail2Ban bans for false positives, check pending reboots.
* **Quarterly**: rotate credentials, review who still needs access, review
  UFW rules, simulate a restore *from the off-host copy only*.

---

## 4. Verification — the definition of done

The host is "hardened" when **all** of these are true simultaneously:

1. `sudo scripts/hardening/audit_hardening.sh` exits **0** with every WARN
   either fixed or documented as a conscious decision in this file.
2. `nmap -Pn <your-public-ip>` from outside shows **no open ports at all**
   (SSH is reachable only from your IP/VPN; everything else via the tunnel).
3. A password-auth SSH attempt fails; key auth works; root login fails.
4. Portainer/NPM/Uptime Kuma are unreachable from the internet but work
   through Cloudflare Access (with MFA).
5. `docker ps` shows no privileged containers and only Portainer holding
   `docker.sock`.
6. PostgreSQL is unreachable from the host's public interface.
7. The last backup is off-host, encrypted, and the last restore test is
   dated this month.
8. Killing `cloudflared` triggers an Uptime Kuma alert within one minute
   (proves the alerting path works).

## 5. If you are breached anyway (quick card)

1. **Do not power off** (RAM/keys vanish) — isolate: `iptables -P INPUT DROP`
   or pull the network cable, keep the tunnel down.
2. From a **clean machine**: rotate Cloudflare credentials, DB passwords,
   SSH keys, all API tokens.
3. Preserve evidence: snapshot disks, copy `/var/log`, audit logs, `docker ps`,
   `ss -antp`.
4. Rebuild the host from scratch (never "clean" a rooted box) and restore
   from the **verified, off-host** backup.
5. Post-mortem in `docs/engineering/INCIDENT_LOG.md` — what the audit script
   would have caught, and add that check.

---

*Related: `docs/operations/PRODUCTION_DEPLOYMENT.md` (release process),
`docs/operations/BACKUP_AND_RECOVERY.md` (backup formats & restore checks),
`scripts/hardening/README.md` (the executable kit).*
