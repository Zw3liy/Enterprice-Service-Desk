#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_fail2ban.sh — installs the hardened Fail2Ban jails.
#
# Installs (from configs/):
#   /etc/fail2ban/jail.d/90-enterprise-service-desk.local
#   /etc/fail2ban/filter.d/npm-auth.conf
# then validates with `fail2ban-client -t` and restarts fail2ban.
#
# The sshd jail is enabled immediately (aggressive mode, exponential
# recidivist bans via UFW). The NPM jail ships commented — enable it
# after verifying the filter against your real NPM logs (the jail file
# explains how).
#
# Environment: DRY_RUN=1
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

step "Fail2Ban hardening"

if ! systemctl list-unit-files fail2ban.service >/dev/null 2>&1 && ! command_exists fail2ban-client; then
    die "fail2ban is not installed (apt install fail2ban)."
fi

install_config "${SCRIPT_DIR}/configs/fail2ban/jail.d/90-enterprise-service-desk.local" \
    "/etc/fail2ban/jail.d/${HARDENING_TAG}.local" || true

install_config "${SCRIPT_DIR}/configs/fail2ban/filter.d/npm-auth.conf" \
    "/etc/fail2ban/filter.d/npm-auth.conf" || true

step "Validating fail2ban configuration"
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would run: fail2ban-client -t"
else
    fail2ban-client -t \
        || die "fail2ban-client -t FAILED — the new config was NOT loaded. Fix jail.d/${HARDENING_TAG}.local"
    ok "fail2ban config valid."
fi

reload_service fail2ban || true

step "Verifying jails"
if [[ "${DRY_RUN}" != "1" ]] && command_exists fail2ban-client; then
    sleep 1
    fail2ban-client status 2>/dev/null | sed -n 's/^Jail list:/Jail list:/p' | sed 's/^/    /'
    if fail2ban-client status sshd >/dev/null 2>&1; then
        ok "sshd jail active. Check ignoreip in the jail if you manage from a fixed IP:"
        log "    /etc/fail2ban/jail.d/${HARDENING_TAG}.local"
    else
        fail "sshd jail not active — inspect: fail2ban-client status"
    fi
fi

step "Summary"
log "Jails: sshd (aggressive, 24h+) + recidive (4 weeks). Bans are applied via UFW (all ports)."
log "Add your management IP to ignoreip BEFORE this runs on a live host, or you can ban yourself."
