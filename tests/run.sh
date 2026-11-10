#!/usr/bin/env bash
# End-to-end test of TA-bunkerweb on a pinned Splunk Enterprise container.
#
#   tests/run.sh            start Splunk, package and install the app, ingest samples/,
#                           assert the fields, tear Splunk down again
#   tests/run.sh --keep     leave the container running (tests/splunk.sh down removes it)
#   SPLTA_SABOTAGE=1 tests/run.sh
#                           break one extraction in the packaged copy first; the run must fail
#
# Exit code 0 only when every assertion passes. The test talks to Splunk on 127.0.0.1 with its
# self-signed certificate, so tests/test_ta.py does not verify TLS.
set -euo pipefail

cd "$(dirname "$0")/.."
# shellcheck source=tests/lib.sh
. tests/lib.sh

keep=0
[ "${1:-}" = "--keep" ] && keep=1

started=0
if ! docker inspect "$NAME" >/dev/null 2>&1; then
  tests/splunk.sh up
  started=1
fi
cleanup() {
  if [ "$started" = 1 ] && [ "$keep" = 0 ]; then
    tests/splunk.sh down
  fi
}
trap cleanup EXIT
sp_wait

pkg=$(./package.sh)
if [ "${SPLTA_SABOTAGE:-0}" = 1 ]; then
  # Rename the uri_path extraction in the packaged copy: the URI assertions must catch it.
  work=$(mktemp -d)
  tar -xzf "$pkg" -C "$work"
  sed -i 's/(?<uri_path>\[^?"\]\*)/(?<uri_pathx>[^?"]*)/' "$work/TA-bunkerweb/default/props.conf"
  pkg="$work/sabotaged.tgz"
  tar -czf "$pkg" -C "$work" TA-bunkerweb
  echo "sabotage: uri_path extraction renamed in the installed copy"
fi

echo "installing $pkg"
sp_install "$pkg"

index="bw_test_$(date +%s)"
sp_post "$BASE/services/data/indexes" -d "name=$index"
sp_ingest "$index" bunkerweb:access samples/access.log
sp_ingest "$index" bunkerweb:access samples/access_adversarial.log
sp_ingest "$index" bunkerweb:error samples/error.log
sp_ingest "$index" bunkerweb:error samples/error_adversarial.log
sp_ingest "$index" bunkerweb:modsec_audit samples/modsec_audit.log

# Wait until captured and synthetic samples are searchable.
want=$(( $(grep -c . samples/access.log) + $(grep -c . samples/access_adversarial.log) + $(grep -c . samples/error.log) + $(grep -c . samples/error_adversarial.log) + $(grep -c . samples/modsec_audit.log) ))
for _ in $(seq 1 60); do
  got=$(sp_curl "$BASE/services/search/jobs/export" --data-urlencode "search=search index=$index | stats count" \
        -d earliest_time=0 -d output_mode=csv | tail -n1 | tr -d '"\r')
  [ "$got" = "$want" ] && break
  sleep 2
done
echo "indexed $got of $want events into $index"

SPLTA_INDEX="$index" SPLTA_PASSFILE="$PASSFILE" SPLTA_URL="$BASE" python3 -I tests/test_ta.py
