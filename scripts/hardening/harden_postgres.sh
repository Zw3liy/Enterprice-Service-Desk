#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_postgres.sh — PostgreSQL hardening for this platform.
#
# Works for both deployments:
#   * native PostgreSQL on this host (psql superuser access), and
#   * containerized PostgreSQL (compose 'db' service) — then it audits
#     exposure and prints the equivalent SQL to run inside the container.
#
# Native mode applies (via ALTER SYSTEM, so it is idempotent and lives
# in postgresql.auto.conf, never hand-edited):
#   password_encryption = scram-sha-256
#   ssl                 = on           (only if server certs exist)
#   log_connections / log_disconnections = on
#   log_min_duration_statement = 1000   (slow query log)
#   log_line_prefix with user/db/app    (attribution for forensics)
#
# Both modes audit:
#   * TCP exposure of 5432 (must not be reachable from the internet;
#     ideally bound to 127.0.0.1 or the internal docker network only)
#   * pg_hba.conf trust/ident lines and wide-open host rules
#   * default/weak POSTGRES_PASSWORD in container environments
#
# Environment:
#   DRY_RUN=1                  preview only.
#   PG_APPLY=1                 actually apply ALTER SYSTEM (native only).
#   DATABASE_URL=...           connection to use (native only).
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

step "PostgreSQL hardening / exposure audit"

PSQL=""
if command_exists psql; then
    PSQL="psql"
fi

# Where is postgres running?
native=false
container=false
if systemctl is-active --quiet postgresql 2>/dev/null; then
    native=true
fi
if command_exists docker && docker ps --format '{{.Image}} {{.Names}}' 2>/dev/null | grep -qi 'postgres'; then
    container=true
fi

if [[ "${native}" == "true" ]]; then
    ok "Native PostgreSQL service detected."
elif [[ "${container}" == "true" ]]; then
    ok "Containerized PostgreSQL detected."
else
    warn "No running PostgreSQL detected on this host (native or container)."
    warn "If the database lives elsewhere, run this script on that host instead."
fi

# ---- exposure audit: 5432 listening sockets ------------------------
step "Checking TCP exposure of port 5432"
listeners="$(ss -lntpH '( sport = :5432 )' 2>/dev/null || true)"
if [[ -z "${listeners}" ]]; then
    skip "Nothing listening on 5432 on this host."
else
    printf '%s\n' "${listeners}" | sed 's/^/        | /'
    if grep -qE '0\.0\.0\.0:5432|\[::\]:5432|\*:5432' <<< "${listeners}"; then
        fail "PostgreSQL is listening on ALL interfaces. Restrict it:"
        fail "  native:      listen_addresses = '127.0.0.1' in postgresql.conf"
        fail "  container:   remove 'ports:' from the db service (web reaches it"
        fail "               over the internal compose network) or bind 127.0.0.1:5432:5432"
        fail "  firewall:    ufw deny 5432/tcp  (UFW should already block it, but"
        fail "               defence in depth means the socket should not be open)"
    elif grep -qE '127\.0\.0\.1:5432|\[::1\]:5432' <<< "${listeners}"; then
        ok "PostgreSQL bound to loopback only."
    else
        warn "PostgreSQL bound to a specific interface — verify it is the internal one."
    fi
fi

# ---- pg_hba audit --------------------------------------------------
step "Auditing pg_hba.conf"
find_pg_hba() {
    local f
    for f in /etc/postgresql/*/main/pg_hba.conf /var/lib/pgsql/data/pg_hba.conf; do
        [[ -f "${f}" ]] && { echo "${f}"; return 0; }
    done
    if [[ "${container}" == "true" ]]; then
        local cid
        cid="$(docker ps --format '{{.ID}} {{.Image}}' | awk 'tolower($2) ~ /postgres/ {print $1; exit}')"
        if [[ -n "${cid}" ]]; then
            docker exec "${cid}" sh -c 'ls /var/lib/postgresql/data/pg_hba.conf /var/lib/postgresql/*/pg_hba.conf 2>/dev/null | head -1' 2>/dev/null || true
        fi
    fi
    return 1
}

