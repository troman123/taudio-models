#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[bootstrap] repo=$ROOT"
python3 -m pip install -e . -q
python3 scripts/check_layout.py
python3 scripts/check_licenses.py || true
echo "[bootstrap] cache_root tip: export TAUDIO_MODEL_CACHE=... then taudio-engines-fetch --list"
echo "[bootstrap] done (models are downloaded on demand; not stored in git)"
