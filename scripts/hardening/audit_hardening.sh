#!/usr/bin/env bash
# -------------------------------------------------------------------
# audit_hardening.sh — read-only security posture audit.
#
# Verifies every control this host claims to have (UFW, Fail2Ban,
# CrowdSec, Auditd, RKHunter, SMART, auto-updates, SSH, Docker,
# PostgreSQL, backups, NTP, ...) plus the controls installed by the
# rest of this kit. Prints [PASS]/[WARN]/[FAIL] per check and a
# summary score. Makes ZERO changes — safe to run any time, from cron,
# or after every config change.
#
# Usage:
#   sudo ./audit_hardening.sh              # full audit
#   sudo ./audit_hardening.sh --quick      # skip slow checks (rkhunter/smart)
#
# Exit codes:  0 = no FAILs (warnings allowed)   1 = at least one FAIL
# -------------------------------------------------------------------

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh" 2>/dev/null || { echo "lib.sh missing"; exit 1; }

QUICK=0
[[ "${1:-}" == "--quick" ]] && QUICK=1

PASS=0; WARN=0; FAIL=0; SKIP=0
# NOTE: these intentionally do NOT delegate to lib.sh's warn/fail/skip
# (that would be infinite recursion) — they print the same format and
# count results. Also re-disable -e: an audit must never abort because
# one probe returned non-zero.
set +e
pass() { printf '    [PASS] %s\n' "$*"; PASS=$((PASS+1)); }
warn() { printf '    [WARN] %s\n' "$*"; WARN=$((WARN+1)); }
fail() { printf '    [FAIL] %s\n' "$*"; FAIL=$((FAIL+1)); }
skip() { printf '    [SKIP] %s\n' "$*"; SKIP=$((SKIP+1)); }

section() { printf '\n\033[1m--- %s ---\033[0m\n' "$*"; }

echo "=============================================================="
echo " Server Hardening Audit — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Host: $(hostname -f 2>/dev/null || hostname)   Kernel: $(uname -r)"
echo "=============================================================="

# -----------------------------------------------------------------
section "1. SSH"
# -----------------------------------------------------------------
sshd_cfg() { sshd -T 2>/dev/null; }
if command_exists sshd; then
    T="$(sshd_cfg)"
    check_ssh() {
        local key="$1" want="$2" got
        got="$(awk -v k="${key}" 'tolower($1)==k {print tolower($2); exit}' <<< "${T}")"
        if [[ "${got}" == "${want}" ]]; then pass "sshd ${key} ${got}"
        elif [[ -z "${got}" ]]; then warn "sshd ${key} not set (expected ${want})"
        else fail "sshd ${key} = ${got} (expected ${want})"; fi
    }
    check_ssh permitrootlogin no
    check_ssh passwordauthentication no
    check_ssh pubkeyauthentication yes
    check_ssh permitemptypasswords no
    check_ssh kbdinteractiveauthentication no
    check_ssh x11forwarding no
    check_ssh allowtcpforwarding no
    check_ssh loglevel verbose
    mat="$(awk 'tolower($1)=="maxauthtries" {print $2; exit}' <<< "${T}")"
    if [[ -n "${mat}" && "${mat}" -le 5 ]]; then
        pass "sshd MaxAuthTries ${mat} (<= 5)"
    else
        fail "sshd MaxAuthTries ${mat:-unset} (expected <= 5)"
    fi
    grep -q 'AuthenticationMethods publickey' <<< "${T}" \
        && pass "sshd AuthenticationMethods publickey enforced" \
        || warn "sshd AuthenticationMethods not restricted to publickey"
    nkeys="$(find /root/.ssh /home/*/.ssh -name authorized_keys -type f 2>/dev/null | wc -l)"
    [[ "${nkeys}" -gt 0 ]] && pass "authorized_keys present for ${nkeys} account(s)" \
        || warn "no authorized_keys found — how do you log in?"
else
    skip "sshd not installed on this host."
fi

