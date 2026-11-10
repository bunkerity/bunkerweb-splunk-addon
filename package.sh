#!/usr/bin/env bash
# Build the Splunkbase package: dist/TA-bunkerweb-<version>.tgz
# The archive holds one top-level directory, TA-bunkerweb/, owned by root, no hidden files.
set -euo pipefail

cd "$(dirname "$0")"
app=TA-bunkerweb
version=$(sed -n 's/^version[[:space:]]*=[[:space:]]*//p' "$app/default/app.conf" | head -n1)
[ -n "$version" ] || { echo "no version in $app/default/app.conf" >&2; exit 1; }

# The repository LICENSE is the single source; the app carries a copy.
mkdir -p "$app/LICENSES"
cp LICENSE "$app/LICENSES/LICENSE"

mkdir -p dist
out="dist/$app-$version.tgz"
tar --sort=name --owner=0 --group=0 --numeric-owner \
    --mode='u=rwX,go=rX' --mtime='2026-01-01 00:00:00 UTC' \
    --exclude='.*' --exclude='__pycache__' --exclude='local' --exclude='local.meta' \
    -czf "$out" "$app"
echo "$out"
