# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CLI: denoise a file via public capability denoise.speech."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from taudio_models.paths import resolve_models_root
from taudio_models.registry import open_capability_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="taudio-models-denoise",
        description=(
            "Speech denoise via public capability denoise.speech. "
            "Install runtime with: pip install 'taudio-models[denoise]'"
        ),
    )
    parser.add_argument("input", type=Path, help="Noisy audio file")
    parser.add_argument("-o", "--output-dir", type=Path, required=True, help="Output directory")
    parser.add_argument(
        "--asset",
        default="deepfilternet3",
        choices=("deepfilternet", "deepfilternet2", "deepfilternet3"),
        help="Public asset id (default: deepfilternet3)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Models root containing manifest.yaml (default: auto-resolve)",
    )
    parser.add_argument("--pf", action="store_true", help="Enable DeepFilterNet post-filter")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print("error: input not found: %s" % args.input, file=sys.stderr)
        return 2

    try:
        root = resolve_models_root(args.repo)
    except FileNotFoundError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    try:
        caps = open_capability_registry(root)
        outs = caps.run_file(
            "denoise.speech",
            args.input,
            args.output_dir,
            asset_id=args.asset,
            params={"pf": bool(args.pf), "is_gpu": False, "log_level": "ERROR"},
        )
    except ImportError as e:
        print("error: %s" % e, file=sys.stderr)
        print("hint: pip install 'taudio-models[denoise]'", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 — surface runtime errors to CLI users
        print("error: %s" % e, file=sys.stderr)
        return 1

    for p in outs:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
