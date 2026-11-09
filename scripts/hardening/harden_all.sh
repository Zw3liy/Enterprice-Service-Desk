#!/usr/bin/env bash
# -------------------------------------------------------------------
# harden_all.sh — run every hardening script in a safe order, then
# score the result with the posture audit.
#
#   sudo ./harden_all.sh              apply everything
#   sudo DRY_RUN=1 ./harden_all.sh    preview everything
#
# Order matters:
#   1. SSH first (lock down access), but the firewall comes right
#      after so the management allow-rule is in place before UFW
#      enables. 2-5 then the host platform, 6-7 the services, and the
#      audit last so it grades the finished state.
#
# A failure in one step is reported but does NOT stop the rest — the
# summary at the end shows what to fix and re-run.
# -------------------------------------------------------------------

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

declare -a STEPS=(
    harden_ssh.sh
    harden_firewall.sh
    harden_kernel.sh
    harden_updates.sh
    harden_login.sh
    harden_fail2ban.sh
    harden_auditd.sh
    harden_monitoring.sh
    harden_docker.sh
    harden_postgres.sh
    harden_edge.sh
)

declare -a RESULTS=()
overall=0

for step_script in "${STEPS[@]}"; do
    printf '\n\033[1m########## %s ##########\033[0m\n' "${step_script}"
    if bash "${SCRIPT_DIR}/${step_script}"; then
        RESULTS+=("OK    ${step_script}")
    else
        rc=$?
        RESULTS+=("FAIL(${rc}) ${step_script}")
        overall=1
    fi
done

printf '\n\033[1m########## posture audit ##########\033[0m\n'
if bash "${SCRIPT_DIR}/audit_hardening.sh" --quick; then
    RESULTS+=("OK    audit_hardening.sh")
else
    RESULTS+=("FAIL  audit_hardening.sh (findings above)")
    overall=1
fi

printf '\n==============================================================\n'
printf ' HARDENING RUN SUMMARY\n'
printf '==============================================================\n'
for line in "${RESULTS[@]}"; do
    printf ' %s\n' "${line}"
done
printf '==============================================================\n'
exit "${overall}"