# -----------------------------------------------------------------
section "2. Accounts & authentication"
# -----------------------------------------------------------------
uid0="$(awk -F: '$3==0 && $1!="root" {print $1}' /etc/passwd)"
[[ -z "${uid0}" ]] && pass "no extra UID-0 accounts" || fail "extra UID-0 accounts: ${uid0}"

emptypw="$(awk -F: '($2=="" || $2=="!") {next} length($2)<2 {print $1}' /etc/shadow 2>/dev/null)"
[[ -z "${emptypw}" ]] && pass "no accounts with empty passwords" || fail "empty-password accounts: ${emptypw}"

if [[ -f /etc/ssh/sshd_config ]] || ls /etc/ssh/sshd_config.d/*.conf >/dev/null 2>&1; then
    grep -rqsE '^\s*PermitRootLogin\s+yes' /etc/ssh/sshd_config /etc/ssh/sshd_config.d/ 2>/dev/null \
        && fail "PermitRootLogin yes found in sshd config files" \
        || pass "no PermitRootLogin yes anywhere in sshd config"
fi

for f in /etc/passwd /etc/shadow /etc/group /etc/gshadow /etc/sudoers /etc/ssh/sshd_config; do
    [[ -e "${f}" ]] || continue
    perms="$(stat -c '%a' "${f}")"
    case "${f}" in
        /etc/passwd|/etc/group) want="644" ;;
        /etc/sudoers) want="440" ;;
        *) want="640"; [[ "${f}" == /etc/ssh/sshd_config ]] && want="600" ;;
    esac
    if [[ "${perms}" == "${want}" ]] || [[ "${f}" == /etc/ssh/sshd_config && "${perms}" == "644" ]]; then
        pass "${f} perms ${perms}"
    else
        warn "${f} perms ${perms} (expected ${want})"
    fi
done

# -----------------------------------------------------------------
section "3. Firewall (UFW / nftables)"
# -----------------------------------------------------------------
if command_exists ufw; then
    if ufw status 2>/dev/null | grep -q 'Status: active'; then
        pass "UFW active"
        ufw status verbose 2>/dev/null | grep -q 'Default: deny (incoming)' \
            && pass "UFW default deny incoming" \
            || fail "UFW incoming default is not deny"
        ufw status verbose 2>/dev/null | grep -q 'Default: deny (outgoing)' \
            && pass "UFW default deny outgoing" \
            || warn "UFW outgoing default is allow (acceptable; deny is stricter)"
        ufw status 2>/dev/null | grep -E '^\s*(80|443|5432|8000|9443|3000|81|8081|3001)\b' | grep -q 'Anywhere' \
            && warn "UFW allows a service port to Anywhere — verify it is intended:"
        ufw status numbered 2>/dev/null | sed 's/^/        | /' | head -30
    else
        fail "UFW installed but NOT active"
    fi
elif command_exists nft; then
    nft list ruleset 2>/dev/null | grep -q . && pass "nftables ruleset present" || fail "nftables has no rules"
else
    fail "no firewall (ufw/nftables) detected"
fi

# -----------------------------------------------------------------
section "4. Intrusion prevention (Fail2Ban / CrowdSec)"
# -----------------------------------------------------------------
if systemctl list-unit-files fail2ban.service >/dev/null 2>&1; then
    systemctl is-active --quiet fail2ban && pass "fail2ban running" || fail "fail2ban not running"
    if command_exists fail2ban-client; then
        jails="$(fail2ban-client status 2>/dev/null | sed -n 's/^Jail list:[[:space:]]*//p' | tr -d ' ')"
        [[ -n "${jails}" ]] && pass "fail2ban jails: ${jails}" || warn "fail2ban has no active jails"
        [[ "${jails}" == *sshd* || "${jails}" == *ssh* ]] && pass "sshd jail active" || warn "no sshd jail in fail2ban"
    fi
else
    warn "fail2ban not installed (CrowdSec alone is acceptable if bouncers are active)"
