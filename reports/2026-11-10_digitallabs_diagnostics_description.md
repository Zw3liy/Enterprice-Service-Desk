# Description Prompt — `digitallabs` Security Diagnostics (2026-11-10)

> Copy-paste-ready description of the raw diagnostics output (cscli metrics,
> fail2ban, auditctl/ausearch/aureport, docker ps, ss, and a Lynis 3.1.6 audit).
> Suitable as a status brief, an input prompt for further analysis, or an
> incident-ticket body.

---

**System under review:** `digitallabs` — Ubuntu 26.10 (kernel 7.3.0, x86_64),
self-hosted Enterprise Service Desk platform. Workloads: Dockerized Nginx
Proxy Manager (80/443/81), Portainer CE (9443), Uptime Kuma (3001), and a
custom `cape-painting` app (8081); native PostgreSQL 18 (loopback-only);
Cloudflare tunnel (`cloudflared`), Tailscale, Postfix (local relay for
alerts), CrowdSec + Fail2Ban + auditd as the security stack.

**Commands captured in the output:** `cscli metrics`, `cscli decisions list`,
`fail2ban-client status [sshd]`, `auditctl -l`, `ausearch -ts today`,
`aureport -au`, `docker ps`, `ss -tulpn`, `apt install lynis`,
`lynis audit system`.

## 1. Threat intelligence & IPS (CrowdSec) — working, community-fed
CrowdSec is healthy: local API up (127.0.0.1:8080), machine registered,
`FirewallBouncer` polling the decisions stream normally (~3,500 fetches) and
actively writing nftables sets. Since install it has processed **~14,991
block decisions, all from the CrowdSec Community Blocklist (CAPI)** —
http:bruteforce 6,802 · generic:scan 3,067 · http:dos 1,770 ·
ssh:bruteforce 1,229 · http:scan 1,141 · smtp:spam 471 · ssh:exploit 256 ·
http:crawl 179 · vm-management:exploit 73 · http:exploit 3. Zero decisions
are active right now (old bans have expired).

**Critical gap — local detection is effectively blind:** the sshd parser
shows 256 hits with **256 unparsed (0 matched)** and `auth.log` shows 342
lines read but only 2 parsed. Every ssh-related ban above is CAPI-sourced,
not locally detected; the only local scenarios instantiated
(`ssh-time-based-bf`, `ssh-time-based-bf_user-enum`) have never overflowed.
Likely cause: the host runs the new OpenSSH session-split daemon
(`sshd-session`, confirmed in audit logs) whose log format the installed hub
parsers don't fully match. There is also **no HTTP log acquisition** (NPM
logs stay inside its container), so local web brute-force detection is
absent too.

## 2. Fail2Ban — armed but silent
One jail (`sshd`, journald backend, matching `_SYSTEMD_UNIT=ssh.service +
_COMM=sshd`): 0 currently failed, 0 total failed, 0 ever banned. Either the
host is genuinely quiet behind CrowdSec's wall — or the filter is also
mismatched against the new sshd log format; verify with `fail2ban-regex`.

## 3. Auditd — running with an **empty ruleset** (standout failure)
`auditctl -l` returns "No rules". `ausearch -ts today` shows only default
kernel/systemd bookkeeping (SERVICE_START/STOP, cron PAM sessions, Docker
iptables churn, CrowdSec bouncer nft set updates, BPF load/unload noise) —
**no identity/sudoers/ssh/docker watches at all**. Lynis independently flags
this (`ACCT-9630: audit daemon enabled with an empty ruleset`). Notable
events in the default stream: one **failed sudo authentication from a cron
job** (user `zweth`, 2026-11-10 02:00:01, `res=failed`) — a scheduled task
nightly attempting passwordless sudo and failing; and repeated
`fwupd-refresh` failures. `aureport -au` confirms 5 auth events for the day
(4 successes incl. a `postgres` su session, 1 failure = that cron sudo).
Also worth verifying: the sudo binary resolves to the unusual path
`/usr/lib/cargo/bin/sudo`.

