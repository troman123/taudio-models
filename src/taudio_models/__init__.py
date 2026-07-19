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
    "StemKind",
    "cache_root",
    "ensure_model",
    "load_manifest",
    "open_registry",
    "register_model",
    "repo_root_from",
]

__version__ = "0.2.0"
