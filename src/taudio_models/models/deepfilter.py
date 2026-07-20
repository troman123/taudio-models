# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Catalog model adapter for deepfilter (bridges to public assets)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from taudio_models.api.model import LoadedModel, Model
from taudio_models.api.registry import register_model
from taudio_models.api.types import ModelInfo, ModelParams
from taudio_models.backends.deepfilter import ensure_deepfilter_import, ensure_upstream_weights
from taudio_models.registry.assets import PublicAssetRegistry

if TYPE_CHECKING:
    from taudio_models.api.registry import ModelRegistry


_VERSION_TO_ASSET = {
    "1": "deepfilternet",
    "2": "deepfilternet2",
    "3": "deepfilternet3",
}


@register_model("deepfilter")
class DeepFilterModel(Model):
    def __init__(self, registry: "ModelRegistry", info: ModelInfo):
        self._registry = registry
        self._info = info
        self._assets = PublicAssetRegistry(registry.root)

    def info(self) -> ModelInfo:
        return self._info

    def _asset_id(self, params: ModelParams) -> str:
        ver = str(params.get("version", "3"))
        return _VERSION_TO_ASSET.get(ver, "deepfilternet3")

    def ensure_weights(self) -> Dict[str, Path]:
        # Default to v3 public asset
        ensured = self._assets.ensure("deepfilternet3")
        lib_path = Path(ensured["lib_path"])
        ensure_deepfilter_import(lib_path)
        model_dir = ensure_upstream_weights(
            str(ensured["upstream_ref"]),
            lib_path=lib_path,
        )
        return {"deepfilternet3": model_dir}

    def load(self, params: Optional[ModelParams] = None) -> LoadedModel:
        params = params or ModelParams()
        validated = params.validated(self._info)
        asset_id = self._asset_id(validated)
        ensured = self._assets.ensure(asset_id)
        lib_path = Path(ensured["lib_path"])
        ensure_deepfilter_import(lib_path)
        model_dir = ensure_upstream_weights(
            str(ensured["upstream_ref"]),
            lib_path=lib_path,
        )
        return LoadedModel(
            info=self._info,
            params=validated,
            weight_paths={asset_id: model_dir},
            backend={
                "kind": "deepfilter",
                "public_capability": "denoise.speech",
                "public_asset": asset_id,
                "upstream_ref": ensured["upstream_ref"],
                "lib_path": str(lib_path),
            },
            meta={"download": "upstream"},
        )
