#!/usr/bin/env bash
# Build an installable Kodi zip for the Sunday TV add-on.
#
#   ./scripts/package_addon.sh            # -> dist/plugin.video.sundaytv-<version>.zip
#
# The zip's top-level folder is the add-on id (Kodi requires this).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDON_ID="plugin.video.sundaytv"
ADDON_DIR="$ROOT/addon/$ADDON_ID"
DIST="$ROOT/dist"

if [[ ! -f "$ADDON_DIR/addon.xml" ]]; then
    echo "error: $ADDON_DIR/addon.xml not found" >&2
    exit 1
fi

# Pull the version out of addon.xml (the first version="x.y.z" on the <addon ...> line).
VERSION="$(grep -m1 -oE 'version="[0-9]+\.[0-9]+\.[0-9]+"' "$ADDON_DIR/addon.xml" | head -1 | cut -d'"' -f2)"
VERSION="${VERSION:-0.0.0}"

mkdir -p "$DIST"
ZIP="$DIST/${ADDON_ID}-${VERSION}.zip"
rm -f "$ZIP"

# Stage into a temp dir so the archive contains a single top-level <addon_id>/ folder and
# excludes caches/local data.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/$ADDON_ID"

# Copy the add-on, excluding python caches and any runtime profile data.
( cd "$ADDON_DIR" && \
  find . \
    -path './resources/data' -prune -o \
    -name '__pycache__' -prune -o \
    -name '*.pyc' -prune -o \
    -type f -print ) | while read -r f; do
    dest="$STAGE/$ADDON_ID/${f#./}"
    mkdir -p "$(dirname "$dest")"
    cp "$ADDON_DIR/$f" "$dest"
done

( cd "$STAGE" && zip -r -q "$ZIP" "$ADDON_ID" )

echo "Built $ZIP"
