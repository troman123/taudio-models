# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public capability registry + registration hooks (open, generic names)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from taudio_models.manifest import load_manifest
from taudio_models.paths import resolve_models_root
from taudio_models.registry.assets import PublicAssetRegistry

# capability_id -> factory(registry) -> PublicCapability
_CAPABILITY_CTORS: Dict[str, Callable[["PublicCapabilityRegistry"], "PublicCapability"]] = {}


def register_capability(
    capability_id: str,
) -> Callable[
    [Callable[["PublicCapabilityRegistry"], "PublicCapability"]],
    Callable[["PublicCapabilityRegistry"], "PublicCapability"],
]:
    """
    Register a capability factory onto the adapter layer.

    Used by open built-ins and by private extensions at import/runtime.
    Factories are applied when PublicCapabilityRegistry is constructed.
    """

    def deco(
        factory: Callable[["PublicCapabilityRegistry"], "PublicCapability"],
    ) -> Callable[["PublicCapabilityRegistry"], "PublicCapability"]:
        _CAPABILITY_CTORS[str(capability_id)] = factory
        return factory

    return deco


@dataclass
class PublicCapability:
    """
    One adapter-layer capability (unified call surface).

    Example ids: denoise.speech (open), dn.speech (private, runtime-registered).

    Thin runners — forward to backends/libs or compose other capabilities:
      run_file  — path in / path out
      run_array — PCM trunk in / PCM trunk out
    """

    id: str
    display_name: str
    default_asset_id: str
    description: str = ""
    kind: str = ""
    # (input_path, output_dir, asset_ensure, params) -> list[Path]
    run_file: Optional[Callable[..., List[Path]]] = None
    # (audio, sample_rate, asset_ensure, params) -> (audio_out, sample_rate)
    run_array: Optional[Callable[..., Any]] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "default_asset_id": self.default_asset_id,
            "description": self.description,
            "kind": self.kind,
            "has_run_file": self.run_file is not None,
            "has_run_array": self.run_array is not None,
            "meta": dict(self.meta),
        }


@dataclass
class ResolvedPublicCapability:
    capability: PublicCapability
    asset_ensure: Dict[str, Any]
    params: Dict[str, Any] = field(default_factory=dict)


class PublicCapabilityRegistry:
    """
    Adapter layer: sole call entry for capabilities.

    Open built-ins load from code + manifest. Private extensions register via
    register_capability before open_capability_registry() / open_adapter().
    Callers use run_file / run_array only — never bypass to libs.
    """

    def __init__(self, models_root: Optional[Path] = None):
        self.root = resolve_models_root(models_root)
        self.manifest = load_manifest(self.root / "manifest.yaml")
        self.assets = PublicAssetRegistry(self.root)
        self._caps: Dict[str, PublicCapability] = {}
        self._load_manifest_caps()
        self._load_code_caps()

    def _load_manifest_caps(self) -> None:
        raw = self.manifest.get("capabilities") or {}
        if not isinstance(raw, dict):
            return
        for cid, entry in raw.items():
            if not isinstance(entry, dict):
                continue
            cid = str(cid)
            if cid in self._caps:
                continue
            self._caps[cid] = PublicCapability(
                id=cid,
                display_name=str(entry.get("display_name") or cid),
                default_asset_id=str(entry.get("default_asset") or entry.get("default_asset_id") or ""),
                description=str(entry.get("description") or ""),
                kind=str(entry.get("kind") or ""),
                meta={k: v for k, v in entry.items() if k not in {
                    "display_name", "default_asset", "default_asset_id",
                    "description", "kind",
                }},
            )

    def _load_code_caps(self) -> None:
        # Import built-in capability modules for side-effect registration
        from taudio_models import capabilities as _caps  # noqa: F401

        for cid, factory in _CAPABILITY_CTORS.items():
            cap = factory(self)
            # Code registration wins for run_file wiring
            self._caps[cid] = cap

    def register(self, capability: PublicCapability) -> None:
        self._caps[capability.id] = capability

    def list_capabilities(self) -> List[PublicCapability]:
        return [self._caps[k] for k in sorted(self._caps)]

    def get(self, capability_id: str) -> PublicCapability:
        key = str(capability_id).strip()
        if key not in self._caps:
            raise KeyError("unknown public capability: %s" % capability_id)
        return self._caps[key]

    def resolve(
        self,
        capability_id: str,
        *,
        asset_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> ResolvedPublicCapability:
        cap = self.get(capability_id)
        aid = (asset_id or cap.default_asset_id or "").strip()
        meta = dict(cap.meta or {})
        # Route / orchestration caps may compose other caps and need no asset.
        allow_no_asset = (
            not aid
            or aid in ("_", "none", "-")
            or cap.kind == "route"
            or bool(meta.get("no_asset"))
        )
        if not aid and not allow_no_asset:
            raise ValueError("capability %s has no default_asset_id" % capability_id)
        if not aid or aid in ("_", "none", "-"):
            ensured: Dict[str, Any] = {
                "asset": {},
                "lib_path": None,
                "weight_paths": {},
                "upstream_ref": None,
                "requested_asset_id": aid or "",
                "resolved_asset_id": "",
            }
        else:
            ensured = self.assets.ensure(aid)
        return ResolvedPublicCapability(
            capability=cap,
            asset_ensure=ensured,
            params=dict(params or {}),
        )

    def has(self, capability_id: str) -> bool:
        return str(capability_id).strip() in self._caps

    def run_file(
        self,
        capability_id: str,
        input_path: Path,
        output_dir: Path,
        *,
        asset_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Path]:
        """Adapter entry: run a registered capability on a file."""
        resolved = self.resolve(capability_id, asset_id=asset_id, params=params)
        runner = resolved.capability.run_file
        if runner is None:
            raise NotImplementedError(
                "capability %s has no run_file" % capability_id
            )
        return runner(
            Path(input_path),
            Path(output_dir),
            resolved.asset_ensure,
            resolved.params,
        )

    def run_array(
        self,
        capability_id: str,
        audio: Any,
        sample_rate: int,
        *,
        asset_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Adapter entry: run a registered capability on a PCM trunk."""
        resolved = self.resolve(capability_id, asset_id=asset_id, params=params)
        runner = resolved.capability.run_array
        if runner is None:
            raise NotImplementedError(
                "capability %s has no run_array; use run_file for path I/O" % capability_id
            )
        return runner(audio, int(sample_rate), resolved.asset_ensure, resolved.params)


def open_capability_registry(models_root: Optional[Path] = None) -> PublicCapabilityRegistry:
    return PublicCapabilityRegistry(models_root=models_root)
