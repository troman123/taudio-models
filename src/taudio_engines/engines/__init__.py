from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from taudio_engines.api.engine import Engine
from taudio_engines.api.registry import register_engine
from taudio_engines.api.types import ModelInfo, ModelParams, RunResult, StemKind

if TYPE_CHECKING:
    from taudio_engines.api.registry import Registry


class _BaseStubEngine(Engine):
    """Placeholder until real libs are wired. Keeps the fixed interface."""

    def __init__(self, registry: "Registry", info: ModelInfo):
        self.registry = registry
        self._info = info

    def info(self) -> ModelInfo:
        return self._info

    def run(
        self,
        input_path: Path,
        output_dir: Path,
        params: Optional[ModelParams] = None,
    ) -> RunResult:
        raise NotImplementedError(
            "engine %s is stubbed; status=planned. Wire libs/ and mark status=available."
            % self._info.id
        )


@register_engine("ause")
class AuseEngine(_BaseStubEngine):
    pass


@register_engine("melro")
class MelroEngine(_BaseStubEngine):
    pass


@register_engine("demucs")
class DemucsEngine(_BaseStubEngine):
    pass


@register_engine("deepfilter")
class DeepFilterEngine(_BaseStubEngine):
    pass


# silence unused import lint for StemKind until real engines write stems
_ = StemKind
