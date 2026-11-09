#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_updates.sh — automatic security updates + bounded logging.
#
# Installs:
#   /etc/apt/apt.conf.d/20auto-upgrades        (daily update+upgrade on)
#   /etc/apt/apt.conf.d/51-enterprise-service-desk  (no auto-reboot,
#       unused-dep cleanup, syslog + mail reporting)
#   /etc/needrestart/conf.d/90-auto.conf       (auto-restart services
#       after library upgrades — no interactive prompt on a headless box)
#   /etc/systemd/journald.conf.d/90-retention.conf  (bounded journald:
#       250 MB / 2 weeks — unbounded logs are a disk-DoS risk)
#
# Environment: DRY_RUN=1
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

step "Automatic security updates"

if command_exists apt-get; then
    install_config "${SCRIPT_DIR}/configs/apt/20auto-upgrades" \
        /etc/apt/apt.conf.d/20auto-upgrades || true
    install_config "${SCRIPT_DIR}/configs/apt/51-enterprise-service-desk" \
        /etc/apt/apt.conf.d/51-enterprise-service-desk || true
else
    skip "apt not found — this host is outside the Ubuntu/Debian target of this kit."
fi

if [[ -d /etc/needrestart ]] || command_exists needrestart; then
    install_config "${SCRIPT_DIR}/configs/needrestart/90-auto.conf" \
        /etc/needrestart/conf.d/90-auto.conf || true
else
    skip "needrestart not installed (apt install needrestart)."
fi

step "Journald retention"
install_config "${SCRIPT_DIR}/configs/journald/90-retention.conf" \
    "/etc/systemd/journald.conf.d/${HARDENING_TAG}-retention.conf" || true
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would restart systemd-journald"
else
    systemctl restart systemd-journald 2>/dev/null && ok "journald restarted with new retention." \
        || warn "could not restart systemd-journald — settings apply at next boot."
fi

step "Enabling the apt timers"
if command_exists apt-get; then
    for timer in apt-daily.timer apt-daily-upgrade.timer; do
        if systemctl list-unit-files "${timer}" >/dev/null 2>&1; then
            run systemctl enable --now "${timer}"
        fi
    done
    ok "apt-daily / apt-daily-upgrade timers enabled."
fi

step "Verifying"
if command_exists apt-get && [[ "${DRY_RUN}" != "1" ]]; then
    unattended-upgrades --help >/dev/null 2>&1 \
        && ok "unattended-upgrades available." \
        || warn "unattended-upgrades not installed (apt install unattended-upgrades)"
    [[ -f /var/run/reboot-required ]] \
        && warn "a reboot is currently pending (from earlier updates)" \
        || ok "no pending reboot."
fi

step "Summary"
log "Security updates apply automatically; the host NEVER reboots itself."
log "The hardening audit flags /var/run/reboot-required — schedule reboots on YOUR timeline."
