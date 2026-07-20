# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""MelBand RoFormer backend — thin glue over libs/MelBandRoformer (not a reimplementation)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

SelectStem = Literal["vocal", "instrumental", "iv"]


def ensure_melband_import(lib_path: Optional[Path] = None) -> None:
    """Prepend vendored libs/MelBandRoformer so enhance_call resolves locally."""
    if lib_path is None:
        return
    lib_path = Path(lib_path).resolve()
    if not lib_path.is_dir():
        return
    root = str(lib_path)
    if root not in sys.path:
        sys.path.insert(0, root)


def _import_error(detail: str) -> ImportError:
    return ImportError(
        "MelBand RoFormer not available (%s).\n"
        "Vendor libs/MelBandRoformer and install runtime deps "
        "(torch, soundfile, ml_collections, einops, beartype, rotary_embedding_torch, librosa)."
        % detail
    )


def _resolve_select(params: Optional[Dict[str, Any]]) -> SelectStem:
    raw = str((params or {}).get("select") or "vocal").strip().lower()
    if raw in ("vocal", "vocals"):
        return "vocal"
    if raw in ("instrumental", "inst", "other"):
        return "instrumental"
    if raw in ("iv", "both"):
        return "iv"
    return "vocal"


def separate_file(
    input_path: Path,
    output_dir: Path,
    *,
    lib_path: Optional[Path] = None,
    asset_ensure: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> List[Path]:
    """Thin wrap: libs `enhance_call.separate_file`."""
    params = dict(params or {})
    asset_ensure = dict(asset_ensure or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    ensure_melband_import(lib_path)
    try:
        from enhance_call import (  # type: ignore
            resolve_checkpoint,
            resolve_config_path,
            separate_file as _separate_file,
        )
    except ImportError as e:
        raise _import_error(str(e)) from e

    lib = Path(lib_path or asset_ensure.get("lib_path") or ".").resolve()
    asset = asset_ensure.get("asset") or {}
    upstream = str(asset_ensure.get("upstream_ref") or asset.get("upstream_ref") or "MelBandRoformer.ckpt")
    config_rel = str(asset.get("config_path") or "configs/config_vocals_mel_band_roformer.yaml")

    model_path = resolve_checkpoint(
        lib_path=lib,
        upstream_ref=upstream,
        params=params,
        weight_paths=asset_ensure.get("weight_paths"),
    )
    config_path = resolve_config_path(
        lib_path=lib,
        config_rel=config_rel,
        params=params,
    )
    select = _resolve_select(params)
    use_gpu = bool(params.get("is_gpu", is_gpu))

    return _separate_file(
        input_path,
        output_dir,
        model_path=model_path,
        config_path=config_path,
        select=select,
        is_gpu=use_gpu,
        device_ids=params.get("device_ids", 0),
        lib_path=lib,
        params=params,
    )


def separate_array(
    audio: Any,
    sample_rate: int,
    *,
    lib_path: Optional[Path] = None,
    asset_ensure: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, int]:
    """Thin wrap: libs `enhance_call.separate_array`."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    params = dict(params or {})
    asset_ensure = dict(asset_ensure or {})

    ensure_melband_import(lib_path)
    try:
        from enhance_call import (  # type: ignore
            resolve_checkpoint,
            resolve_config_path,
            separate_array as _separate_array,
        )
    except ImportError as e:
        raise _import_error(str(e)) from e

    lib = Path(lib_path or asset_ensure.get("lib_path") or ".").resolve()
    asset = asset_ensure.get("asset") or {}
    upstream = str(asset_ensure.get("upstream_ref") or asset.get("upstream_ref") or "MelBandRoformer.ckpt")
    config_rel = str(asset.get("config_path") or "configs/config_vocals_mel_band_roformer.yaml")

    model_path = resolve_checkpoint(
        lib_path=lib,
        upstream_ref=upstream,
        params=params,
        weight_paths=asset_ensure.get("weight_paths"),
    )
    config_path = resolve_config_path(
        lib_path=lib,
        config_rel=config_rel,
        params=params,
    )
    select = _resolve_select(params)
    use_gpu = bool(params.get("is_gpu", is_gpu))

    return _separate_array(
        audio,
        int(sample_rate),
        model_path=model_path,
        config_path=config_path,
        select=select,
        is_gpu=use_gpu,
        device_ids=params.get("device_ids", 0),
        lib_path=lib,
        params=params,
    )
