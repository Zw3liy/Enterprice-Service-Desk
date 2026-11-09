#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_login.sh — password policy & account lockout configuration.
#
# Installs:
#   /etc/security/pwquality.conf   (14+ chars, mixed classes, dict check)
#   /etc/security/faillock.conf    (5 failures -> 15 min lockout, incl. root)
# and edits /etc/login.defs (backed up) to tighten defaults for NEW
# accounts:
#   PASS_MAX_DAYS 90, PASS_MIN_DAYS 1, PASS_WARN_AGE 7,
#   UMASK 027, LOGIN_RETRIES 3, ENCRYPT_METHOD SHA512
#
# Two manual steps this script deliberately does NOT do:
#   1. Activating pam_faillock (PAM stack change — lockout risk):
#        sudo pam-auth-update
#      → enable "Restrict failed login attempts", test a SECOND login
#      session before closing this one.
#   2. Aging EXISTING accounts — login.defs only affects new ones:
#        sudo chage -M 90 -m 1 -W 7 <user>   (per existing user)
#
# Environment: DRY_RUN=1
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

step "Password policy (PAM pwquality)"
install_config "${SCRIPT_DIR}/configs/pam/pwquality.conf" \
    /etc/security/pwquality.conf || true

step "Account lockout policy (pam_faillock)"
install_config "${SCRIPT_DIR}/configs/pam/faillock.conf" \
    /etc/security/faillock.conf || true

step "login.defs defaults for new accounts"
if [[ -f /etc/login.defs ]]; then
    backup_file /etc/login.defs
    set_def() {
        local key="$1" value="$2"
        if grep -qE "^\s*${key}\b" /etc/login.defs; then
            if grep -qE "^\s*${key}\s+${value}\s*$" /etc/login.defs; then
                log "login.defs ${key} already ${value}."
            elif [[ "${DRY_RUN}" == "1" ]]; then
                log "DRY-RUN: would set login.defs ${key} ${value}"
            else
                sed -i -E "s|^\s*${key}\b.*|${key}    ${value}|" /etc/login.defs
                log "login.defs: ${key} -> ${value}"
            fi
        else
            if [[ "${DRY_RUN}" == "1" ]]; then
                log "DRY-RUN: would append login.defs ${key} ${value}"
            else
                printf '%s    %s\n' "${key}" "${value}" >> /etc/login.defs
                log "login.defs: appended ${key} ${value}"
            fi
        fi
    }
    set_def PASS_MAX_DAYS 90
    set_def PASS_MIN_DAYS 1
    set_def PASS_WARN_AGE 7
    set_def UMASK 027
    set_def LOGIN_RETRIES 3
    set_def ENCRYPT_METHOD SHA512
else
    skip "/etc/login.defs not found."
fi

step "Summary"
log "Policy in force for NEW passwords/accounts. Two manual follow-ups:"
log "  1. Activate lockout: sudo pam-auth-update  -> 'Restrict failed login attempts'"
log "     (keep this session open; verify a second login first)"
log "  2. Age existing accounts: sudo chage -M 90 -m 1 -W 7 <user>"
