# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from taudio_models.api.registry import open_registry
from taudio_models.cache import cache_root, ensure_model
from taudio_models.manifest import load_manifest
from taudio_models.paths import resolve_models_root
from taudio_models.registry import PublicAssetRegistry, open_capability_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="taudio-models-fetch",
        description="List catalog / assets / capabilities / download weights.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Models root containing manifest.yaml (default: auto-resolve)",
    )
    parser.add_argument("--list", action="store_true", help="List weight ids in weights:")
    parser.add_argument(
        "--list-engines",
        "--list-catalog",
        action="store_true",
        dest="list_catalog",
        help="List catalog models + ModelParams",
    )
    parser.add_argument(
        "--list-assets",
        action="store_true",
        help="List public assets",
    )
    parser.add_argument(
        "--list-capabilities",
        action="store_true",
        help="List public capabilities",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--model", type=str, default=None, help="Download one weight id")
    parser.add_argument("--all", action="store_true", help="Download all weights")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args(argv)

    try:
        root = resolve_models_root(args.repo)
    except FileNotFoundError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    if args.list_assets:
        assets = PublicAssetRegistry(root).list_assets()
        data = [a.to_dict() for a in assets]
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            for a in data:
                print(
                    "%s  upstream=%s  lib=%s"
                    % (a["id"], a["upstream_ref"], a["lib"])
                )
        return 0

    if args.list_capabilities:
        caps = open_capability_registry(root).list_capabilities()
        data = [c.to_dict() for c in caps]
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            for c in data:
                print(
                    "%s  default_asset=%s  kind=%s  run_file=%s"
                    % (
                        c["id"],
                        c["default_asset_id"],
                        c["kind"] or "-",
                        c["has_run_file"],
                    )
                )
        return 0

    if args.list_catalog:
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

    models = manifest.get("weights") or manifest.get("models") or {}
    print("cache_root: %s" % cache_root())

    if args.list or (not args.model and not args.all):
        if not models:
            print("weights: (none with urls; DeepFilterNet uses upstream download)")
        else:
            print("weights:")
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
