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
set -uo pipefail

QUIET=0
case "${1:-}" in
  --quiet) QUIET=1 ;;
  -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
  "") ;;
  *) echo "unknown arg: $1" >&2; exit 2 ;;
esac

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

out=$( { audit_scope "" "system"; [ -n "${XDG_RUNTIME_DIR:-}" ] && audit_scope "--user" "user"; } 2>/dev/null )

checked=$(printf '%s\n' "$out" | grep -c '^COUNT$' || true)
while IFS='|' read -r kind label unit detail; do
  case "$kind" in
    EXPOSED)   exposed=$((exposed+1));   [ "$QUIET" -eq 0 ] && printf '  ! %-7s %-38s %s\n' "$label" "$unit" "$detail" ;;
    MITIGATED) mitigated=$((mitigated+1)); [ "$QUIET" -eq 0 ] && printf '  ~ %-7s %-38s %s\n' "$label" "$unit" "$detail" ;;
  esac
done < <(printf '%s\n' "$out" | grep -E '^(EXPOSED|MITIGATED)\|' || true)

printf '%s: checked=%d exposed=%d mitigated=%d\n' "$(hostname)" "$checked" "$exposed" "$mitigated"
[ "$exposed" -eq 0 ]
