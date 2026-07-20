# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public asset registry (open, generic names)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from taudio_models.manifest import load_manifest, repo_root_from


@dataclass(frozen=True)
class PublicAsset:
    """One downloadable / resolvable public asset."""

    id: str
    display_name: str
    lib: str
    upstream_ref: str
    download: str = "upstream"  # upstream | urls
    weight_ids: List[str] = field(default_factory=list)
    license_spdx: str = ""
    description: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "lib": self.lib,
            "upstream_ref": self.upstream_ref,
            "download": self.download,
            "weight_ids": list(self.weight_ids),
            "license_spdx": self.license_spdx,
            "description": self.description,
            "meta": dict(self.meta),
        }


def _assets_from_manifest(manifest: Dict[str, Any]) -> Dict[str, PublicAsset]:
    raw = manifest.get("assets") or {}
    out: Dict[str, PublicAsset] = {}
    if not isinstance(raw, dict):
        return out
    for aid, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        out[str(aid)] = PublicAsset(
            id=str(aid),
            display_name=str(entry.get("display_name") or aid),
            lib=str(entry.get("lib") or ""),
            upstream_ref=str(entry.get("upstream_ref") or ""),
            download=str(entry.get("download") or "upstream"),
            weight_ids=[str(x) for x in (entry.get("weight_ids") or [])],
            license_spdx=str(entry.get("license_spdx") or ""),
            description=str(entry.get("description") or ""),
            meta={k: v for k, v in entry.items() if k not in {
                "display_name", "lib", "upstream_ref", "download",
                "weight_ids", "license_spdx", "description",
            }},
        )
    return out


class PublicAssetRegistry:
    """
    Open-source public asset table.

    Generic stable ids (e.g. deepfilternet3). Does not use internal short names.
    """

    def __init__(self, models_root: Optional[Path] = None):
        self.root = Path(models_root).resolve() if models_root else repo_root_from()
        self.manifest = load_manifest(self.root / "manifest.yaml")
        self._assets = _assets_from_manifest(self.manifest)

    def list_assets(self) -> List[PublicAsset]:
        return [self._assets[k] for k in sorted(self._assets)]

    def get(self, asset_id: str) -> PublicAsset:
        key = str(asset_id).strip()
        if key not in self._assets:
            raise KeyError("unknown public asset: %s" % asset_id)
        return self._assets[key]

    def resolve_lib_path(self, asset_id: str) -> Path:
        asset = self.get(asset_id)
        if not asset.lib:
            raise ValueError("asset %s has empty lib" % asset_id)
        path = (self.root / asset.lib).resolve()
        return path

    def ensure(self, asset_id: str) -> Dict[str, Any]:
        """
        Ensure asset is ready.

        For download=upstream (DeepFilterNet): defer to lib's maybe_download_model
        when the backend runs. Returns metadata + lib path.
        For download=urls: use taudio_models.cache.ensure_model on weight_ids.
        """
        asset = self.get(asset_id)
        lib_path = self.resolve_lib_path(asset_id)
        weight_paths: Dict[str, Path] = {}
        if asset.download == "urls" and asset.weight_ids:
            from taudio_models.cache import ensure_model

            weight_manifest = dict(self.manifest)
            weight_manifest["models"] = self.manifest.get("weights") or {}
            for wid in asset.weight_ids:
                weight_paths[wid] = ensure_model(weight_manifest, wid)
        return {
            "asset": asset.to_dict(),
            "lib_path": lib_path,
            "weight_paths": weight_paths,
            "upstream_ref": asset.upstream_ref,
        }
