#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_monitoring.sh — disk-health, rootkit scanning, and the weekly
# posture-audit schedule.
#
# Installs:
#   /etc/smartd.conf                  (SMART warnings -> root mail)
#   /etc/rkhunter.conf.local          (dpkg verification, no network
#                                      fetches, mail on warning)
#   /etc/cron.d/rkhunter              (daily scan + propupd)
#   /etc/cron.d/hardening-audit       (weekly audit_hardening.sh --quick
#                                      -> /var/log/hardening-audit.log)
#
# The audit cron path is substituted with THIS checkout's absolute
# path — run the script from wherever the repo lives on the server.
#
# Environment: DRY_RUN=1
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

step "SMART disk monitoring"
if command_exists smartctl; then
    install_config "${SCRIPT_DIR}/configs/smartd/smartd.conf" /etc/smartd.conf || true
    if systemctl list-unit-files smartd.service >/dev/null 2>&1; then
        reload_service smartd || true
    elif systemctl list-unit-files smartmontools.service >/dev/null 2>&1; then
        reload_service smartmontools || true
    else
        skip "smartd service not found — config in place for when it is installed."
    fi
    if [[ "${DRY_RUN}" != "1" ]]; then
        log "One-time alert-path test (sends a test mail): smartd -q onecheck -M test"
    fi
else
    skip "smartmontools not installed (apt install smartmontools)."
fi

step "Rootkit hunter schedule"
if command_exists rkhunter; then
    install_config "${SCRIPT_DIR}/configs/rkhunter/rkhunter.conf.local" \
        /etc/rkhunter.conf.local || true
    install_config "${SCRIPT_DIR}/configs/cron/rkhunter" /etc/cron.d/rkhunter || true
    if [[ "${DRY_RUN}" != "1" ]]; then
        rkhunter --propupd >/dev/null 2>&1 || warn "rkhunter --propupd failed (run once manually)."
    fi
else
    skip "rkhunter not installed (apt install rkhunter)."
fi

step "Weekly hardening audit schedule"
audit_script="${REPO_ROOT}/scripts/hardening/audit_hardening.sh"
if [[ -x "${audit_script}" ]]; then
    if [[ "${DRY_RUN}" == "1" ]]; then
        log "DRY-RUN: would install /etc/cron.d/hardening-audit (root -> ${audit_script})"
    else
        sed "s|@HARDENING_ROOT@|${REPO_ROOT}|g" \
            "${SCRIPT_DIR}/configs/cron/hardening-audit" > /tmp/hardening-audit.cron
        install -m 0644 /tmp/hardening-audit.cron /etc/cron.d/hardening-audit
        rm -f /tmp/hardening-audit.cron
        ok "Installed /etc/cron.d/hardening-audit (Mondays 04:17)."
    fi
else
    warn "audit_hardening.sh not found/executable at ${audit_script}"
fi

step "Summary"
log "Schedules now active:"
log "  daily  03:27  rkhunter rootkit scan (warnings mailed to root)"
log "  weekly 04:17  hardening audit -> /var/log/hardening-audit.log"
log "  smartd        continuous disk health (warnings mailed to root)"
log "Mailing root requires a local MTA — if none is installed, wire the"
log "events into your notification channel of choice (SERVER_HARDENING.md §3.7)."
