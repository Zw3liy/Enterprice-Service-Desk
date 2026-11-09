#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_firewall.sh — UFW baseline: zero public inbound ports.
#
# With the Cloudflare tunnel carrying all traffic inbound, this host
# needs NO publicly open ports at all. The script:
#   * default deny incoming / deny routed / allow outgoing
#   * rate-limited SSH allow rule for your management address ONLY
#   * low-rate logging
#   * enables UFW (with lockout guards — see below)
#
# Docker caveat (documented in SERVER_HARDENING.md §3.2): published
# container ports BYPASS UFW via the DOCKER iptables chain. UFW alone
# cannot keep a published port private — bind container ports to
# 127.0.0.1 (docker-compose.production.yml / ops-stack.hardened.yml).
#
# Lockout guards:
#   * An allow+rate-limit rule for the SSH port is created BEFORE
#     `ufw enable`, sourced from (in order):
#       1. SSH_MGMT_CIDR   (explicit env, e.g. SSH_MGMT_CIDR=196.10.5.22/32)
#       2. the client IP of the current SSH session (SSH_CONNECTION)
#   * If neither is available the script refuses to enable UFW.
#   * KEEP YOUR CURRENT SSH SESSION OPEN and open a second login to
#     verify before closing anything.
#
# Environment:
#   SSH_MGMT_CIDR=...     management IP/CIDR allowed to SSH (recommended)
#   SSH_PORT=22           override SSH port detection
#   UFW_ALLOW_LAN_SUBNET= e.g. 10.0.0.0/24 — extra allow for LAN/VPN
#   UFW_EGRESS=deny       stricter: default deny outgoing (+ curated
#                         allowlist for DNS/NTP/HTTP(S)/SMTP-submission)
#   FORCE_ENABLE=1        enable even if no SSH allow rule could be made
#   DRY_RUN=1             preview only
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

command_exists ufw || die "ufw is not installed (apt install ufw)."

step "Firewall (UFW) hardening"

# ---- determine SSH port & management source -----------------------
ssh_port="${SSH_PORT:-}"
if [[ -z "${ssh_port}" ]]; then
    if command_exists sshd; then
        ssh_port="$(sshd -T 2>/dev/null | awk 'tolower($1)=="port" {print $2; exit}')"
    fi
fi
ssh_port="${ssh_port:-22}"
log "SSH port: ${ssh_port}"

mgmt_cidr="${SSH_MGMT_CIDR:-}"
if [[ -z "${mgmt_cidr}" && -n "${SSH_CONNECTION:-}" ]]; then
    client_ip="$(awk '{print $1}' <<< "${SSH_CONNECTION}")"
    if [[ "${client_ip}" == *:* ]]; then
        mgmt_cidr="${client_ip}/128"
    else
        mgmt_cidr="${client_ip}/32"
    fi
    log "Derived management source from SSH_CONNECTION: ${mgmt_cidr}"
    log "(set SSH_MGMT_CIDR to pin a permanent address — DHCP changes will lock you out otherwise!)"
fi

if [[ -z "${mgmt_cidr}" && "${FORCE_ENABLE:-0}" != "1" ]]; then
    die "No management source known. Set SSH_MGMT_CIDR=<your-ip>/32 (or FORCE_ENABLE=1 if UFW already allows your access)."
fi

# ---- defaults -----------------------------------------------------
step "Setting default policies"
run ufw default deny incoming
run ufw default deny routed

if [[ "${UFW_EGRESS:-allow}" == "deny" ]]; then
    run ufw default deny outgoing
    # Curated egress allowlist for a tunnel-fronted host.
    run ufw allow out 53/tcp comment 'DNS'
    run ufw allow out 53/udp comment 'DNS'
    run ufw allow out 123/udp comment 'NTP'
    run ufw allow out 80/tcp comment 'ACME/apt/crl'
    run ufw allow out 443/tcp comment 'Cloudflare tunnel/apt/updates'
    run ufw allow out 587/tcp comment 'SMTP submission (mail alerts)'
    log "Egress default-deny installed with a minimal allowlist."
else
    run ufw default allow outgoing
fi

run ufw logging low

# ---- management rules (BEFORE any enable) -------------------------
if [[ -n "${mgmt_cidr}" ]]; then
    step "Allowing SSH from ${mgmt_cidr} (rate limited)"
    run ufw limit from "${mgmt_cidr}" to any port "${ssh_port}" proto tcp comment 'SSH management (rate-limited)'
fi

if [[ -n "${UFW_ALLOW_LAN_SUBNET:-}" ]]; then
    step "Allowing LAN/VPN subnet ${UFW_ALLOW_LAN_SUBNET}"
    run ufw allow from "${UFW_ALLOW_LAN_SUBNET}" comment 'LAN/VPN access'
fi

# ---- enable with guard -------------------------------------------
step "Enabling UFW"
if [[ -z "${mgmt_cidr}" && "${FORCE_ENABLE:-0}" == "1" ]]; then
    warn "FORCE_ENABLE=1 with no SSH allow rule — you have 10 seconds to Ctrl-C..."
    sleep 10
fi
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would run: ufw --force enable"
else
    ufw --force enable
    ok "UFW enabled."
fi

step "Resulting rules"
run ufw status verbose

step "Summary"
log "Expected posture: NO ports open to the internet; SSH only from ${mgmt_cidr:-<your-ip>}."
log "Verify from OUTSIDE this network:  nmap -Pn <public-ip>   (expect: all scanned ports filtered/closed)"
log "No inbound allow is needed for the Cloudflare tunnel — it dials OUT."
log "Remember: Docker-published ports bypass UFW. Keep container ports on 127.0.0.1."
log "KEEP THIS SSH SESSION OPEN until a fresh login is proven."
