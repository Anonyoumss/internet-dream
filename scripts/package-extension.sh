#!/usr/bin/env bash
# Package the browser extension as a zip for Chrome/Firefox (MV3).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="dist/internet-dream-extension.zip"
mkdir -p dist
rm -f "$OUT"
cd extension
zip -qr "../$OUT" . -x "*.md"
echo "built $OUT"
