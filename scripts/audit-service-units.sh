#!/usr/bin/env bash
# audit-service-units.sh - validator for SERVICE_UNIT_STANDARD.md
#
# Flags every enabled service unit where systemd's start limiter can NEVER
# engage AND no backoff is configured, i.e. a permanently-broken unit would
# retry forever at a fixed interval.
#
# The rule (see standards/SERVICE_UNIT_STANDARD.md §1):
#     RestartSec x (StartLimitBurst - 1)  MUST BE  <  StartLimitIntervalSec
# Defaults Burst=5 / Interval=10s mean any RestartSec >= 2.5s disables the
# limiter silently. Backoff (RestartSteps>0, systemd 254+) is accepted as a
# mitigation because it caps the storm even when the limiter never fires.
#
# Exit: 0 = clean, 1 = exposed units found, 2 = usage/environment error.
#
# Usage:
#   ./audit-service-units.sh              # this host, both scopes
#   ./audit-service-units.sh --quiet      # only the summary line
#   ./audit-service-units.sh --system-only # node genuinely has no user scope
set -uo pipefail

QUIET=0; SYSTEM_ONLY=0
for a in "$@"; do
  case "$a" in
    --quiet) QUIET=1 ;;
    --system-only) SYSTEM_ONLY=1 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    "") ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

command -v systemctl >/dev/null 2>&1 || { echo "systemctl not found" >&2; exit 2; }

exposed=0; mitigated=0; checked=0

# systemd reports times either as raw microseconds or as "1s 500ms"/"5min".
to_secs() {
  local s="${1:-}"
  case "$s" in
    ""|infinity) echo 0; return ;;
    *[!0-9]*) ;;
    *) echo $(( s / 1000000 )); return ;;   # raw microseconds
  esac
  awk -v s="$s" 'BEGIN{
    t=0; n="";
    while (match(s, /[0-9.]+(us|ms|min|s|h)/)) {
      tok=substr(s, RSTART, RLENGTH); s=substr(s, RSTART+RLENGTH)
      if (match(tok,/us$/))      { u=1e-6; v=substr(tok,1,length(tok)-2) }
      else if (match(tok,/ms$/)) { u=1e-3; v=substr(tok,1,length(tok)-2) }
      else if (match(tok,/min$/)){ u=60;   v=substr(tok,1,length(tok)-3) }
      else if (match(tok,/h$/))  { u=3600; v=substr(tok,1,length(tok)-1) }
      else                       { u=1;    v=substr(tok,1,length(tok)-1) }
      t += v*u
    }
    printf "%d", t
  }'
}

audit_scope() {
  local scope="$1" label="$2"
  systemctl $scope list-unit-files --no-pager --state=enabled 2>/dev/null \
    | awk '/\.service/{print $1}' \
    | while read -r u; do
        [ -z "$u" ] && continue
        local restart rs_raw li_raw burst steps rs li span
        restart=$(systemctl $scope show "$u" -p Restart --value 2>/dev/null)
        [ "${restart:-no}" = "no" ] && continue
        rs_raw=$(systemctl $scope show "$u" -p RestartUSec --value 2>/dev/null)
        li_raw=$(systemctl $scope show "$u" -p StartLimitIntervalUSec --value 2>/dev/null)
        burst=$(systemctl $scope show "$u" -p StartLimitBurst --value 2>/dev/null)
        steps=$(systemctl $scope show "$u" -p RestartSteps --value 2>/dev/null)
        rs=$(to_secs "$rs_raw"); li=$(to_secs "$li_raw")
        burst=${burst:-5}; steps=${steps:-0}
        echo "COUNT"
        [ "$li" -le 0 ] && continue
        [ "$burst" -le 1 ] && continue
        span=$(( rs * (burst - 1) ))
        if [ "$span" -ge "$li" ]; then
          if [ "$steps" -gt 0 ]; then
            echo "MITIGATED|$label|$u|RestartSec=${rs}s Burst=$burst Interval=${li}s (backoff set)"
          else
            echo "EXPOSED|$label|$u|RestartSec=${rs}s Burst=$burst Interval=${li}s span=${span}s >= ${li}s"
          fi
        fi
      done
}

# User scope is where most SK units live, so a run that cannot see it is NOT a
# clean run. cron/systemd start with no XDG_RUNTIME_DIR, so derive it; if it
# still is not reachable, say so loudly and fail rather than reporting green on
# a partial sweep. A check that silently narrows itself is worse than no check.
user_scope_ok=0
if [ -z "${XDG_RUNTIME_DIR:-}" ] && [ -d "/run/user/$(id -u)" ]; then
  export XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi
if [ -n "${XDG_RUNTIME_DIR:-}" ] && systemctl --user show-environment >/dev/null 2>&1; then
  user_scope_ok=1
fi

out=$( { audit_scope "" "system"; [ "$user_scope_ok" -eq 1 ] && audit_scope "--user" "user"; } 2>/dev/null )

checked=$(printf '%s\n' "$out" | grep -c '^COUNT$' || true)
while IFS='|' read -r kind label unit detail; do
  case "$kind" in
    EXPOSED)   exposed=$((exposed+1));   [ "$QUIET" -eq 0 ] && printf '  ! %-7s %-38s %s\n' "$label" "$unit" "$detail" ;;
    MITIGATED) mitigated=$((mitigated+1)); [ "$QUIET" -eq 0 ] && printf '  ~ %-7s %-38s %s\n' "$label" "$unit" "$detail" ;;
  esac
done < <(printf '%s\n' "$out" | grep -E '^(EXPOSED|MITIGATED)\|' || true)

if [ "$user_scope_ok" -eq 1 ]; then
  printf '%s: checked=%d exposed=%d mitigated=%d\n' "$(hostname)" "$checked" "$exposed" "$mitigated"
elif [ "$SYSTEM_ONLY" -eq 1 ]; then
  # Declared intent: this node has no user scope (hypervisor, appliance, root-only).
  printf '%s: checked=%d exposed=%d mitigated=%d SCOPE=system-only(declared)\n' "$(hostname)" "$checked" "$exposed" "$mitigated"
else
  printf '%s: checked=%d exposed=%d mitigated=%d SCOPE=system-only\n' "$(hostname)" "$checked" "$exposed" "$mitigated"
  printf 'WARN: user scope NOT audited (no reachable XDG_RUNTIME_DIR / user manager).\n' >&2
  printf 'WARN: most SK units are user units, so this result is PARTIAL, not clean.\n' >&2
  printf 'WARN: pass --system-only if this node genuinely has no user scope.\n' >&2
  exit 1
fi
[ "$exposed" -eq 0 ]
