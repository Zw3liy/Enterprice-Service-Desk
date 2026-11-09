#!/usr/bin/env bash
# -------------------------------------------------------------------
# lib.sh — shared helpers for the server hardening kit.
#
# Sourced by every script in scripts/hardening/. Never run directly.
#
# Design rules for this kit:
#   * Idempotent — running a script twice must be safe.
#   * Non-destructive — every file touched is backed up first.
#   * Fail-closed on validation — never reload a service with a config
#     that does not pass its own config test (sshd -t, nginx -t, ...).
#   * DRY_RUN=1 prints what would happen and changes nothing.
# -------------------------------------------------------------------

set -euo pipefail

# Tag used in drop-in file names so everything this kit installs is
# easy to find and easy to remove: grep for "enterprise-service-desk".
HARDENING_TAG="90-enterprise-service-desk"

DRY_RUN="${DRY_RUN:-0}"

log()  { printf '%s [INFO] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
step() { printf '\n==> %s\n' "$*"; }
ok()   { printf '    [PASS] %s\n' "$*"; }
warn() { printf '    [WARN] %s\n' "$*"; }
fail() { printf '    [FAIL] %s\n' "$*"; }
skip() { printf '    [SKIP] %s\n' "$*"; }

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        die "This script must run as root. Re-run with: sudo $0"
    fi
}

# Detect the distro family. The kit targets Ubuntu/Debian (UFW,
# unattended-upgrades style hosts). Set HARDENING_FORCE_DISTRO=debian
# or =ubuntu to override detection for testing.
detect_distro() {
    if [[ -n "${HARDENING_FORCE_DISTRO:-}" ]]; then
        echo "${HARDENING_FORCE_DISTRO}"
        return
    fi
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        case "${ID:-}" in
            ubuntu) echo "ubuntu" ;;
            debian) echo "debian" ;;
            raspbian) echo "debian" ;;
            *)
                if [[ "${ID_LIKE:-}" == *debian* || "${ID_LIKE:-}" == *ubuntu* ]]; then
                    echo "debian"
                else
                    echo "unknown"
                fi
                ;;
        esac
    else
        echo "unknown"
    fi
}

# Backup a file before modifying it. Keeps one timestamped copy per run.
backup_file() {
    local file="$1"
    if [[ -f "${file}" ]]; then
        local stamp backup
        stamp="$(date -u +%Y%m%dT%H%M%SZ)"
        backup="${file}.bak.${stamp}"
        if [[ "${DRY_RUN}" == "1" ]]; then
            log "DRY-RUN: would back up ${file} -> ${backup}"
        else
            cp -a "${file}" "${backup}"
            log "Backed up ${file} -> ${backup}"
        fi
    fi
}

# Write a drop-in config file only if its content differs from what is
# already there. Usage: install_dropin /etc/ssh/sshd_config.d/xx.conf <<'EOF' ... EOF
install_dropin() {
    local target="$1"
    local content
    content="$(cat)"

    if [[ -f "${target}" ]] && [[ "$(cat "${target}")" == "${content}" ]]; then
        log "${target} already up to date."
        return 1   # signals "no change"
    fi

    backup_file "${target}"
    if [[ "${DRY_RUN}" == "1" ]]; then
        log "DRY-RUN: would write ${target}"
        cat <<< "${content}" | sed 's/^/        | /'
    else
        mkdir -p "$(dirname "${target}")"
        printf '%s\n' "${content}" > "${target}"
        chmod 0644 "${target}"
        log "Wrote ${target}"
    fi
    return 0   # signals "changed"
}

# Install a config file from this kit's configs/ directory, keeping a
# backup of anything it replaces. Same return convention as
# install_dropin: 0 = changed, 1 = already up to date.
install_config() {
    local src="$1" dest="$2" mode="${3:-0644}"

    [[ -f "${src}" ]] || die "config template missing: ${src}"

    if [[ -f "${dest}" ]] && cmp -s "${src}" "${dest}"; then
        log "${dest} already up to date."
        return 1
    fi

    backup_file "${dest}"
    if [[ "${DRY_RUN}" == "1" ]]; then
        log "DRY-RUN: would install ${src} -> ${dest} (mode ${mode})"
    else
        mkdir -p "$(dirname "${dest}")"
        install -m "${mode}" "${src}" "${dest}"
        log "Installed ${dest} (from $(basename "${src}"))"
    fi
    return 0
}

# Reload/restart a service only if it exists and is active/enable-able.
reload_service() {
    local svc="$1"
    if ! systemctl list-unit-files "${svc}.service" >/dev/null 2>&1; then
        skip "${svc} not installed on this host — config left in place for when it is."
        return 2
    fi
    if [[ "${DRY_RUN}" == "1" ]]; then
        log "DRY-RUN: would restart ${svc}"
        return 0
    fi
    if systemctl restart "${svc}"; then
        ok "Restarted ${svc}."
        return 0
    fi
    warn "Could not restart ${svc} (is systemd running?). Restart it manually."
    return 1
}

# Run a command, or just print it under DRY_RUN=1.
run() {
    if [[ "${DRY_RUN}" == "1" ]]; then
        log "DRY-RUN: $*"
    else
        "$@"
    fi
}

service_name() {
    # Debian/Ubuntu call it "ssh"; most other distros "sshd".
    if systemctl list-unit-files ssh.service >/dev/null 2>&1; then
        echo "ssh"
    else
        echo "sshd"
    fi
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}
