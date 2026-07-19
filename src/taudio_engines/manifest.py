from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def repo_root_from(start: Optional[Path] = None) -> Path:
    """Find repository root by walking up until manifest.yaml is found."""
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "manifest.yaml").is_file():
            return p
    raise FileNotFoundError("manifest.yaml not found from %s" % cur)


def load_manifest(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load manifest.yaml. If path is a directory, use <dir>/manifest.yaml."""
    if path is None:
        path = repo_root_from() / "manifest.yaml"
    else:
        path = Path(path)
        if path.is_dir():
            path = path / "manifest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping: %s" % path)
    data.setdefault("engines", {})
    data.setdefault("models", {})
    data["_manifest_path"] = str(path.resolve())
    return data


def get_model(manifest: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    models = manifest.get("models") or {}
    if model_id not in models:
        raise KeyError("model id not in manifest: %s" % model_id)
    entry = models[model_id]
    if not isinstance(entry, dict):
        raise ValueError("model entry must be a mapping: %s" % model_id)
    return entry
