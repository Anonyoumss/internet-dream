#!/usr/bin/env bash
# Install & run the Internet's Dream Linux desktop client.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/python dream_desktop.py
