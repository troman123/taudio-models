from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from taudio_engines.api.registry import open_registry
from taudio_engines.cache import cache_root, ensure_model
from taudio_engines.manifest import load_manifest, repo_root_from


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="taudio-engines-fetch",
        description="List engines / download weights (weights never in git).",
    )
    parser.add_argument("--repo", type=Path, default=None, help="taudio-engines repo root")
    parser.add_argument("--list", action="store_true", help="List weight ids in models:")
    parser.add_argument("--list-engines", action="store_true", help="List callable engines + params")
    parser.add_argument("--json", action="store_true", help="JSON output for --list-engines")
    parser.add_argument("--model", type=str, default=None, help="Download one weight id")
    parser.add_argument("--all", action="store_true", help="Download all weights")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args(argv)

    try:
        root = Path(args.repo).resolve() if args.repo else repo_root_from()
    except Exception as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    if args.list_engines:
        reg = open_registry(root)
        infos = [m.to_dict() for m in reg.list_models(include_planned=True)]
        if args.json:
            print(json.dumps(infos, indent=2, ensure_ascii=False))
        else:
            for m in infos:
                print(
                    "%s  status=%s  caps=%s  params=%s"
                    % (
                        m["id"],
                        m["status"],
                        ",".join(m["capabilities"]) or "-",
                        ",".join(p["name"] for p in m["params"]) or "-",
                    )
                )
        return 0

    try:
        manifest = load_manifest(root / "manifest.yaml")
    except Exception as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    models = manifest.get("models") or {}
    print("cache_root: %s" % cache_root())

    if args.list or (not args.model and not args.all):
        if not models:
            print("models: (none registered yet)")
        else:
            print("models:")
            for mid, entry in models.items():
                urls = entry.get("urls") or []
                print(
                    "  - %s  cache_key=%s  urls=%d"
                    % (mid, entry.get("cache_key", mid), len(urls))
                )
        if not args.model and not args.all:
            return 0

    targets = list(models.keys()) if args.all else ([args.model] if args.model else [])
    if not targets:
        print("error: no models to fetch", file=sys.stderr)
        return 2

    for mid in targets:
        try:
            path = ensure_model(manifest, mid, force=args.force)
            print("ok %s -> %s" % (mid, path))
        except Exception as e:
            print("fail %s: %s" % (mid, e), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