fi

if command_exists cscli; then
    systemctl is-active --quiet crowdsec && pass "crowdsec running" || fail "crowdsec not running"
    bouncers="$(cscli bouncers list 2>/dev/null | grep -c '✔\|enabled' || true)"
    [[ "${bouncers}" -gt 0 ]] && pass "crowdsec bouncer(s) registered" || fail "no crowdsec bouncers — decisions are not enforced"
    decisions="$(cscli decisions list 2>/dev/null | grep -cE 'ban|captcha|throttle' || true)"
    log "        (currently ${decisions} active crowdsec decisions)"
else
    warn "crowdsec not installed on this host"
fi

# -----------------------------------------------------------------
section "5. Audit & integrity (auditd / rkhunter / AIDE)"
# -----------------------------------------------------------------
if systemctl list-unit-files auditd.service >/dev/null 2>&1; then
    systemctl is-active --quiet auditd && pass "auditd running" || fail "auditd not running"
    rules="$(auditctl -l 2>/dev/null | grep -cE 'passwd|shadow|group|sudoers|sshd' || true)"
    [[ "${rules}" -ge 3 ]] && pass "auditd watches identity & sshd files (${rules} rules)" \
        || warn "few/no auditd rules on identity & sshd files (see docs/operations/SERVER_HARDENING.md §5)"
else
    fail "auditd not installed"
fi

if [[ "${QUICK}" -eq 0 ]]; then
    if command_exists rkhunter; then
        if [[ -f /var/log/rkhunter.log ]]; then
            last="$(stat -c %y /var/log/rkhunter.log 2>/dev/null | cut -d' ' -f1)"
            warns="$(grep -c 'Warning' /var/log/rkhunter.log 2>/dev/null || true)"
            pass "rkhunter last ran ${last} (${warns} warnings in log — review them)"
        else
            warn "rkhunter installed but never ran (no /var/log/rkhunter.log)"
        fi
    else
        warn "rkhunter not installed"
    fi
    if command_exists aide || systemctl list-unit-files aidecheck.service >/dev/null 2>&1; then
        pass "AIDE file-integrity tooling present"
    else
        warn "no file-integrity tool (AIDE) — changes to system binaries go unnoticed"
    fi
fi

# -----------------------------------------------------------------
section "6. Kernel / sysctl profile"
# -----------------------------------------------------------------
for kv in \
    net.ipv4.tcp_syncookies=1 \
    kernel.randomize_va_space=2 \
    kernel.kptr_restrict=2 \
    kernel.dmesg_restrict=1 \
    net.ipv4.conf.all.accept_redirects=0 \
    net.ipv4.conf.all.send_redirects=0 \
    fs.suid_dumpable=0 ; do
    k="${kv%%=*}"; want="${kv#*=}"
    got="$(sysctl -n "${k}" 2>/dev/null || echo '?')"
    [[ "${got}" == "${want}" ]] && pass "sysctl ${k}=${got}" || fail "sysctl ${k}=${got} (expected ${want})"
done
[[ -f /etc/sysctl.d/90-enterprise-service-desk.conf ]] \
    && pass "hardening kit sysctl drop-in installed" \
    || warn "hardening kit sysctl drop-in missing (run scripts/hardening/harden_kernel.sh)"

