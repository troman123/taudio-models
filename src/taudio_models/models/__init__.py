from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from taudio_models.api.model import LoadedModel, Model
from taudio_models.api.registry import register_model
from taudio_models.api.types import ModelInfo, ModelParams

if TYPE_CHECKING:
    from taudio_models.api.registry import ModelRegistry


class _BaseModel(Model):
    """Catalog stub: structure + weight ensure/load shell until libs are wired."""

    def __init__(self, registry: "ModelRegistry", info: ModelInfo):
        self.registry = registry
        self._info = info

    def info(self) -> ModelInfo:
        return self._info

    def ensure_weights(self) -> Dict[str, Path]:
        return self.registry.ensure_weights(self._info.id)

    def load(self, params: Optional[ModelParams] = None) -> LoadedModel:
        info = self.info()
        validated = (params or ModelParams()).validated(info)
        weight_paths = self.ensure_weights() if info.weight_ids else {}
        # backend remains None until open libs are vendored and status=available
        return LoadedModel(
            info=info,
            params=validated,
            weight_paths=weight_paths,
            backend=None,
            meta={"loader": "stub", "note": "inference belongs in TaudioProcess engine layer"},
        )


@register_model("ause")
class AuseModel(_BaseModel):
    pass


@register_model("melro")
class MelroModel(_BaseModel):
    pass


@register_model("demucs")
class DemucsModel(_BaseModel):
    pass


@register_model("deepfilter")
class DeepFilterModel(_BaseModel):
    pass
