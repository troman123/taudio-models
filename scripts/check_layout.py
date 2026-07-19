#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "LICENSE",
    "NOTICE",
    "README.md",
    "AGENTS.md",
    "manifest.yaml",
    "docs/model-cache.md",
    "docs/nonfree.md",
    "src/taudio_engines/cache.py",
    "src/taudio_engines/manifest.py",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        print("missing:", ", ".join(missing), file=sys.stderr)
        return 1
    # Refuse tracked-looking weight dirs committed by mistake
    bad_globs = list(ROOT.rglob("*.ckpt")) + list(ROOT.rglob("*.onnx")) + list(ROOT.rglob("*.pth"))
    bad = [p for p in bad_globs if ".git" not in p.parts and ".cache" not in p.parts]
    if bad:
        print("weight files must not live in the repo:", file=sys.stderr)
        for p in bad[:20]:
            print(" ", p, file=sys.stderr)
        return 1
    print("layout ok:", ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
