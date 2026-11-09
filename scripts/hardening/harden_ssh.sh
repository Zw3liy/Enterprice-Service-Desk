#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_ssh.sh — SSH server hardening.
#
# Installs a drop-in at /etc/ssh/sshd_config.d/90-enterprise-service-desk.conf
# (OpenSSH reads the Include directory first, and the first obtained
# value wins, so these settings take precedence over the main config).
#
# Safety: the config is validated with `sshd -t` BEFORE the daemon is
# reloaded. If validation fails, nothing is reloaded and the previous
# config keeps running. Password authentication is already disabled on
# this host — this script never enables it and never touches keys.
#
# Environment overrides (all optional):
#   SSH_ALLOW_GROUPS="ssh-users"   restrict SSH logins to a group (OFF by
#                                  default: enabling it without creating
#                                  the group and adding yourself first
#                                  locks you out).
#   SSH_ALLOW_USERS="alice,bob"    restrict SSH logins to these users.
#   SSH_ALLOW_TCP_FORWARDING=yes   keep TCP forwarding (default: no).
#   DRY_RUN=1                      print actions, change nothing.
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

DROP_IN="/etc/ssh/sshd_config.d/${HARDENING_TAG}.conf"
SSHD_BIN="$(command -v sshd || true)"
[[ -n "${SSHD_BIN}" ]] || die "sshd binary not found — is openssh-server installed?"

step "SSH hardening"

allow_forwarding="no"
[[ "${SSH_ALLOW_TCP_FORWARDING:-no}" == "yes" ]] && allow_forwarding="yes"

restrict_lines=""
if [[ -n "${SSH_ALLOW_GROUPS:-}" ]]; then
    restrict_lines+="AllowGroups ${SSH_ALLOW_GROUPS//,/ }"$'\n'
    log "Login restricted to group(s): ${SSH_ALLOW_GROUPS}"
fi
if [[ -n "${SSH_ALLOW_USERS:-}" ]]; then
    restrict_lines+="AllowUsers ${SSH_ALLOW_USERS//,/ }"$'\n'
    log "Login restricted to user(s): ${SSH_ALLOW_USERS}"
fi

changed=0
install_dropin "${DROP_IN}" <<EOF || changed=$?
# Managed by scripts/hardening/harden_ssh.sh — do not edit by hand.
# Remove this file and run \`systemctl reload ssh\` to revert.

# --- Authentication -------------------------------------------------
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
HostbasedAuthentication no
IgnoreRhosts yes
GSSAPIAuthentication no
KerberosAuthentication no
PermitUserEnvironment no
AuthenticationMethods publickey

# --- Session / brute-force surface ----------------------------------
MaxAuthTries 3
MaxSessions 5
MaxStartups 10:30:60
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
TCPKeepAlive yes

# --- Forwarding / tunneling (abuse surface) -------------------------
DisableForwarding yes
AllowTcpForwarding ${allow_forwarding}
AllowAgentForwarding no
AllowStreamLocalForwarding no
PermitTunnel no
GatewayPorts no
X11Forwarding no

# --- Crypto (modern-only suites; old clients may need these relaxed) -
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512
Ciphers chacha20-poly1305@openssh.com,aes128-gcm@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
CASignatureAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256

# --- Logging (feeds fail2ban / crowdsec / auditd) -------------------
LogLevel VERBOSE
${restrict_lines}Banner /etc/issue.net
StrictModes yes
UsePAM yes
PrintMotd no
EOF

# Banner file (harmless, and gives a legal notice on auth prompts).
if [[ ! -f /etc/issue.net ]]; then
    if [[ "${DRY_RUN}" == "1" ]]; then
        log "DRY-RUN: would create /etc/issue.net banner"
    else
        printf 'Authorised access only. All activity is monitored and logged.\n' > /etc/issue.net
        chmod 0644 /etc/issue.net
        log "Created /etc/issue.net banner."
    fi
fi

# Validate BEFORE reloading — fail closed.
step "Validating sshd configuration"
# sshd -t needs the privilege-separation dir that the daemon's systemd
# unit normally creates (RuntimeDirectory=sshd). Harmless if present.
run mkdir -p /run/sshd
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would run: ${SSHD_BIN} -t"
else
    if ! "${SSHD_BIN}" -t; then
        die "sshd -t FAILED. The new config was NOT loaded. Fix ${DROP_IN} and re-run."
    fi
    ok "sshd -t passed."
fi

step "Reloading SSH daemon"
svc="$(service_name)"
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would run: systemctl reload ${svc}"
else
    if systemctl reload "${svc}"; then
        ok "Reloaded ${svc}. Existing SSH sessions are not disconnected."
    elif systemctl is-active --quiet "${svc}"; then
        die "reload of ${svc} failed while it is active — investigate before closing this session."
    else
        warn "${svc} is not running on this host — config is validated and installed; it applies when the service starts."
    fi
fi

step "Summary"
log "Drop-in: ${DROP_IN}"
log "Verify from a NEW terminal (keep your current session open!):"
log "    ssh -o PreferredAuthentications=password root@localhost   # must fail"
log "    ssh ${USER:-<you>}@localhost                              # key auth only"
if [[ "${changed}" -eq 0 ]]; then
    log "Note: config was already in place; reload was still performed."
fi