# -----------------------------------------------------------------
section "7. Docker"
# -----------------------------------------------------------------
if command_exists docker; then
    if [[ -f /etc/docker/daemon.json ]]; then
        while read -r st msg; do
            case "${st}" in
                PASS) pass "${msg}" ;;
                *)    warn "${msg}" ;;
            esac
        done < <(python3 - <<'PY' 2>/dev/null
import json
try:
    cfg = json.load(open("/etc/docker/daemon.json"))
except Exception as exc:
    print("WARN", f"daemon.json unreadable: {exc}")
    raise SystemExit
def chk(key, want):
    got = cfg.get(key, "<unset>")
    print(("PASS" if got == want else "WARN"), f"daemon.json {key} = {got!r} (want {want!r})")
chk("no-new-privileges", True)
chk("live-restore", True)
PY
)
        grep -q '"max-size"' /etc/docker/daemon.json \
            && pass "daemon.json log rotation configured" \
            || warn "daemon.json has no log rotation"
    else
        warn "no /etc/docker/daemon.json — engine defaults apply (run harden_docker.sh)"
    fi
    if docker info >/dev/null 2>&1; then
        priv="$(docker ps -q | xargs -r docker inspect --format '{{.Name}} {{.HostConfig.Privileged}}' | awk '$2=="true"{print $1}')"
        [[ -z "${priv}" ]] && pass "no privileged containers" || fail "privileged containers: ${priv}"
        sock="$(docker ps -q | xargs -r docker inspect --format '{{range .Mounts}}{{if eq .Source "/var/run/docker.sock"}}{{$.Name}} {{end}}{{end}}' | tr -d ' ' | grep -v '^/portainer$' | grep -v '^$' || true)"
        [[ -z "${sock}" ]] && pass "docker.sock not mounted by unexpected containers" \
            || warn "docker.sock mounted outside portainer: ${sock}"
        pub="$(docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E '0\.0\.0\.0:|:::' || true)"
        [[ -z "${pub}" ]] && pass "no container ports published on all interfaces" \
            || { warn "container ports published on ALL interfaces:"; printf '%s\n' "${pub}" | sed 's/^/        | /'; }
        dmembers="$(getent group docker | cut -d: -f4 2>/dev/null)"
        [[ -z "${dmembers}" ]] && pass "docker group empty (use sudo docker)" \
            || warn "docker group members (root-equivalent): ${dmembers}"
    else
        skip "docker daemon not reachable"
    fi
else
    skip "docker not installed"
fi

# -----------------------------------------------------------------
section "8. PostgreSQL exposure"
# -----------------------------------------------------------------
ps="$(ss -lntpH '( sport = :5432 )' 2>/dev/null || true)"
if [[ -z "${ps}" ]]; then
    pass "nothing listening on 5432 on this host"
elif grep -qE '0\.0\.0\.0:5432|\[::\]:5432|\*:5432' <<< "${ps}"; then
    fail "PostgreSQL listening on ALL interfaces:"
    printf '%s\n' "${ps}" | sed 's/^/        | /'
else
    pass "PostgreSQL not bound to all interfaces"
fi

# -----------------------------------------------------------------
section "9. Management UIs (Portainer / Nginx Proxy Manager / Uptime Kuma)"
# -----------------------------------------------------------------
for svc in "9443:Portainer" "81:NginxProxyManager-admin" "8081:NginxProxyManager" "3001:UptimeKuma" "8000:ServiceDesk-app"; do
    port="${svc%%:*}"; name="${svc#*:}"
    s="$(ss -lntpH "( sport = :${port} )" 2>/dev/null || true)"
    [[ -z "${s}" ]] && continue
    if grep -qE "0\.0\.0\.0:${port}|\[::\]:${port}|\*:${port}" <<< "${s}"; then
        warn "${name} (:${port}) listening on ALL interfaces — should be 127.0.0.1 or behind the tunnel/VPN only"
    else
        pass "${name} (:${port}) not exposed on all interfaces"
    fi
done
log "Verify each admin UI additionally has: strong unique password + MFA + Cloudflare Access (or VPN) in front."

# -----------------------------------------------------------------
section "10. Cloudflare tunnel"
# -----------------------------------------------------------------
if pgrep -a cloudflared >/dev/null 2>&1; then
    args="$(pgrep -a cloudflared | head -3)"
    if grep -qE 'trycloudflare|--url' <<< "${args}"; then
        warn "QUICK tunnel in use (trycloudflare) — ephemeral URL, no Access policies, no audit trail."
        warn "Move to a named/managed tunnel: cloudflared service + credentials file + Cloudflare Access."
    else
        pass "cloudflared running as a named/managed tunnel"
    fi
    log "        (process: $(echo "${args}" | sed 's/^/ /'))"
