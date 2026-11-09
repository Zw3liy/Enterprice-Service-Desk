#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_edge.sh — edge configuration for Nginx Proxy Manager and the
# Cloudflare tunnel.
#
# This script is an INSTALLER + INSTRUCTOR, because both surfaces are
# live-generated: NPM generates its nginx config from its database, and
# a cloudflared config carries per-host secrets. Clobbering either
# automatically would cause an outage, so:
#
#   * Native nginx (if installed): installs the snippets into
#     /etc/nginx/snippets/, validates with `nginx -t`, reloads.
#   * NPM: prints the exact mount + paste instructions for the
#     snippets in configs/nginx/ (http_top zones/real-ip, per-host
#     Advanced tabs), verified with `nginx -t` inside the container.
#   * cloudflared: installs the named-tunnel TEMPLATE to
#     /etc/cloudflared/config.yml.example (never overwrites a live
#     config.yml unless INSTALL_CLOUDFLARED_CONFIG=1 and none exists).
#
# Environment:
#   INSTALL_CLOUDFLARED_CONFIG=1  install the template as the real
#                                 config IF no config.yml exists yet
#   DRY_RUN=1                     preview only
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

CFG="${SCRIPT_DIR}/configs"

step "Native nginx (when present)"
if command_exists nginx; then
    install_config "${CFG}/nginx/http_top-real-ip-cloudflare.conf" \
        /etc/nginx/snippets/real-ip-cloudflare.conf || true
    install_config "${CFG}/nginx/http_top-rate-limit.conf" \
        /etc/nginx/snippets/rate-limit-zones.conf || true
    install_config "${CFG}/nginx/server-advanced/security-headers.conf" \
        /etc/nginx/snippets/security-headers.conf || true
    install_config "${CFG}/nginx/server-advanced/ssl-hardening.conf" \
        /etc/nginx/snippets/ssl-hardening.conf || true
    if [[ "${DRY_RUN}" == "1" ]]; then
        log "DRY-RUN: would run nginx -t && systemctl reload nginx"
    else
        nginx -t || die "nginx -t failed — snippets installed but NOT applied. Fix and reload manually."
        systemctl reload nginx 2>/dev/null && ok "nginx reloaded." || warn "reload nginx manually."
    fi
else
    skip "native nginx not on this host (NPM runs it in a container)."
fi

step "Nginx Proxy Manager — snippet installation"
cat <<EOF
    NPM generates its nginx config from its database, so snippets are
    MOUNTED and PASTED (verified with nginx -t before reload):

    1. Create a host directory and put the http-context pieces in it:
         mkdir -p /opt/npm-custom
         cat ${CFG}/nginx/http_top-real-ip-cloudflare.conf \\
             ${CFG}/nginx/http_top-rate-limit.conf > /opt/npm-custom/http_top.conf
       (NPM includes /data/nginx/custom/http_top.conf at the top of its
       http {} block — verified against NPM's nginx.conf on GitHub.)

    2. Mount it in the NPM container (see configs/compose/ops-stack.hardened.yml):
         volumes:
           - /opt/npm-custom:/data/nginx/custom:ro

    3. Restart NPM, verify, reload:
         docker exec npm nginx -t && docker exec npm nginx -s reload

    4. Per HTTPS proxy host, paste BOTH files from
       ${CFG}/nginx/server-advanced/  into the host's "Advanced" tab:
         security-headers.conf + ssl-hardening.conf (+ rate-limit.conf).

    5. If NPM's UI "real IP" feature is enabled instead, skip the
       real-ip file (they do the same job).
EOF

step "Cloudflare named tunnel template"
install_config "${CFG}/cloudflared/config.yml" \
    /etc/cloudflared/config.yml.example || true

if [[ ! -f /etc/cloudflared/config.yml && "${INSTALL_CLOUDFLARED_CONFIG:-0}" == "1" ]]; then
    install_config "${CFG}/cloudflared/config.yml" /etc/cloudflared/config.yml || true
    warn "Installed as the live config — fill in <TUNNEL-UUID> and the credentials path BEFORE running."
elif [[ -f /etc/cloudflared/config.yml ]]; then
    log "/etc/cloudflared/config.yml exists — left untouched (merge by hand from the .example if needed)."
fi

cat <<'EOF'

    Named tunnel quickstart (replaces the Quick Tunnel):
      1. cloudflared tunnel login
      2. cloudflared tunnel create esd
      3. Fill the UUID + credentials path into /etc/cloudflared/config.yml
         (start from /etc/cloudflared/config.yml.example)
      4. cloudflared tunnel route dns esd service-desk.example.com
      5. cloudflared service install <TOKEN-or-UUID>
      6. Attach Cloudflare Access (SSO+MFA) to EVERY admin hostname in
         Zero Trust -> Access -> Applications. Do not skip this.
EOF

step "Summary"
log "Edge hardening is config + verification, not automation — the instructions"
log "above end with nginx -t / cloudflared checks so nothing silent breaks."
