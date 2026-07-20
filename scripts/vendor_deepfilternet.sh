#!/usr/bin/env bash
# Vendor DeepFilterNet Python tree into libs/DeepFilterNet (run on a machine with space).
# Does NOT commit platform .so files.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/libs/DeepFilterNet"
SRC="${1:-}"

if [[ -z "$SRC" ]]; then
  echo "Usage: $0 /path/to/audioprocessPython/DeepFilterNet"
  echo "  or:  $0 /path/to/cloned/Rikorose/DeepFilterNet"
  exit 1
fi

if [[ ! -d "$SRC/df" ]]; then
  echo "error: expected $SRC/df" >&2
  exit 1
fi

mkdir -p "$DEST"
rsync -a --delete \
  --exclude '.DS_Store' \
  --exclude '__pycache__' \
  --exclude '*.so' \
  --exclude '*.dylib' \
  --exclude '*.pyd' \
  "$SRC/" "$DEST/"

mkdir -p "$ROOT/licenses/deepfilternet"
if [[ -f "$SRC/LICENSE" ]]; then
  cp "$SRC/LICENSE" "$ROOT/licenses/deepfilternet/LICENSE"
elif [[ ! -f "$ROOT/licenses/deepfilternet/LICENSE" ]]; then
  curl -fsSL -o "$ROOT/licenses/deepfilternet/LICENSE" \
    https://raw.githubusercontent.com/Rikorose/DeepFilterNet/main/LICENSE || true
fi

cat > "$DEST/README.md" <<'EOF'
# DeepFilterNet (vendored)

Python sources vendored for taudio-models. Native `libdf` must match the host
platform (build from upstream or install a wheel). `*.so` / `*.dylib` are not
committed.

Weights download at runtime via upstream `maybe_download_model` (not in git).
EOF

echo "Vendored DeepFilterNet -> $DEST"
echo "Next: install/build libdf for your platform, then run denoise smoke on test env."