else
    warn "cloudflared not running on this host (fine if the tunnel runs elsewhere)"
fi

# -----------------------------------------------------------------
section "11. Updates & reboot state"
# -----------------------------------------------------------------
if systemctl list-unit-files unattended-upgrades.service >/dev/null 2>&1; then
    systemctl is-enabled --quiet unattended-upgrades 2>/dev/null \
        && pass "unattended-upgrades enabled" || warn "unattended-upgrades not enabled"
fi
if [[ -f /etc/apt/apt.conf.d/20auto-upgrades ]]; then
    grep -q 'Unattended-Upgrade "1"' /etc/apt/apt.conf.d/20auto-upgrades \
        && pass "auto-upgrades configured" || warn "20auto-upgrades does not enable Unattended-Upgrade"
fi
[[ -f /var/run/reboot-required ]] \
    && warn "REBOOT REQUIRED to finish applying security updates ($(cat /var/run/reboot-required.pkgs 2>/dev/null | head -3 | tr '\n' ' '))" \
    || pass "no pending reboot"

# -----------------------------------------------------------------
section "12. Backups & cron"
# -----------------------------------------------------------------
if crontab -l 2>/dev/null | grep -qiE 'backup|pg_dump'; then
    pass "backup cron entries present for root:"
    crontab -l 2>/dev/null | grep -iE 'backup|pg_dump' | sed 's/^/        | /'
else
    for d in /etc/cron.d /etc/cron.daily; do
        grep -riqE 'backup|pg_dump' "${d}" 2>/dev/null && found=1
    done
    [[ "${found:-0}" == "1" ]] && pass "backup entries found in /etc/cron.*" \
        || fail "NO backup cron entries found — a compromised host with no off-host backup is a total loss"
fi
log "        Reminder: backups must be (a) OFF this host, (b) ENCRYPTED, (c) RESTORE-TESTED."

# -----------------------------------------------------------------
section "13. Time sync, logging, misc"
# -----------------------------------------------------------------
if command_exists timedatectl; then
    timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -q yes \
        && pass "clock synchronised (NTP)" || warn "clock NOT NTP-synchronised — log correlation & TLS will suffer"
fi
if command_exists journalctl; then
    maxuse="$(grep -rhE '^\s*(SystemMaxUse|MaxRetentionSec)' /etc/systemd/journald.conf /etc/systemd/journald.conf.d/ 2>/dev/null | head -2)"
    [[ -n "${maxuse}" ]] && pass "journald retention configured" || warn "journald retention unlimited — disk-fill risk"
fi
[[ -d /var/log/apt ]] && pass "apt history retained in /var/log/apt" || warn "no /var/log/apt history"

# SMART (slow-ish) ------------------------------------------------
if [[ "${QUICK}" -eq 0 ]] && command_exists smartctl; then
    disks="$(lsblk -dno NAME,TYPE 2>/dev/null | awk '$2=="disk"{print "/dev/"$1}')"
    for d in ${disks}; do
        if smartctl -H "${d}" 2>/dev/null | grep -q 'PASSED\|OK'; then
            pass "SMART health ${d}: PASSED"
        else
            warn "SMART health ${d}: could not verify (run: smartctl -H ${d})"
        fi
    done
fi

# -----------------------------------------------------------------
echo ""
echo "=============================================================="
printf ' AUDIT RESULT:  %d PASS   %d WARN   %d FAIL   %d SKIP\n' "${PASS}" "${WARN}" "${FAIL}" "${SKIP}"
echo "=============================================================="
if [[ "${FAIL}" -gt 0 ]]; then
    echo " Verdict: NOT HARDENED — fix every FAIL above, then re-run."
    exit 1
else
    echo " Verdict: hardened baseline met. Review WARNs — each one is a"
    echo "          conscious risk decision, not an accident."
    exit 0
fi
