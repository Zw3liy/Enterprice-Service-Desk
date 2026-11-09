#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_auditd.sh — installs the forensic audit ruleset.
#
# Installs configs/auditd/90-enterprise-service-desk.rules to
#   /etc/audit/rules.d/
# and loads it with `augenrules --load`.
#
# The ruleset watches identity files, sudoers, sshd config/keys, cron,
# the Docker binary & socket, kernel module loading, clock changes,
# mounts, deletions and permission changes — all tagged for
# `ausearch -k <tag>` queries.
#
# Immutability (-e 2) is shipped COMMENTED in the rules file: enable it
# only once the ruleset is final (after -e 2, changing rules needs a
# reboot). Iterate first, lock down second.
#
# Environment: DRY_RUN=1
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

step "AuditD rules installation"

if ! systemctl list-unit-files auditd.service >/dev/null 2>&1 && ! command_exists auditctl; then
    die "auditd is not installed (apt install auditd audispd-plugins)."
fi

install_config "${SCRIPT_DIR}/configs/auditd/90-enterprise-service-desk.rules" \
    "/etc/audit/rules.d/${HARDENING_TAG}.rules" || true

step "Loading rules"
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would run: augenrules --load"
else
    if command_exists augenrules; then
        augenrules --load || die "augenrules --load failed — inspect the rules file syntax."
    else
        auditctl -R "/etc/audit/rules.d/${HARDENING_TAG}.rules" \
            || die "auditctl -R failed — inspect the rules file syntax."
    fi
    ok "Audit rules loaded."
fi

step "Verifying"
if [[ "${DRY_RUN}" != "1" ]]; then
    count="$(auditctl -l 2>/dev/null | grep -c 'enterprise\|identity\|sshd\|sudoers\|docker\|modules\|time\|delete\|perm_mod\|mounts' || true)"
    if [[ "${count}" -ge 15 ]]; then
        ok "${count} tagged audit rules active."
    else
        warn "only ${count} expected rules visible via auditctl -l — review /etc/audit/rules.d/${HARDENING_TAG}.rules"
    fi
    auditctl -s 2>/dev/null | sed 's/^/    /' || true
fi

step "Summary"
log "Query examples:"
log "    ausearch -k identity -i          # who changed users/passwords"
log "    ausearch -k sshd -i              # sshd config changes"
log "    ausearch -k docker -i            # docker admin activity"
log "    aureport --auth --summary        # auth failure summary"
log "When the ruleset is final, uncomment '-e 2' in the rules file and reboot:"
log "    /etc/audit/rules.d/${HARDENING_TAG}.rules"
log "Ship /var/log/audit/ OFF this host — attackers delete local logs first."
