from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union


class ModelStatus(str, Enum):
    AVAILABLE = "available"
    PLANNED = "planned"
    DISABLED = "disabled"


class ParamType(str, Enum):
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    ENUM = "enum"
    PATH = "path"


class Capability(str, Enum):
    SEPARATE_VOCALS = "separate_vocals"
    SEPARATE_INSTRUMENTAL = "separate_instrumental"
    SEPARATE_LEAD = "separate_lead"
    SEPARATE_BACKING = "separate_backing"
    DENOISE = "denoise"
    LOUDNORM = "loudnorm"
    ENHANCE = "enhance"


class StemKind(str, Enum):
    MIX = "mix"
    VOCALS = "vocals"
    INSTRUMENTAL = "instrumental"
    LEAD = "lead"
    BACKING = "backing"
    OTHER = "other"


@dataclass(frozen=True)
class ModelParam:
    """One tunable parameter exposed the same way for every model."""

    name: str
    type: ParamType
    default: Any = None
    description: str = ""
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    choices: Optional[List[Any]] = None
    required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ModelParam":
        return cls(
            name=str(data["name"]),
            type=ParamType(str(data.get("type", "string"))),
            default=data.get("default"),
            description=str(data.get("description") or ""),
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            choices=list(data["choices"]) if data.get("choices") is not None else None,
            required=bool(data.get("required", False)),
        )


@dataclass(frozen=True)
class ModelInfo:
    """Queryable model capability card — stable contract for TaudioProcess / clients."""

    id: str
    display_name: str
    status: ModelStatus
    capabilities: List[Capability] = field(default_factory=list)
    params: List[ModelParam] = field(default_factory=list)
    output_stems: List[StemKind] = field(default_factory=list)
    weight_ids: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    license_spdx: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "params": [p.to_dict() for p in self.params],
            "output_stems": [s.value for s in self.output_stems],
            "weight_ids": list(self.weight_ids),
            "aliases": list(self.aliases),
            "license_spdx": self.license_spdx,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ModelInfo":
        return cls(
            id=str(data["id"]),
            display_name=str(data.get("display_name") or data["id"]),
            status=ModelStatus(str(data.get("status", "planned"))),
            capabilities=[Capability(x) for x in (data.get("capabilities") or [])],
            params=[ModelParam.from_dict(p) for p in (data.get("params") or [])],
            output_stems=[StemKind(x) for x in (data.get("output_stems") or [])],
            weight_ids=[str(x) for x in (data.get("weight_ids") or [])],
            aliases=[str(x) for x in (data.get("aliases") or [])],
            license_spdx=str(data.get("license_spdx") or ""),
            description=str(data.get("description") or ""),
        )


@dataclass
class ModelParams:
    """
    Unified parameter bag passed into every model.run().

    Unknown keys are rejected unless allow_extra=True.
    Values are coerced/validated against ModelInfo.params.
    """

    values: Dict[str, Any] = field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.values)

    @classmethod
    def from_mapping(cls, data: Optional[Mapping[str, Any]] = None) -> "ModelParams":
        return cls(values=dict(data or {}))

    def validated(self, info: ModelInfo, *, allow_extra: bool = False) -> "ModelParams":
        known = {p.name: p for p in info.params}
        extras = [k for k in self.values if k not in known]
        if extras and not allow_extra:
            raise ValueError(
                "unknown params for model %s: %s; allowed=%s"
                % (info.id, extras, sorted(known))
            )
        out: Dict[str, Any] = {}
        for name, spec in known.items():
            if name in self.values:
                out[name] = _coerce(spec, self.values[name])
            elif spec.required and spec.default is None:
                raise ValueError("missing required param %s for model %s" % (name, info.id))
            else:
                out[name] = spec.default
        return ModelParams(values=out)


@dataclass(frozen=True)
class Artifact:
    stem: StemKind
    path: Path

    def to_dict(self) -> Dict[str, Any]:
        return {"stem": self.stem.value, "path": str(self.path)}


@dataclass(frozen=True)
class RunRequest:
    """Fixed request shape for TaudioProcess -> engines."""

    model_id: str
    input_path: Path
    output_dir: Path
    params: ModelParams = field(default_factory=ModelParams)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "input_path": str(self.input_path),
            "output_dir": str(self.output_dir),
            "params": self.params.to_dict(),
        }


@dataclass(frozen=True)
class RunResult:
    model_id: str
    artifacts: List[Artifact]
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "meta": dict(self.meta),
        }


def _coerce(spec: ModelParam, value: Any) -> Any:
    t = spec.type
    if t is ParamType.BOOL:
        if isinstance(value, bool):
            return value
        if str(value).lower() in ("1", "true", "yes", "on"):
            return True
        if str(value).lower() in ("0", "false", "no", "off"):
            return False
        raise ValueError("param %s expects bool, got %r" % (spec.name, value))
    if t is ParamType.INT:
        v = int(value)
        _range_check(spec, v)
        return v
    if t is ParamType.FLOAT:
        v = float(value)
        _range_check(spec, v)
        return v
    if t is ParamType.ENUM:
        if spec.choices is not None and value not in spec.choices:
            raise ValueError(
                "param %s must be one of %s, got %r" % (spec.name, spec.choices, value)
            )
        return value
    if t is ParamType.PATH:
        return str(value)
    return str(value) if value is not None else value


def _range_check(spec: ModelParam, value: Union[int, float]) -> None:
    if spec.minimum is not None and value < spec.minimum:
        raise ValueError("param %s < minimum %s" % (spec.name, spec.minimum))
    if spec.maximum is not None and value > spec.maximum:
        raise ValueError("param %s > maximum %s" % (spec.name, spec.maximum))


JsonDict = Dict[str, Any]
