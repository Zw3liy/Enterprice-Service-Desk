# Enterprise Service Desk — Full Detailed Description of Diagnostics Output

**Host:** `digitallabs` (zweth@) · **Session window:** 2026-11-10, 05:40–06:20 UTC · **Companion to:** `2026-11-10_digitallabs_diagnostics_description.md` (the earlier brief)
**Scope of this capture:** a guided remediation attempt on the live server — auditd rule loading, CrowdSec refresh and reconfiguration, Fail2Ban verification against real logs, listener/exposure re-check, chasing the 02:00 failed sudo, and identification of the sudo binary. All timestamps are UTC (server runs UTC).

**What changed vs. the earlier brief:** the 02:00 mystery is SOLVED (item 6 — the nightly Postgres backup is silently failing), the auditd gap is confirmed root-caused (the repo with our hardening kit is **not deployed on the server**), the CrowdSec hub is proven current (so the parser problem is not staleness), and the sudo oddity is most likely explained (sudo-rs via alternatives).

---

## 1. auditd — healthy daemon, empty ruleset, and the kit never arrived

### 1.1 Status decode (`auditctl -s`)

| Setting | Value | Meaning |
|---|---|---|
| enabled | 1 | kernel auditing is on |
| failure | 1 | printk mode — daemon keeps running if a write fails (vs. 2 = panic) |
| pid | 36673 | auditd running |
| rate_limit | 0 | no throttling |
| backlog_limit | 8192 | kernel queue size (default) |
| lost | 0 | **no events lost** — healthy |
| backlog / backlog_wait_time | 0 / 60000 ms | queue empty, default wait |
| loginuid_immutable | 0 unlocked | immutable login UIDs not enforced (by design in our kit — the `-e 2` line is intentionally commented) |

Verdict: the daemon is fine. The problem is purely an empty ruleset.

### 1.2 The empty-ruleset proof chain

- `auditctl -l` → **"No rules"** — three separate times: before the reload, after `augenrules --load` + `systemctl restart auditd`, and at the end.
- `sudo augenrules --load` → **`/usr/sbin/augenrules: No change`** — there is nothing in `/etc/audit/rules.d/` to compile, so the compiled `/etc/audit/audit.rules` is unchanged.
- The restart cycle is visible in the audit log: `DAEMON_END (op=terminate)` → `DAEMON_START (op=start ver=4.1.2 format=enriched kernel=7.3.0-10-generic)` → `SERVICE_START/STOP unit=audit-rules` (the oneshot that runs augenrules). Event numbering resets across the restart (…2642 → 7099 → 5396…), which is normal, not tampering.
- What `auditctl -R /etc/audit/audit.rules` actually loaded — decoded from the PROCTITLE hex (`2F7362696E2F617564697463746C002D52002F6574632F61756469742F61756469742E72756C6573` = `/sbin/auditctl -R /etc/audit/audit.rules`) — was only three CONFIG_CHANGE events:
  - `op=set audit_backlog_limit=8192 old=8192`
  - `op=set audit_failure=1 old=1`
  - `op=set audit_backlog_wait_time=60000 old=60000`

  In every case **old == new**: the file contains nothing but the distro default tuning lines (`-D`, `-b 8192`, `-f 1` …). No watch rules, no key rules.