## 4. Network & container exposure — mixed
Good: PostgreSQL 18 bound to **127.0.0.1:5432 only**; Portainer bound to
**127.0.0.1:9443** (matches the hardened ops-stack guidance); CrowdSec LAPI,
bouncer, cloudflared metrics, and Postfix (25) all loopback-only; SSH is
key-authenticated; Tailscale provides an out-of-band management plane.
Bad: **Docker publishes four services on 0.0.0.0** — NPM (80/443 **and the
81 admin UI**), Uptime Kuma (3001), and `cape-painting` (8081). Published
Docker ports bypass UFW via the DOCKER chain, so these are internet-reachable
unless stopped upstream. sshd also listens on 0.0.0.0:22 (defensible with
key-only auth + CrowdSec/Fail2Ban, but a management-IP/Tailscale allowlist
would be tighter).

## 5. Lynis 3.1.6 audit — hardening index **63/100** (273 tests)
5 warnings: (1) **vulnerable packages pending upgrade** (PKGS-7392 —
unpatched CVEs live right now); (2) Postfix SMTP banner discloses
OS/software (MAIL-8818); (3–5) PostgreSQL 18 config files world-readable —
`/etc/postgresql/18/main/{postgresql,pg_ctl,start}.conf` → `chmod 600`
(DBS-1828). 37 suggestions, the highest-value being: empty audit ruleset
(ACCT-9630), GRUB boot password + UEFI disabled, **disk unencrypted**
(`/` on `/dev/sdb3`), no file-integrity tool (AIDE), weak `/etc/issue{,.net}`
banners, no remote log shipping (LOGG-2154), USB-storage not disabled,
unresolved dccp/sctp/rds/tipc kernel protocols, PAM password-strength &
hashing-rounds, password aging & umask in login.defs, and a batch of sysctl
values below profile (kptr_restrict, suid_dumpable, sysrq,
unprivileged_bpf_disabled, bpf_jit_harden, protected_fifos,
rp_filter/log_martians/send_redirects — note `net.ipv4.ip_forward` differs
by design because Docker requires it). AppArmor is enabled but 77 processes
run unconfined.

## 6. Verdict & priority actions
Posture is **better than average but not yet hardened**: real-time community
blocking works, the database and Portainer are correctly loopback-bound, and
SSH is key-only — but the host is running with **zero audit rules, blind
local intrusion detection (parser mismatch), four internet-facing Docker
ports (including the NPM admin UI), and known-vulnerable packages**.

1. **Load the audit ruleset** — `scripts/hardening/harden_auditd.sh`
   (identity/sudoers/ssh/docker/kernel watches; enables `ausearch -k`).
2. **Fix CrowdSec parsing** — `cscli hub update && cscli hub upgrade`, then
   validate the sshd filter against the new `sshd-session` log lines
   (`fail2ban-regex` too); pipe NPM logs into CrowdSec acquis for local HTTP
   detection.
3. **Close the 0.0.0.0 Docker ports** — rebind NPM:81, Uptime Kuma:3001 and
   cape-painting:8081 to 127.0.0.1 (pattern: `configs/compose/ops-stack.hardened.yml`
   + `docker-compose.production.yml`); keep only the tunnel path public.
4. **Patch now** — `apt update && apt upgrade` (PKGS-7392); `chmod 600`
   the three PostgreSQL conf files; blank the Postfix banner.
5. **Investigate the 02:00 failed cron sudo** (which user crontab, why sudo)
   and verify the `cargo`-path sudo binary.
6. **Lynis follow-ups** — GRUB password, AIDE, legal banners, remote log
   shipping, `harden_kernel.sh` for the sysctl deltas, then re-run
   `sudo scripts/hardening/audit_hardening.sh` (expect it to score these
   same findings) and `lynis audit system` to track the index upward.
