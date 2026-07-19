#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest_path = ROOT / "manifest.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    engines = data.get("engines") or {}
    errors = []
    for name, eng in engines.items():
        if eng.get("status") == "planned":
            continue
        lf = eng.get("license_file")
        if not lf:
            errors.append("%s: missing license_file" % name)
            continue
        if not (ROOT / lf).is_file():
            errors.append("%s: license_file not found: %s" % (name, lf))
        if not eng.get("license_spdx"):
            errors.append("%s: missing license_spdx" % name)
    if errors:
        print("license check failed:", file=sys.stderr)
        for e in errors:
            print(" ", e, file=sys.stderr)
        return 1
    print("license check ok (planned engines skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