- End-to-end proof that nothing is being watched: `sudo touch /etc/test-audit-file` produced **zero records** (the only SYSCALL records in the window are auditctl's own `sendto` calls), and `ausearch -k identity` / `-k ssh` / `-k docker` all return **`<no matches>`** — those keys exist only in our `90-enterprise-service-desk.rules`, which is not on the box.

### 1.3 Why the rules never loaded — the kit is not deployed

```
cd /srv/projects/enterprise-service-desk        → No such file or directory
sudo scripts/hardening/harden_auditd.sh         → sudo: command not found
```

The repository (with `scripts/hardening/`) has **not been cloned to this server**. The auth.log shows `/srv/projects` was only created on Nov 09 13:13 and currently holds `cape-painting`, not the Enterprise Service Desk repo. Everything in the earlier brief about "run `harden_auditd.sh`" presupposed the repo on the host — that step was never done.

**Fix (either):**

```bash
# A. deploy the kit
sudo apt install -y git && mkdir -p /srv/projects && cd /srv/projects
git clone https://github.com/Zw3liy/Enterprice-Service-Desk.git
cd Enterprice-Service-Desk
sudo scripts/hardening/harden_auditd.sh          # installs 90-enterprise-service-desk.rules + augenrules --load

# B. or just the rules, minimal footprint
sudo install -m 640 scripts/hardening/configs/auditd/90-enterprise-service-desk.rules /etc/audit/rules.d/
sudo augenrules --load
```

**Verify:** `sudo auditctl -l` lists the rules; repeat the `touch /etc/test-audit-file` test and it appears in `ausearch -ts recent`.

### 1.4 Side notes

- auditd version 4.1.2, `format=enriched`.
- The daemon reports **kernel 7.3.0-10-generic**, while the earlier Lynis capture listed 7.3.0-19 — run `uname -r`; you may be booting an older kernel than the one installed (check for a pending reboot / GRUB default).
- `systemctl restart auditd` worked here (Ubuntu allows it); `service auditd restart` remains the portable form.

---

## 2. CrowdSec — engine healthy, parsers blind, hub already current

### 2.1 Hub refresh is a no-op

`cscli hub update` → "Nothing to do, the hub index is up to date." · `cscli hub upgrade` → only "check & update data files". So the parser problems below are **not** fixed by updating — the shipped versions are already the latest.

### 2.2 Installed parsers (12, all enabled)

auditd-logs 0.9 · dateparse-enrich 0.2 · geoip-enrich 0.5 · http-logs 1.4 · nginx-logs 2.0 · postfix-logs 1.0 · postscreen-logs 0.3 · public-dns-allowlist 0.1 · sshd-logs 3.1 · sshd-success-logs 0.2 · syslog-logs 1.1 · whitelists 0.3.
The nginx/postfix/postscreen/sshd-success parsers show **zero traffic** — nothing acquires the logs they read.

### 2.3 Acquisition metrics — what's parsing and what isn't

Before the acquis edit:

| Source | Read | Parsed | Unparsed |
|---|---|---|---|
| file:/var/log/audit/audit.log | 20→24 | 3 | 17→21 |
| file:/var/log/auth.log | 10→13 | **0** | 10→13 |
| file:/var/log/syslog | 6→8 | **0** | 6→8 |

After `nano /etc/crowdsec/acquis.yaml` + restart (counters reset): audit.log 3 read / 0 parsed, auth.log 2 read / 0 parsed, and **`/var/log/syslog` disappeared from acquisition entirely** — keep it, cron lives there.

Root causes (all confirmed by the data):

1. **auth.log/syslog use ISO-8601 timestamps** with fractional seconds + offset (`2026-11-10T02:00:01.085841+00:00`). `crowdsecurity/syslog-logs` 1.1 expects RFC3164/5424 — every line falls through unparsed. This is why auth.log shows **0 parsed**.
2. **sshd logs are in the new OpenSSH `sshd-session[pid]:` format**, which `sshd-logs` 3.1 does not recognize (earlier capture: 256 hits / **256 unparsed**). The hub is current, so this needs a parser-side workaround until upstream catches up.
3. **NPM's logs are not acquired at all.** nginx-logs/http-logs are installed but idle; the NPM access/auth logs under `/srv/docker/npm/data/logs/` are never read → no local HTTP detection whatsoever.
4. Only 3 of ~24 audit.log lines parse (the SYSCALL/PROCTITLE shapes); PAM/USER_*/SERVICE_* record types fall through `auditd-logs` 0.9 — cosmetic, but it's why the unparsed count is high.

Note on counters: CrowdSec tails files from the restart point — the 342-line read in the earlier capture vs. 10–13 lines now is tail position after restart, not log loss.

### 2.4 Decisions & plumbing

All ~14,991 decisions remain **CAPI-only** (http:bruteforce 6802 · generic:scan 3067 · http:dos 1770 · ssh:bruteforce 1229 · http:scan 1141 · smtp:spam 471 · ssh:exploit 256 · http:crawl 179 · vm-management:exploit 73 · http:exploit 3) — **zero locally generated bans**. Local API (127.0.0.1:8080) and the firewall bouncer (`FirewallBouncer-IP2cGm…`, polling `/v1/decisions/stream`) are healthy. Whitelists account for 3 private-IP + 3 public-DNS hits.

`cscli explain --file /var/log/auth.log` failed — it needs a type flag. Correct form:

```bash
sudo cscli explain --file /var/log/auth.log --type syslog
```

**Fix list:** add acquis entries for NPM's logs (`/srv/docker/npm/data/logs/*.log`, nginx-logs parser), restore the syslog source, test one real `sshd-session` line with `cscli explain --type syslog`, and if it still misses, add a local parser override for the `sshd-session` prefix.

---

## 3. Fail2Ban — armed, but blind

- Jail `sshd`: currently failed 0, total failed 0, banned 0 — **ever**. Journal match: `_SYSTEMD_UNIT=ssh.service + _COMM=sshd`.
- **Smoking gun:** connection handling logs come from `sshd-session` (comm=`sshd-session`), but the jail matches `_COMM=sshd` — so it only ever sees the master daemon's lines (listen notices, pre-auth timeouts) and never the session/failure lines. Until this is fixed, Fail2Ban adds zero protection beyond CrowdSec's CAPI list.
- **Fix:** journalmatch `_SYSTEMD_UNIT=ssh.service` alone (or add `_COMM=sshd-session`), in `/etc/fail2ban/jail.local` / `jail.d/99-tos-ssh.local` (their custom files, created Nov 08–09).
- The `fail2ban-regex` run is **inconclusive, not exonerating**: output shows `single line : /dev/fd/63` and "Lines: 1 lines … 1 missed" — only one line ever reached the filter, because the process-substitution fd didn't survive `sudo`. Re-test properly:

```bash
journalctl -u ssh --since "24 hours ago" | sudo fail2ban-regex - /etc/fail2ban/filter.d/sshd.conf
sudo fail2ban-regex "Failed password for invalid user admin from 203.0.113.5 port 52344 ssh2" /etc/fail2ban/filter.d/sshd.conf
```

- Encouraging detail: the shipped filter's **prefregex already accepts `sshd(?:-session)?`**, so once the jail can see the lines, the stock filter should classify failures correctly.

---

## 4. SSH journal (Nov 08–10)

- Every interactive login is **`Accepted publickey`** — key-only auth is working; no password failures in the window.
- Internet noise on the open port: two `Timeout before authentication for …` (probes stalling pre-auth) and `Connection closed by authenticating user …` lines — expected with sshd on 0.0.0.0:22.
- Cosmetic: repeated `lastlog_openseek: Could not seek…` warnings from `sshd-session` (known OpenSSH 9.8+ lastlog quirk; harmless).
- sshd master (pid 5203) has been up since the Nov 08 14:46 SIGHUP; listens 0.0.0.0:22 + [::]:22. UFW now carries a **global `allow 22/tcp`** (replacing the earlier tailscale0-scoped rule). Consider scoping SSH back to `tailscale0` (or Cloudflare Access); key-only auth plus a *working* Fail2Ban is the residual control.

---

## 5. Network exposure (`ss -tulpn`) — and why the `ufw deny` rules don't help

**Loopback-only (good):** PostgreSQL 5432 · postfix 25 (+ ::1) · Portainer 9443 · CrowdSec LAPI 8080 + metrics 6060 · firewall-bouncer 60601 · cloudflared metrics 20242 · chronyd 323 · resolved 53.

**Wildcard 0.0.0.0 (+ [::]) via docker-proxy:** **81 (NPM admin), 3001 (Uptime Kuma), 8081 (cape-painting)** — plus 80/443 (NPM, expected). **sshd 22** on all interfaces. tailscaled UDP 41641 (WireGuard — by design, authenticated peers only). Two tailscale TCP listeners bound to the tailnet addresses only (100.111.99.36:35258, fd7a…:55056) — tailnet-visible only.

**Critical caveat:** the `ufw deny 9000/9443/3001/8081` rules added on Nov 09 (twice — 19:53 and 19:57, creating duplicates) **do not block Docker-published ports**. Docker's DNAT happens in PREROUTING before UFW's INPUT rules; anything published on 0.0.0.0 remains reachable from the internet regardless of UFW deny rules. **81, 3001 and 8081 are internet-facing right now**, despite what `ufw status` suggests. The effective fix is binding them to `127.0.0.1` (the exact pattern in `scripts/hardening/configs/compose/ops-stack.hardened.yml`), or DOCKER-USER/uw-docker rules; and regardless, these admin UIs need MFA behind Cloudflare Access. Also decide whether 80/443 should be world-published at all (direct inbound path alongside the tunnel) or restricted to Cloudflare's IP ranges / loopback once the tunnel carries everything.

---

## 6. The 02:00 mystery is SOLVED — nightly Postgres backups are silently failing

The full chain is in the logs, aligned to the second:

1. syslog: `CRON[241649]: (zweth) CMD (/srv/backups/postgres/backup-postgres.sh >/dev/null 2>&1)` — 02:00:01.
2. auth.log: `sudo: pam_unix(sudo:auth): conversation failed` and `auth could not identify password for [zweth]` — 02:00:01.
3. audit: `USER_AUTH … grantors=? acct="zweth" exe="…/sudo" terminal=? res=failed` — 02:00:01.

**Diagnosis:** the backup script invokes `sudo` non-interactively; cron has no TTY, PAM cannot prompt, authentication fails immediately (note `grantors=?` — auth never reached a grantor). The job then dies, and `>/dev/null 2>&1` hides the failure completely. So the **Postgres backup has been failing every night since it was scheduled**. The 02:15 `backup-docker.sh` job likely succeeds (zweth is in the `docker` group and may not need sudo) — verify files exist under `/srv/backups/`.

**Fix:** move the jobs to root's crontab (or systemd timers), or add a tight `/etc/sudoers.d/backups` `NOPASSWD` rule for exactly the commands the script needs; stop discarding output — log to `/var/log/backups.log`. **Verify tomorrow that fresh dumps appear in `/srv/backups/postgres/`.** This was flagged as "investigate the failed cron sudo" in the earlier brief; the intent is benign (your own backup job) but the effect is critical (no working database backup). Also relevant: `rclone` was installed at 05:47 today — presumably the start of off-host backup copies; it is not configured yet.

---

## 7. sudo provenance — unusual path, almost certainly sudo-rs

Facts from the tail of the capture:

- `which sudo` → `/usr/bin/sudo` (hashed), which is a symlink: `/usr/bin/sudo → /etc/alternatives/sudo` (created Sep 22) — i.e. managed by `update-alternatives`.
- `dpkg -S /usr/bin/sudo` → "no path found" — **normal** for an alternatives symlink (the symlink itself isn't owned by a package).
- Running `/usr/lib/cargo/bin/sudo` directly prints `expected one of these actions: --help, --version, …` followed by the classic `usage: sudo [-ABbknS] …` lines. The first line is **not** classic-C-sudo error style; it matches a Rust CLI parser. `/usr/lib/cargo/bin` is Rust-toolchain layout.
- audit records consistently attribute sudo to `exe="/usr/lib/cargo/bin/sudo"` — expected while the alternative points there.

**Reading:** this is the signature of **sudo-rs** (the Rust reimplementation of sudo, the default on newer Ubuntu releases), installed via the distro's cargo packaging with an alternatives symlink — almost certainly benign packaging, **not** a plant. But verify rather than assume:

```bash
readlink -f /usr/bin/sudo
dpkg -S "$(readlink -f /usr/bin/sudo)"
update-alternatives --display sudo
sudo --version
```

If `dpkg -S` **does** own the real binary → question closed. If it does not, treat it as an incident (reinstall the sudo package, compare hashes, run rkhunter/AIDE).

---

## 8. Operational timeline from auth.log (Nov 07–10)

Condensed build history of the server: netplan configuration → Tailscale (installed via `sh /tmp/tailscale.sh` — note: scripts-from-/tmp) → OpenSSH with drop-in `00-tos-hardening.conf` (validated with `sshd -t` before reload — good practice) → Fail2Ban + `99-tos-ssh.local` + `jail.local` → Docker CE with LVM volume `tos-data` (200 G), data-root migrated to `/srv/tos-data/docker` via rsync + `daemon.json` + containerd root + systemd drop-ins (validated before restart — good) → cloudflared from Cloudflare's apt repo → NPM stack at `/srv/docker/npm` → mediflow migration staging (SHA256SUMS-verified `database.dump` + `private_documents.tar.gz`) and company-hp staging → tooling (`gh`, node/npm, tmux, fzf, **rclone**, **lynis**) → security stack installs (ufw, fail2ban, auditd, rkhunter with `--propupd`, unattended-upgrades, CrowdSec + nginx/sshd/http-cve/linux collections + firewall-bouncer) → `pg_dumpall` runs → rkhunter check → this session.

Small items worth a second look: `apt install ironseed` during the read-only `/dev/sda1` inspection (`/mnt/mukango-inspection`) — confirm that was intended; one mistyped sudo password (Nov 08 14:57 — benign); an `apt-get updatesudo apt-get update` paste typo (harmless); and **zweth is in the `docker` group** (root-equivalent — consider limiting it to break-glass use).

---

## 9. Verdict & ranked actions (with verification)

The perimeter remains strong (key-only SSH, tunnel edge, CAPI blocklist, loopback DB/mail), but this capture confirms all three local detection/backup layers are currently inert: **auditd has no rules, Fail2Ban sees nothing, and the nightly Postgres backup fails silently.**

| # | Action | Verify |
|---|---|---|
| 1 | **Restore the 02:00 backup** (root crontab / sudoers NOPASSWD / timers; log output) | fresh dump in `/srv/backups/postgres/` tomorrow |
| 2 | **Deploy the repo and load auditd rules** (`harden_auditd.sh`) | `auditctl -l` shows rules; touch test appears in `ausearch` |
| 3 | **Fix Fail2Ban journalmatch** (drop/extend `_COMM`), re-test with piped `fail2ban-regex` | synthetic failure produces a ban |
| 4 | **Rebind 81/3001/8081 to 127.0.0.1** (UFW deny is bypassed by Docker) | `ss -tulpn` + external port probe |
| 5 | **CrowdSec:** NPM log acquisitions, restore syslog source, `cscli explain --type` checks, sshd-session override | lines parsed > 0; local alerts appear |
| 6 | **Verify sudo provenance** (item 7 commands) | `dpkg` owns the real binary |
| 7 | Housekeeping: `uname -r` vs installed kernel (reboot if stale), dedupe UFW rules, scope SSH to tailscale0, docker-group hygiene, configure rclone for off-host copies | — |
