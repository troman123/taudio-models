# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from taudio_models.paths import resolve_models_root


def repo_root_from(start: Optional[Path] = None) -> Path:
    """
    Find a checkout root by walking up until manifest.yaml is found.

    Prefer ``resolve_models_root()`` for runtime; this helper remains for
    scripts that must locate a git working tree from an arbitrary start path.
    """
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "manifest.yaml").is_file():
            return p
    raise FileNotFoundError("manifest.yaml not found from %s" % cur)


def load_manifest(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load manifest.yaml. If path is a directory, use <dir>/manifest.yaml."""
    if path is None:
        path = resolve_models_root() / "manifest.yaml"
    else:
        path = Path(path)
        if path.is_dir():
            path = path / "manifest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping: %s" % path)
    # Normalize legacy keys
    if "catalog" not in data and isinstance(data.get("engines"), dict):
        data["catalog"] = data["engines"]
    if "weights" not in data and isinstance(data.get("models"), dict):
        data["weights"] = data["models"]
    data.setdefault("catalog", {})
    data.setdefault("weights", {})
    data.setdefault("assets", {})
    data.setdefault("capabilities", {})
    data["_manifest_path"] = str(path.resolve())
    return data


def get_weight(manifest: Dict[str, Any], weight_id: str) -> Dict[str, Any]:
    weights = manifest.get("weights") or manifest.get("models") or {}
    if weight_id not in weights:
        raise KeyError("weight id not in manifest: %s" % weight_id)
    entry = weights[weight_id]
    if not isinstance(entry, dict):
        raise ValueError("weight entry must be a mapping: %s" % weight_id)
    return entry


# Back-compat name used by cache.ensure_model
def get_model(manifest: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    return get_weight(manifest, model_id)
