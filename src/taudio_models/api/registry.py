# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from taudio_models.api.model import LoadedModel, Model
from taudio_models.api.types import (
    Capability,
    ModelInfo,
    ModelParam,
    ModelParams,
    ModelStatus,
    StemKind,
)
from taudio_models.cache import ensure_model
from taudio_models.manifest import load_manifest, repo_root_from

_MODEL_CTORS: Dict[str, Type[Model]] = {}


def register_model(model_id: str) -> Callable[[Type[Model]], Type[Model]]:
    def deco(cls: Type[Model]) -> Type[Model]:
        _MODEL_CTORS[model_id] = cls
        return cls

    return deco


def _info_from_catalog_entry(model_id: str, entry: Dict[str, Any]) -> ModelInfo:
    caps = [Capability(x) for x in (entry.get("capabilities") or [])]
    stems = [StemKind(x) for x in (entry.get("output_stems") or [])]
    params = [ModelParam.from_dict(p) for p in (entry.get("params") or [])]
    status = ModelStatus(str(entry.get("status", "planned")))
    if status is ModelStatus.AVAILABLE and model_id not in _MODEL_CTORS:
        status = ModelStatus.PLANNED
    return ModelInfo(
        id=model_id,
        display_name=str(entry.get("display_name") or model_id),
        status=status,
        version=str(entry.get("version") or "0.0.0"),
        capabilities=caps,
        params=params,
        output_stems=stems,
        weight_ids=[
            str(x)
            for x in (
                entry.get("weight_ids")
                or entry.get("requires_models")
                or []
            )
        ],
        aliases=[str(x) for x in (entry.get("aliases") or [])],
        license_spdx=str(entry.get("license_spdx") or ""),
        description=str(entry.get("description") or ""),
    )


def _catalog(manifest: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer "catalog"; accept legacy "engines" key during migration.
    cat = manifest.get("catalog")
    if isinstance(cat, dict):
        return cat
    legacy = manifest.get("engines")
    return legacy if isinstance(legacy, dict) else {}


def _weights(manifest: Dict[str, Any]) -> Dict[str, Any]:
    w = manifest.get("weights")
    if isinstance(w, dict):
        return w
    legacy = manifest.get("models")
    return legacy if isinstance(legacy, dict) else {}


class ModelRegistry:
    """
    Open-source model layer facade.

    Query model cards, download weights, load model handles.
    Does NOT process audio files/frames — that is TaudioProcess engine layer.
    """

    def __init__(self, models_root: Optional[Path] = None):
        self.root = Path(models_root).resolve() if models_root else repo_root_from()
        self.manifest = load_manifest(self.root / "manifest.yaml")
        from taudio_models import models as _models  # noqa: F401

    def list_models(
        self,
        *,
        include_planned: bool = True,
        capability: Optional[Capability] = None,
    ) -> List[ModelInfo]:
        out: List[ModelInfo] = []
        for mid, entry in _catalog(self.manifest).items():
            if not isinstance(entry, dict):
                continue
            info = _info_from_catalog_entry(mid, entry)
            if not include_planned and info.status is not ModelStatus.AVAILABLE:
                continue
            if capability is not None and capability not in info.capabilities:
                continue
            out.append(info)
        return out

    def get_model(self, model_id_or_alias: str) -> ModelInfo:
        mid = self.resolve_id(model_id_or_alias)
        entry = _catalog(self.manifest).get(mid)
        if not isinstance(entry, dict):
            raise KeyError("unknown model: %s" % model_id_or_alias)
        return _info_from_catalog_entry(mid, entry)

    def resolve_id(self, model_id_or_alias: str) -> str:
        key = str(model_id_or_alias).strip()
        cat = _catalog(self.manifest)
        if key in cat:
            return key
        for mid, entry in cat.items():
            if key in (entry.get("aliases") or []):
                return mid
        raise KeyError("unknown model id/alias: %s" % model_id_or_alias)

    def ensure_weights(self, model_id_or_alias: str) -> Dict[str, Path]:
        info = self.get_model(model_id_or_alias)
        # Temporarily expose weight entries under manifest for ensure_model helper
        weight_manifest = dict(self.manifest)
        weight_manifest["models"] = _weights(self.manifest)
        paths: Dict[str, Path] = {}
        for wid in info.weight_ids:
            paths[wid] = ensure_model(weight_manifest, wid)
        return paths

    def create_model(self, model_id_or_alias: str) -> Model:
        mid = self.resolve_id(model_id_or_alias)
        info = self.get_model(mid)
        ctor = _MODEL_CTORS.get(mid)
        if ctor is None:
            raise RuntimeError("model %s has no registered Model implementation" % mid)
        return ctor(registry=self, info=info)

    def load_model(
        self,
        model_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> LoadedModel:
        """Fixed open API: load model + weights; no audio I/O."""
        model = self.create_model(model_id)
        info = model.info()
        validated = ModelParams.from_mapping(params).validated(info)
        return model.load(validated)


def open_registry(models_root: Optional[Path] = None) -> ModelRegistry:
    return ModelRegistry(models_root=models_root)


# Back-compat alias
Registry = ModelRegistry
