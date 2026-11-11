#!/usr/bin/env bash
# Install & run the Internet's Dream Linux desktop client.
# Installs PyQt6 AND the full dreamcore engine with all source extras
# (Google APIs + Telethon userbot) so `dream` CLI works from the bundle.
set -euo pipefail
cd "$(dirname "$0")"
CORE_DIR="../core"
[ -d "$CORE_DIR" ] || CORE_DIR="core"   # works both in-repo and in tarball

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
if [ -f "$CORE_DIR/pyproject.toml" ]; then
  # full extras: google APIs + telethon userbot (+ fall back to base if offline)
  .venv/bin/pip install -q -e "$CORE_DIR[google,telegram]" || \
    .venv/bin/pip install -q -e "$CORE_DIR"
fi
echo "dreamcore installed — 'dream' CLI available at .venv/bin/dream"
exec .venv/bin/python dream_desktop.py
