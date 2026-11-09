#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_kernel.sh — kernel / network stack / resource hardening.
#
# Installs:
#   /etc/sysctl.d/90-enterprise-service-desk.conf    (network + kernel)
#   /etc/security/limits.d/90-enterprise-service-desk.conf (core dumps)
#   /etc/modprobe.d/90-enterprise-service-desk.conf  (rare protocols off)
#
# Deliberately NOT touched:
#   * net.ipv4.ip_forward — Docker requires =1 and manages it itself.
#   * Anything Docker manages in the netfilter namespace.
#
# Environment: DRY_RUN=1 to preview.
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

step "Kernel / network hardening"

# ---- sysctl -------------------------------------------------------
install_dropin "/etc/sysctl.d/${HARDENING_TAG}.conf" <<'EOF' || true
# Managed by scripts/hardening/harden_kernel.sh — do not edit by hand.

# --- Anti-spoofing / redirect abuse --------------------------------
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# --- ICMP hygiene ---------------------------------------------------
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# --- TCP hardening --------------------------------------------------
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_rfc1337 = 1
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# --- Kernel pointer / debug surface --------------------------------
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.yama.ptrace_scope = 1
kernel.perf_event_paranoid = 2
kernel.unprivileged_bpf_disabled = 1
kernel.sysrq = 0

# --- Filesystem protections ----------------------------------------
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.protected_fifos = 2
fs.protected_regular = 2
fs.suid_dumpable = 0

# --- ASLR ----------------------------------------------------------
kernel.randomize_va_space = 2
EOF

# ---- core dumps ---------------------------------------------------
install_dropin "/etc/security/limits.d/${HARDENING_TAG}.conf" <<'EOF' || true
# Managed by scripts/hardening/harden_kernel.sh — do not edit by hand.
*    hard    core    0
*    soft    core    0
root hard    core    0
root soft    core    0
EOF

# Also make sure systemd-coredump won't keep cores around, where present.
if [[ -d /etc/systemd ]]; then
    install_dropin "/etc/systemd/coredump.conf.d/${HARDENING_TAG}.conf" <<'EOF' || true
[Coredump]
Storage=none
ProcessSizeMax=0
EOF
fi

# ---- rare/legacy kernel protocols (CIS benchmark recommendation) --
install_dropin "/etc/modprobe.d/${HARDENING_TAG}.conf" <<'EOF' || true
# Managed by scripts/hardening/harden_kernel.sh — do not edit by hand.
# These protocols have no legitimate use on this host and a history of
# kernel CVEs. Blacklisting shrinks the attack surface.
install dccp /bin/true
install sctp /bin/true
install rds /bin/true
install tipc /bin/true
install cramfs /bin/true
install freevxfs /bin/true
install hfs /bin/true
install hfsplus /bin/true
install jffs2 /bin/true
install squashfs /bin/true  # NOTE: remove this line if snap is in use
install udf /bin/true
EOF
if command_exists snap && snap list >/dev/null 2>&1; then
    warn "snap detected — squashfs must NOT be blacklisted. Remove the squashfs line from /etc/modprobe.d/${HARDENING_TAG}.conf"
fi

# ---- apply sysctl -------------------------------------------------
step "Applying sysctl settings"
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would run: sysctl --system"
else
    sysctl --system >/dev/null
    ok "sysctl settings applied."
fi

# ---- verify a few critical values ---------------------------------
step "Verifying critical values"
declare -A expect=(
    [net.ipv4.tcp_syncookies]=1
    [kernel.randomize_va_space]=2
    [net.ipv4.conf.all.accept_redirects]=0
)
for key in "${!expect[@]}"; do
    actual="$(sysctl -n "${key}" 2>/dev/null || echo "?")"
    if [[ "${actual}" == "${expect[${key}]}" ]]; then
        ok "${key} = ${actual}"
    else
        fail "${key} = ${actual} (expected ${expect[${key}]})"
    fi
done

step "Summary"
log "Configs installed under /etc/sysctl.d/, /etc/security/limits.d/, /etc/modprobe.d/ (tag: ${HARDENING_TAG})."
log "A reboot is recommended for the modprobe blacklist and limits to fully apply."