if pg_hba="$(find_pg_hba)"; then
    log "pg_hba.conf: ${pg_hba}"
    hba_content="$(cat "${pg_hba}" 2>/dev/null || docker exec "$(docker ps --format '{{.ID}} {{.Image}}' | awk 'tolower($2) ~ /postgres/ {print $1; exit}')" cat "${pg_hba}" 2>/dev/null || true)"
    bad_lines="$(printf '%s\n' "${hba_content}" | grep -vE '^\s*#|^\s*$' | grep -E '\btrust\b|\bident\b|0\.0\.0\.0/0|::/0' || true)"
    if [[ -n "${bad_lines}" ]]; then
        fail "Risky pg_hba lines found:"
        printf '%s\n' "${bad_lines}" | sed 's/^/        | /'
        fail "Replace trust/ident with scram-sha-256 and narrow the source addresses."
    else
        ok "No trust/ident/wide-open rules in pg_hba.conf."
    fi
else
    skip "pg_hba.conf not found from this host."
fi

# ---- native hardening via ALTER SYSTEM -----------------------------
if [[ "${native}" == "true" && -n "${PSQL}" ]]; then
    step "Native PostgreSQL settings"
    run_as_postgres() {
        if [[ "${DRY_RUN}" == "1" ]]; then
            log "DRY-RUN: sudo -u postgres psql -c \"$1\""
        else
            sudo -u postgres psql -v ON_ERROR_STOP=1 -c "$1"
        fi
    }

    if [[ "${PG_APPLY:-0}" == "1" ]]; then
        run_as_postgres "ALTER SYSTEM SET password_encryption = 'scram-sha-256';"
        run_as_postgres "ALTER SYSTEM SET log_connections = on;"
        run_as_postgres "ALTER SYSTEM SET log_disconnections = on;"
        run_as_postgres "ALTER SYSTEM SET log_min_duration_statement = 1000;"
        run_as_postgres "ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d/%a ';"
        if [[ -f /var/lib/postgresql/server.crt || -f /etc/ssl/certs/ssl-cert-snakeoil.pem ]]; then
            run_as_postgres "ALTER SYSTEM SET ssl = on;"
        else
            warn "No server certificate found — skipping ssl=on. Create one (e.g. certbot or snakeoil) then re-run."
        fi
        run_as_postgres "SELECT pg_reload_conf();"
        ok "Settings applied via ALTER SYSTEM (see postgresql.auto.conf)."
        log "Re-hash existing passwords to scram: each role must RE-SET its password (or run an offline rehash)."
    else
        skip "PG_APPLY=1 not set — settings NOT changed. Recommended SQL:"
        cat <<'EOF'
        | ALTER SYSTEM SET password_encryption = 'scram-sha-256';
        | ALTER SYSTEM SET log_connections = on;
        | ALTER SYSTEM SET log_disconnections = on;
        | ALTER SYSTEM SET log_min_duration_statement = 1000;
        | ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d/%a ';
        | ALTER SYSTEM SET ssl = on;   -- when certificates exist
        | SELECT pg_reload_conf();
        | -- then re-SET each role password so hashes move to scram-sha-256
EOF
    fi
elif [[ "${container}" == "true" ]]; then
    step "Containerized PostgreSQL — recommended compose settings"
    cat <<'EOF'
        | # in the db service of your production compose file:
        |   environment:
        |     POSTGRES_HOST_AUTH_METHOD: scram-sha-256   # refuse md5/trust
        |   command: >
        |     postgres
        |       -c password_encryption=scram-sha-256
        |       -c log_connections=on
        |       -c log_disconnections=on
        |       -c log_min_duration_statement=1000
        |   # no 'ports:' section — the web container reaches db over the
        |   # internal compose network; nothing else needs 5432.
EOF
fi

# ---- weak container password --------------------------------------
if [[ "${container}" == "true" ]] && command_exists docker; then
    step "Checking container database credentials"
    weak="$(docker ps --format '{{.ID}}' | xargs -r docker inspect \
        --format '{{range .Config.Env}}{{println .}}{{end}}' \
        | grep -E '^POSTGRES_PASSWORD=' | sort -u | grep -E 'development-only|password|postgres|changeme|secret' || true)"
    if [[ -n "${weak}" ]]; then
        fail "Weak/default POSTGRES_PASSWORD detected in container environment variables."
        fail "Set a strong POSTGRES_PASSWORD via .env (never commit it) and rotate the role password."
    else
        ok "No obvious default database passwords in container env."
    fi
fi

step "Summary"
log "Exposure audit complete. The database must never be reachable from the internet."
log "Backups: follow docs/operations/BACKUP_AND_RECOVERY.md — pg_dump + JSON backup, stored OFF this host and encrypted."
