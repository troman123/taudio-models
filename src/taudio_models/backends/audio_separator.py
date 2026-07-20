# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Audio Separator backend — thin glue over pip `audio-separator` or vendored audio_separatorv."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from taudio_models.cache import cache_root

SelectStem = Literal["vocal", "instrumental", "iv"]

# Source audioprocessPython/modules/audioseparator.py MODEL_LOOKUP
MODEL_LOOKUP: Dict[str, str] = {
    "melk2": "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
    "rofep": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "rofk2": "UVR_MDXNET_KARA_2.onnx",
    "rofk1": "UVR_MDXNET_KARA_2.onnx",
    "base": "UVR-MDX-NET-Inst_HQ_3.onnx",
    "vocin": "MDX23C-8KFFT-InstVoc_HQ_2.ckpt",
    "mdxin": "UVR-MDX-NET-Inst_HQ_5.onnx",
}

_SELECT_TO_STEM: Dict[str, str] = {
    "vocal": "vocal",
    "vocals": "vocal",
    "vocallead": "vocal",
    "vocalback": "vocal",
    "instrumental": "inst",
    "inst": "inst",
    "iv": "iv",
}


def _import_error(detail: str) -> ImportError:
    return ImportError(
        "Audio Separator not available (%s).\n"
        "Install optional deps: pip install 'taudio-models[separate]' "
        "or vendor libs/audio_separatorv."
        % detail
    )


def ensure_separator_import(lib_path: Optional[Path] = None) -> Any:
    """Import Separator from vendored audio_separatorv or pip audio-separator."""
    if lib_path is not None:
        lib_path = Path(lib_path).resolve()
        if lib_path.is_dir():
            parent = lib_path.parent
            for root in (parent, lib_path):
                root_s = str(root)
                if root_s not in sys.path:
                    sys.path.insert(0, root_s)
    try:
        from audio_separatorv.separator import Separator  # type: ignore

        return Separator
    except ImportError:
        pass
    try:
        from audio_separator.separator import Separator  # type: ignore

        return Separator
    except ImportError as e:
        raise _import_error(str(e)) from e


def resolve_model_code(params: Optional[Dict[str, Any]]) -> str:
    params = dict(params or {})
    raw = params.get("model") or params.get("m") or params.get("model_weight") or "rofep"
    return str(raw).strip().lower()


def resolve_model_filename(model_code: str) -> str:
    code = str(model_code).strip().lower()
    if code in MODEL_LOOKUP:
        return MODEL_LOOKUP[code]
    name = str(model_code).strip()
    if name.lower().endswith((".ckpt", ".onnx", ".pth", ".pt")):
        return name
    raise ValueError(
        "unknown Audio Separator model code %r; known codes: %s"
        % (model_code, ", ".join(sorted(MODEL_LOOKUP)))
    )


