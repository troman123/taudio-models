# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Resolve where taudio-models data (manifest.yaml) lives."""

from __future__ import annotations

import os
from pathlib import Path


def bundled_manifest_dir() -> Path:
    """Directory containing the packaged manifest.yaml (inside the wheel)."""
    return Path(__file__).resolve().parent / "resources"


def resolve_models_root(explicit: Path | str | None = None) -> Path:
    """
    Resolve the models root directory (must contain manifest.yaml).

    Order:
      1. explicit argument
      2. $TAUDIO_MODELS_ROOT
      3. walk upward from cwd for a checkout (manifest.yaml)
      4. packaged resources/ shipped with the wheel

    This lets both ``pip install`` users and git checkouts work without
    guessing.
    """
    if explicit is not None:
        root = Path(explicit).expanduser().resolve()
        _require_manifest(root, "explicit path")
        return root

    env = os.environ.get("TAUDIO_MODELS_ROOT", "").strip()
    if env:
        root = Path(env).expanduser().resolve()
        _require_manifest(root, "TAUDIO_MODELS_ROOT")
        return root

    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / "manifest.yaml").is_file():
            return p

    bundled = bundled_manifest_dir()
    if (bundled / "manifest.yaml").is_file():
        return bundled

    raise FileNotFoundError(
        "Could not find manifest.yaml. Do one of:\n"
        "  - export TAUDIO_MODELS_ROOT=/path/to/taudio-models\n"
        "  - run from a git checkout of taudio-models\n"
        "  - pip install taudio-models (ships a bundled manifest)\n"
        "Started from cwd=%s" % cwd
    )


def _require_manifest(root: Path, label: str) -> None:
    if not (root / "manifest.yaml").is_file():
        raise FileNotFoundError(
            "%s=%s does not contain manifest.yaml" % (label, root)
        )
