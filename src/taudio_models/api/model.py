from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from taudio_models.api.types import ModelInfo, ModelParams


@dataclass
class LoadedModel:
    """
    Opaque loaded model handle for the closed engine layer (TaudioProcess).

    Open-source model layer only prepares: info, validated params, weight paths,
    and optional backend object once libs are wired. It does NOT process files
    or PCM frames — that stays in TaudioProcess.
    """

    info: ModelInfo
    params: ModelParams
    weight_paths: Dict[str, Path] = field(default_factory=dict)
    backend: Any = None
    meta: Dict[str, Any] = field(default_factory=dict)


class Model(ABC):
    """
    Open-source model layer contract.

    - describe structure (ModelInfo / ModelParams)
    - download weights
    - load weights / backend

    Not responsible for: reading wav/pcm, writing stems, batching, pipelines.
    """

    @abstractmethod
    def info(self) -> ModelInfo:
        raise NotImplementedError

    @abstractmethod
    def ensure_weights(self) -> Dict[str, Path]:
        """Download required weights into cache; return id -> local path."""
        raise NotImplementedError

    @abstractmethod
    def load(self, params: Optional[ModelParams] = None) -> LoadedModel:
        """Validate params, ensure weights, load backend (when available)."""
        raise NotImplementedError