def resolve_model_store_dir(
    *,
    models_root: Optional[Path] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Path:
    params = dict(params or {})
    explicit = params.get("model_store_dir") or params.get("model_file_dir")
    if explicit:
        path = Path(str(explicit)).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    for env_key in ("TAUDIO_AUDIO_SEPARATOR_MODELS_DIR", "TAUDIO_AUSE_MODELS_DIR"):
        env_val = os.environ.get(env_key, "").strip()
        if env_val:
            path = Path(env_val).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            return path.resolve()

    store = cache_root() / "audio-separator-models"
    if models_root is not None:
        under_root = Path(models_root).resolve() / "audio-separator-models"
        if under_root.is_dir() and any(under_root.iterdir()):
            return under_root
    store.mkdir(parents=True, exist_ok=True)
    return store.resolve()


def ensure_model_file(model_store_dir: Path, model_filename: str) -> Path:
    path = Path(model_store_dir) / model_filename
    if path.is_file():
        return path.resolve()
    raise FileNotFoundError(
        "Audio Separator model not found: %s\n"
        "Place weights under %s or set TAUDIO_AUDIO_SEPARATOR_MODELS_DIR.\n"
        "P2 ECS (rofep + melk2): model_bs_roformer_ep_317_sdr_12.9755.ckpt, "
        "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
        % (path, model_store_dir)
    )


def _resolve_select(params: Optional[Dict[str, Any]]) -> SelectStem:
    raw = str((params or {}).get("select") or "vocal").strip().lower()
    if raw in _SELECT_TO_STEM:
        mapped = _SELECT_TO_STEM[raw]
        if mapped == "iv":
            return "iv"
        if mapped == "inst":
            return "instrumental"
        return "vocal"
    return "vocal"


def _stem_key_from_filename(filename: str, input_basename: str, model_core_name: str) -> str:
    pattern = re.compile(r"\((.*?)\)")
    _, file_ext = os.path.splitext(filename)
    clean_string = filename
    clean_string = clean_string.replace(input_basename, "")
    clean_string = clean_string.replace(model_core_name, "")
    match = pattern.search(clean_string)
    if match:
        stem_tag = match.group(1).lower()
    else:
        stem_tag = clean_string.lower()
    if "vocal" in stem_tag:
        return "vocal"
    if "inst" in stem_tag:
        return "inst"
    if "drum" in stem_tag:
        return "drums"
    if "bass" in stem_tag:
        return "bass"
    if "guitar" in stem_tag:
        return "guitar"
    if "piano" in stem_tag:
        return "piano"
    return "other"


def _hash_name(filename: str) -> str:
    return hashlib.md5(filename.encode("utf-8")).hexdigest()


def _classify_outputs(
    output_files: List[str],
    *,
    output_dir: Path,
    input_path: Path,
    model_filename: str,
) -> Dict[str, Path]:
    input_basename = input_path.stem
    model_core_name = model_filename.split(".")[0]
    result: Dict[str, Path] = {}
    for filename in output_files:
        full_path = output_dir / filename
        if not full_path.is_file():
            continue
        _, file_ext = os.path.splitext(filename)
        key_name = _stem_key_from_filename(filename, input_basename, model_core_name)
        final_name = "%s_%s_%s%s" % (_hash_name(filename), input_basename, key_name, file_ext)
        final_path = output_dir / final_name
        if final_path.exists():
            final_path.unlink()
        full_path.rename(final_path)
        result[key_name] = final_path
    return result


def separate_file(
    input_path: Path,
    output_dir: Path,
    *,
    lib_path: Optional[Path] = None,
    asset_ensure: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    params: Optional[Dict[str, Any]] = None,
    models_root: Optional[Path] = None,
) -> List[Path]:
    """Run karaoke/stem separation; return selected stem path(s)."""
    params = dict(params or {})
    asset_ensure = dict(asset_ensure or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    model_code = resolve_model_code(params)
    model_filename = resolve_model_filename(model_code)
    model_store_dir = resolve_model_store_dir(models_root=models_root, params=params)
    ensure_model_file(model_store_dir, model_filename)

    Separator = ensure_separator_import(lib_path)
    select = _resolve_select(params)
    use_gpu = bool(params.get("is_gpu", is_gpu))
    log_level = logging.DEBUG if params.get("debug") else logging.INFO
    output_format = str(params.get("output_format") or "WAV")

    # audio-separator API drifted: older builds take force_gpu; 0.4x dropped it.
    import inspect

    ctor_kwargs: Dict[str, Any] = {
        "log_level": log_level,
        "model_file_dir": str(model_store_dir),
        "output_dir": str(output_dir),
        "output_format": output_format,
    }
    try:
        accepted = set(inspect.signature(Separator.__init__).parameters)
    except (TypeError, ValueError):
        accepted = set()
    if "force_gpu" in accepted:
        ctor_kwargs["force_gpu"] = use_gpu
    elif use_gpu and "use_autocast" in accepted:
        ctor_kwargs["use_autocast"] = True
    # Generic passthrough: caller may supply Separator kwargs (e.g. mdxc_params).
    for key in (
        "mdxc_params",
        "mdx_params",
        "vr_params",
        "demucs_params",
        "chunk_duration",
        "sample_rate",
    ):
        if key in params and key in accepted:
            ctor_kwargs[key] = params[key]
    separator = Separator(**ctor_kwargs)
    separator.load_model(model_filename=model_filename)
    output_files = separator.separate(str(input_path))
    stems = _classify_outputs(
        list(output_files or []),
        output_dir=output_dir,
        input_path=input_path,
        model_filename=model_filename,
    )

    if select == "iv":
        paths = [stems[k] for k in ("vocal", "inst") if k in stems]
        if paths:
            return paths
        raise RuntimeError("separation produced no vocal/inst stems: %s" % list(stems))

    want = "inst" if select == "instrumental" else "vocal"
    if want in stems:
        return [stems[want]]
    raise RuntimeError(
        "separation missing stem %r (got %s) for select=%r model=%r"
        % (want, list(stems), select, model_code)
    )


def separate_array(
    audio: Any,
    sample_rate: int,
    *,
    lib_path: Optional[Path] = None,
    asset_ensure: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    params: Optional[Dict[str, Any]] = None,
    models_root: Optional[Path] = None,
) -> Tuple[Any, int]:
    """Array path via temp wav — real inference, not a toy DSP stub."""
    import tempfile

    import numpy as np
    import soundfile as sf

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    arr = np.asarray(audio, dtype=np.float32)
    with tempfile.TemporaryDirectory(prefix="taudio_ause_") as tmp:
        tmp_dir = Path(tmp)
        in_path = tmp_dir / "input.wav"
        out_dir = tmp_dir / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        sf.write(str(in_path), arr.T if arr.ndim == 2 else arr, int(sample_rate))
        outs = separate_file(
            in_path,
            out_dir,
            lib_path=lib_path,
            asset_ensure=asset_ensure,
            is_gpu=is_gpu,
            params=params,
            models_root=models_root,
        )
        data, sr = sf.read(str(outs[0]), always_2d=True, dtype="float32")
        return data.T, int(sr)
