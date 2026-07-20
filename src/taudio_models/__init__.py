# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""taudio-models: open-source model layer (structure, version, download, load)."""

from taudio_models.api import (
    Capability,
    LoadedModel,
    Model,
    ModelInfo,
    ModelParam,
    ModelParams,
    ModelRegistry,
    ModelStatus,
    ParamType,
    StemKind,
    open_registry,
    register_model,
)
from taudio_models.cache import cache_root, ensure_model
from taudio_models.manifest import load_manifest, repo_root_from
from taudio_models.paths import resolve_models_root
from taudio_models.registry import (
    PublicAsset,
    PublicAssetRegistry,
    PublicCapability,
    PublicCapabilityRegistry,
    ResolvedPublicCapability,
    open_capability_registry,
    register_capability,
)

__all__ = [
    "Capability",
    "LoadedModel",
    "Model",
    "ModelInfo",
    "ModelParam",
    "ModelParams",
    "ModelRegistry",
    "ModelStatus",
    "ParamType",
    "PublicAsset",
    "PublicAssetRegistry",
    "PublicCapability",
    "PublicCapabilityRegistry",
    "ResolvedPublicCapability",
    "StemKind",
    "cache_root",
    "ensure_model",
    "load_manifest",
    "open_capability_registry",
    "open_registry",
    "register_capability",
    "register_model",
    "repo_root_from",
    "resolve_models_root",
]

__version__ = "0.4.0"
