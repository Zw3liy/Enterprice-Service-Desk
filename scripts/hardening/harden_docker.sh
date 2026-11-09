#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_docker.sh — Docker Engine daemon hardening.
#
# Merges security-relevant defaults into /etc/docker/daemon.json
# (existing keys are preserved; only these are set):
#
#   no-new-privileges : true    containers can never gain privileges
#                               via setuid binaries / sudo (default ON
#                               for every container).
#   live-restore      : true    daemon restarts/upgrades don't kill
#                               running containers.
#   log-driver        : json-file with rotation — an unbounded json.log
#                               is a disk-DoS and can leak secrets.
#
# Deliberately NOT set here (they break real deployments — see
# docs/operations/SERVER_HARDENING.md):
#   * "icc": false             breaks compose web -> db traffic.
#   * "userns-remap"           breaks volume ownership for most images.
#   * "userland-proxy": false  can break localhost hairpin access to
#                              published ports (NPM on the same host).
#
# Also reports container-level findings: privileged containers, docker
# socket mounts, published ports on 0.0.0.0, members of the docker
# group (root-equivalent).
#
# Environment:
#   DRY_RUN=1          preview only.
#   DOCKER_NO_RESTART=1  write config but do not restart docker
#                        (schedule the restart yourself; it blips
#                        container networking for ~1-2s even with
#                        live-restore).
# -------------------------------------------------------------------

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_root

step "Docker daemon hardening"

command_exists docker || die "docker not found on this host."
command_exists python3 || die "python3 is required to merge daemon.json safely."

DAEMON_JSON="/etc/docker/daemon.json"
mkdir -p /etc/docker

if [[ -f "${DAEMON_JSON}" ]]; then
    backup_file "${DAEMON_JSON}"
fi

merge_daemon_json() {
    python3 - "$DAEMON_JSON" <<'PY'
import json, sys, os

path = sys.argv[1]
config = {}
if os.path.exists(path):
    try:
        with open(path) as fh:
            config = json.load(fh) or {}
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: {path} is not valid JSON ({exc}). Fix it manually first.")

wanted = {
    "no-new-privileges": True,
    "live-restore": True,
    "log-driver": "json-file",
    "log-opts": {"max-size": "10m", "max-file": "3"},
}

changed = False
for key, value in wanted.items():
    if config.get(key) != value:
        note = f"  {key}: {json.dumps(config.get(key, '<unset>'))} -> {json.dumps(value)}"
        config[key] = value
        print(note)
        changed = True

if changed:
    with open(path, "w") as fh:
        json.dump(config, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("UPDATED")
else:
    print("UNCHANGED")
PY
}

if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would merge into ${DAEMON_JSON}:"
    merge_daemon_json >/dev/null 2>&1 || true
    log "  no-new-privileges=true, live-restore=true, json-file log rotation (10m x 3)"
else
    merge_out="$(merge_daemon_json)"
    if grep -q "UPDATED" <<< "${merge_out}"; then
        log "daemon.json updated:"
        grep -v "UPDATED" <<< "${merge_out}" | sed 's/^/        | /'
    else
        log "daemon.json already has the desired settings."
    fi
    chmod 0644 "${DAEMON_JSON}"
fi

step "Validating daemon.json"
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would validate JSON syntax"
else
    python3 -c "import json,sys; json.load(open('${DAEMON_JSON}'))" \
        || die "daemon.json is invalid JSON — docker will not start. Fix ${DAEMON_JSON}."
    ok "daemon.json is valid JSON."
fi

step "Reloading Docker"
if [[ "${DRY_RUN}" == "1" ]]; then
    log "DRY-RUN: would run: systemctl reload docker (or restart if reload unsupported)"
elif [[ "${DOCKER_NO_RESTART:-0}" == "1" ]]; then
    warn "DOCKER_NO_RESTART=1 — config written but NOT applied. Run: systemctl restart docker"
else
    if systemctl reload docker >/dev/null 2>&1; then
        ok "Docker reloaded."
    else
        warn "reload unsupported on this engine — restarting docker (brief container network blip)."
        systemctl restart docker
        ok "Docker restarted."
    fi
fi

step "Container-level audit (read-only findings)"
if docker info >/dev/null 2>&1; then
    # Privileged containers
    priv="$(docker ps -q | xargs -r docker inspect --format '{{.Name}} {{.HostConfig.Privileged}}' | awk '$2=="true"{print $1}' || true)"
    if [[ -n "${priv}" ]]; then
        fail "Privileged containers running: ${priv}"
    else
        ok "No privileged containers."
    fi

    # Docker socket mounts (root-equivalent)
    sock="$(docker ps -q | xargs -r docker inspect \
        --format '{{range .Mounts}}{{if eq .Source "/var/run/docker.sock"}}{{$.Name}} {{end}}{{end}}' \
        | tr -d ' ' | sort -u || true)"
    sock_filtered="$(grep -v '^/portainer$' <<< "${sock}" | grep -v '^$' || true)"
    if [[ -n "${sock_filtered}" ]]; then
        warn "Containers mounting the Docker socket (root-equivalent): ${sock_filtered}"
        warn "Only a container orchestrator (e.g. Portainer) should ever hold the socket."
    else
        ok "Docker socket only mounted where expected (or not at all)."
    fi

    # Published ports bound to all interfaces
    pub="$(docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E '0\.0\.0\.0:|:::' || true)"
    if [[ -n "${pub}" ]]; then
        warn "Containers publishing ports on ALL interfaces:"
        printf '%s\n' "${pub}" | sed 's/^/        | /'
        warn "Prefer 127.0.0.1:port bindings behind the tunnel/proxy, or internal networks."
    else
        ok "No container ports published on 0.0.0.0."
    fi

    # docker group membership = root-equivalent
    if getent group docker >/dev/null 2>&1; then
        members="$(getent group docker | cut -d: -f4)"
        if [[ -n "${members}" ]]; then
            warn "Members of the 'docker' group (root-equivalent): ${members}"
        else
            ok "'docker' group has no members (good — use sudo docker)."
        fi
    fi
else
    skip "docker daemon not reachable — container audit skipped."
fi

step "Summary"
log "Managed file: ${DAEMON_JSON} (keys tagged ${HARDENING_TAG} via this script's docs)."
log "Container-level hardening for this repo lives in compose.yaml / docker-compose.production.yml."
