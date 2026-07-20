# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Easiest CLI: denoise a file via public capability denoise.speech."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from taudio_models.manifest import repo_root_from
from taudio_models.registry import open_capability_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="taudio-models-denoise",
        description="Speech denoise (public capability denoise.speech). "
        "Requires: pip install 'taudio-models[denoise]' or pip install deepfilternet",
    )
    parser.add_argument("input", type=Path, help="Noisy audio file")
    parser.add_argument("-o", "--output-dir", type=Path, required=True, help="Output directory")
    parser.add_argument(
        "--asset",
        default="deepfilternet3",
        help="Public asset id (deepfilternet / deepfilternet2 / deepfilternet3)",
    )
    parser.add_argument("--repo", type=Path, default=None, help="taudio-models repo root")
    parser.add_argument("--pf", action="store_true", help="Enable post-filter")
    args = parser.parse_args(argv)

    try:
        root = Path(args.repo).resolve() if args.repo else repo_root_from()
    except Exception:
        # installed package: fall back to cwd / env
        env = __import__("os").environ.get("TAUDIO_MODELS_ROOT", "").strip()
        root = Path(env).resolve() if env else Path.cwd()

    caps = open_capability_registry(root)
    outs = caps.run_file(
        "denoise.speech",
        args.input,
        args.output_dir,
        asset_id=args.asset,
        params={"pf": bool(args.pf), "is_gpu": False, "log_level": "ERROR"},
    )
    for p in outs:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
