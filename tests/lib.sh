# shellcheck shell=bash
# Helpers shared by tests/run.sh and tests/splunk.sh. Sourced, not executed.

NAME=${SPLTA_NAME:-splta-splunk}
MGMT_PORT=${SPLTA_MGMT_PORT:-19089}
# Password file lives outside the repository, mode 0600, and is shredded by `down`.
PASSFILE=${SPLTA_PASSFILE:-${XDG_RUNTIME_DIR:-/tmp}/splta-splunk.pass}
BASE="https://127.0.0.1:${MGMT_PORT}"

# curl against the management API without printing the password on the command line.
sp_curl() {
  curl -sk -m 120 --config <(printf 'user = "admin:%s"\n' "$(cat "$PASSFILE")") "$@"
}

sp_wait() {
  for _ in $(seq 1 120); do
    # The API can answer while the image's Ansible bootstrap is still configuring Splunk.
    if [ "$(docker inspect --format '{{.State.Health.Status}}' "$NAME" 2>/dev/null)" = healthy ] &&
        sp_curl -m 5 "$BASE/services/server/info?output_mode=json" 2>/dev/null | grep -q '"version"'; then
      return 0
    fi
    sleep 3
  done
  echo "Splunk did not become healthy with an authenticated management API" >&2
  return 1
}

# sp_post <url> <curl args...>: POST and retry while splunkd settles after a restart. 201 and 409
# (already there) count as done.
sp_post() {
  local url=$1 code
  shift
  for _ in $(seq 1 15); do
    code=$(sp_curl -o /dev/null -w '%{http_code}' "$url" "$@" || true)
    case "$code" in 200 | 201 | 409) return 0 ;; esac
    sleep 4
  done
  echo "POST $url failed (last HTTP code: $code)" >&2
  return 1
}

# sp_install <tgz>: install the package the way an admin would, then restart.
sp_install() {
  local tgz=$1
  docker cp "$tgz" "$NAME:/tmp/ta.tgz"
  docker exec -u root "$NAME" chmod 644 /tmp/ta.tgz
  # The POST can drop the connection while Splunk unpacks the app (curl exit 56), so the result
  # is read back from the app list instead of from the reply.
  sp_curl "$BASE/services/apps/local" -d name=/tmp/ta.tgz -d filename=true -d update=true -d output_mode=json >/dev/null || true
  local installed=0
  for _ in $(seq 1 30); do
    if sp_curl "$BASE/services/apps/local/TA-bunkerweb?output_mode=json" 2>/dev/null | grep -q '"BunkerWeb Add-on for Splunk"'; then
      installed=1
      break
    fi
    sleep 2
  done
  if [ "$installed" != 1 ]; then
    echo "app install failed: TA-bunkerweb is not in the app list" >&2
    return 1
  fi
  # The restart drops the connection (curl exit 56): ignore that, then wait for the port to go
  # down and come back, so a still-running old splunkd is not mistaken for the restarted one.
  sp_curl -X POST "$BASE/services/server/control/restart" >/dev/null || true
  for _ in $(seq 1 60); do
    sp_curl -m 3 "$BASE/services/server/info?output_mode=json" >/dev/null 2>&1 || break
    sleep 2
  done
  sleep 5
  sp_wait
}

# sp_ingest <index> <sourcetype> <file>: raw ingest through the receivers/simple endpoint,
# which runs the sourcetype's line breaking and timestamp settings like any other input.
sp_ingest() {
  local index=$1 sourcetype=$2 file=$3
  sp_post "$BASE/services/receivers/simple?index=$index&sourcetype=$sourcetype&source=$(basename "$file")&host=splta-test" \
    --data-binary "@$file"
}
