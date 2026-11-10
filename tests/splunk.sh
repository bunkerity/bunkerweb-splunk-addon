#!/usr/bin/env bash
# Start or stop the throwaway Splunk Enterprise container used by tests/run.sh.
#   tests/splunk.sh up     start splta-splunk, wait for bootstrap and the management API
#   tests/splunk.sh down   remove it and shred the generated admin password
#
# The Splunk terms flags below accept the Splunk licence and general terms for this local,
# throwaway container only. They are not accepted for anything else.
set -euo pipefail

# shellcheck source=tests/lib.sh
. "$(dirname "$0")/lib.sh"

IMAGE="splunk/splunk:10.2.9@sha256:dced648eaaa403d8aee927d629f8e4708e5880d56753a41764094024d6ccd7e8"
WEB_PORT=${SPLTA_WEB_PORT:-19000}

up() {
  if docker inspect "$NAME" >/dev/null 2>&1; then
    echo "$NAME already exists" >&2
    sp_wait
    return
  fi
  free_mb=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
  if [ "$free_mb" -lt 5000 ]; then
    echo "only ${free_mb} MiB available, Splunk needs about 4 GiB: refusing to start" >&2
    exit 1
  fi
  if [ ! -s "$PASSFILE" ]; then
    (umask 077; head -c 24 /dev/urandom | base64 | tr -d '/+=' > "$PASSFILE")
  fi
  envfile=$(mktemp); chmod 600 "$envfile"
  printf 'SPLUNK_PASSWORD=%s\n' "$(cat "$PASSFILE")" > "$envfile"
  docker run -d --name "$NAME" --memory 4g --memory-swap 4g \
    -p "127.0.0.1:${MGMT_PORT}:8089" -p "127.0.0.1:${WEB_PORT}:8000" \
    --env-file "$envfile" \
    -e SPLUNK_START_ARGS=--accept-license \
    -e SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com \
    "$IMAGE" >/dev/null
  shred -u -z -n 3 -- "$envfile"
  echo "waiting for Splunk (a cold start takes 2 to 4 minutes) ..."
  if sp_wait; then
    echo "Splunk is up"
    return 0
  fi
  docker logs --tail 30 "$NAME" >&2 || true
  exit 1
}

down() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  [ -f "$PASSFILE" ] && shred -u -z -n 3 -- "$PASSFILE"
  return 0
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
