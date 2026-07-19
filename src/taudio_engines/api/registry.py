from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from taudio_engines.api.engine import Engine
from taudio_engines.api.types import (
    Capability,
    ModelInfo,
    ModelParam,
    ModelParams,
    ModelStatus,
    ParamType,
    RunRequest,
    RunResult,
    StemKind,
)
from taudio_engines.manifest import load_manifest, repo_root_from

_ENGINE_CTORS: Dict[str, Type[Engine]] = {}


def register_engine(model_id: str) -> Callable[[Type[Engine]], Type[Engine]]:
    def deco(cls: Type[Engine]) -> Type[Engine]:
        _ENGINE_CTORS[model_id] = cls
        return cls

    return deco


def _param_from_raw(raw: Dict[str, Any]) -> ModelParam:
    return ModelParam.from_dict(raw)


def _info_from_engine_entry(model_id: str, entry: Dict[str, Any]) -> ModelInfo:
    caps = [Capability(x) for x in (entry.get("capabilities") or [])]
    stems = [StemKind(x) for x in (entry.get("output_stems") or [])]
    params = [_param_from_raw(p) for p in (entry.get("params") or [])]
    status = ModelStatus(str(entry.get("status", "planned")))
    # available only if status says so AND a ctor is registered (or still planned)
    if status is ModelStatus.AVAILABLE and model_id not in _ENGINE_CTORS:
        # advertised available but not wired yet -> treat as planned for callers
        status = ModelStatus.PLANNED
    return ModelInfo(
        id=model_id,
        display_name=str(entry.get("display_name") or model_id),
        status=status,
        capabilities=caps,
        params=params,
        output_stems=stems,
        weight_ids=[str(x) for x in (entry.get("requires_models") or entry.get("weight_ids") or [])],
        aliases=[str(x) for x in (entry.get("aliases") or [])],
        license_spdx=str(entry.get("license_spdx") or ""),
        description=str(entry.get("description") or ""),
    )


class Registry:
    """Query + run facade used by TaudioProcess."""

    def __init__(self, engines_root: Optional[Path] = None):
        self.root = Path(engines_root).resolve() if engines_root else repo_root_from()
        self.manifest = load_manifest(self.root / "manifest.yaml")
        # import stub engines so register_engine runs
        from taudio_engines import engines as _engines  # noqa: F401

    def list_models(
        self,
        *,
        include_planned: bool = True,
        capability: Optional[Capability] = None,
    ) -> List[ModelInfo]:
        out: List[ModelInfo] = []
        engines = self.manifest.get("engines") or {}
        for mid, entry in engines.items():
            if not isinstance(entry, dict):
                continue
            info = _info_from_engine_entry(mid, entry)
            if not include_planned and info.status is not ModelStatus.AVAILABLE:
                continue
            if capability is not None and capability not in info.capabilities:
                continue
            out.append(info)
        return out

    def get_model(self, model_id_or_alias: str) -> ModelInfo:
        mid = self.resolve_id(model_id_or_alias)
        engines = self.manifest.get("engines") or {}
        entry = engines.get(mid)
        if not isinstance(entry, dict):
            raise KeyError("unknown model: %s" % model_id_or_alias)
        return _info_from_engine_entry(mid, entry)

    def resolve_id(self, model_id_or_alias: str) -> str:
        key = str(model_id_or_alias).strip()
        engines = self.manifest.get("engines") or {}
        if key in engines:
            return key
        for mid, entry in engines.items():
            aliases = entry.get("aliases") or []
            if key in aliases:
                return mid
        raise KeyError("unknown model id/alias: %s" % model_id_or_alias)

    def create_engine(self, model_id_or_alias: str) -> Engine:
        mid = self.resolve_id(model_id_or_alias)
        info = self.get_model(mid)
        if info.status is not ModelStatus.AVAILABLE:
            raise RuntimeError("model %s is not available (status=%s)" % (mid, info.status.value))
        ctor = _ENGINE_CTORS.get(mid)
        if ctor is None:
            raise RuntimeError("model %s has no registered Engine implementation" % mid)
        return ctor(registry=self, info=info)

    def run(self, request: RunRequest) -> RunResult:
        engine = self.create_engine(request.model_id)
        info = engine.info()
        params = request.params.validated(info)
        return engine.run(request.input_path, request.output_dir, params)

    def run_model(
        self,
        model_id: str,
        input_path: Path,
        output_dir: Path,
        params: Optional[Dict[str, Any]] = None,
    ) -> RunResult:
        """Fixed TaudioProcess entry: one model id + ModelParams dict."""
        req = RunRequest(
            model_id=model_id,
            input_path=Path(input_path),
            output_dir=Path(output_dir),
            params=ModelParams.from_mapping(params),
        )
        return self.run(req)


def open_registry(engines_root: Optional[Path] = None) -> Registry:
    return Registry(engines_root=engines_root)
