"""Thin inference entry for MelBand RoFormer vocal separation (vendored model tree)."""

from __future__ import annotations

import contextlib
import gc
import hashlib
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
import soundfile as sf
import torch
import torch.nn as nn
import yaml
from ml_collections import ConfigDict

warnings.filterwarnings("ignore")

SelectStem = Literal["vocal", "instrumental", "iv"]
_DEFAULT_CONFIG = "configs/config_vocals_mel_band_roformer.yaml"
_MODEL_TYPE = "mel_band_roformer"


def _resolve_torch_dtype(dtype: Optional[Union[str, torch.dtype]]) -> Optional[torch.dtype]:
    """Generic dtype knob: None/fp32 → float32; fp16/half → float16."""
    if dtype is None:
        return None
    if isinstance(dtype, torch.dtype):
        return dtype
    key = str(dtype).strip().lower()
    if key in ("", "fp32", "float32", "float"):
        return torch.float32
    if key in ("fp16", "float16", "half"):
        return torch.float16
    raise ValueError("unsupported dtype %r (use fp32 or fp16)" % dtype)


def _apply_inference_knobs(
    config: ConfigDict,
    *,
    chunk_size: Optional[int] = None,
    flash_attn: Optional[bool] = None,
) -> None:
    """Apply generic inference overrides already present in the yaml schema."""
    if chunk_size is not None:
        config.inference.chunk_size = int(chunk_size)
    if flash_attn is not None:
        config.model.flash_attn = bool(flash_attn)


def ensure_melband_import(lib_path: Optional[Path] = None) -> None:
    """Prepend vendored libs/MelBandRoformer so `mel_band_roformer` resolves locally."""
    if lib_path is None:
        lib_path = Path(__file__).resolve().parent
    lib_path = Path(lib_path).resolve()
    if not lib_path.is_dir():
        return
    root = str(lib_path)
    if root not in sys.path:
        sys.path.insert(0, root)


def default_config_path(lib_path: Optional[Path] = None) -> Path:
    root = Path(lib_path or Path(__file__).resolve().parent)
    return root / _DEFAULT_CONFIG


def get_model_from_config(model_type: str, config: ConfigDict):
    if model_type == _MODEL_TYPE:
        from mel_band_roformer import MelBandRoformer

        return MelBandRoformer(**dict(config.model))
    raise ValueError("Unknown model type: %s" % model_type)


def get_windowing_array(window_size: int, fade_size: int, device):
    fadein = torch.linspace(0, 1, fade_size)
    fadeout = torch.linspace(1, 0, fade_size)
    window = torch.ones(window_size)
    window[-fade_size:] *= fadeout
    window[:fade_size] *= fadein
    return window.to(device)


def demix_track(config, model, mix, device, first_chunk_time=None):
    C = config.inference.chunk_size
    N = config.inference.num_overlap
    step = C // N
    fade_size = C // 10
    border = C - step
    model_dtype = next(model.parameters()).dtype

    if mix.shape[1] > 2 * border and border > 0:
        mix = nn.functional.pad(mix, (border, border), mode="reflect")

    windowing_array = get_windowing_array(C, fade_size, device)

    # autocast is CUDA-only; on CPU it only inflates peak RAM.
    amp_ctx = (
        torch.cuda.amp.autocast()
        if device.type == "cuda"
        else contextlib.nullcontext()
    )
    with amp_ctx:
        with torch.no_grad():
            if config.training.target_instrument is not None:
                req_shape = (1,) + tuple(mix.shape)
            else:
                req_shape = (len(config.training.instruments),) + tuple(mix.shape)

            mix = mix.to(device)
            result = torch.zeros(req_shape, dtype=torch.float32, device=device)
            counter = torch.zeros(req_shape, dtype=torch.float32, device=device)

            i = 0
            total_length = mix.shape[1]
            num_chunks = (total_length + step - 1) // step

            if first_chunk_time is None:
                first_chunk = True
            else:
                first_chunk = False

            while i < total_length:
                part = mix[:, i : i + C]
                length = part.shape[-1]
                if length < C:
                    if length > C // 2 + 1:
                        part = nn.functional.pad(input=part, pad=(0, C - length), mode="reflect")
                    else:
                        part = nn.functional.pad(
                            input=part, pad=(0, C - length, 0, 0), mode="constant", value=0
                        )
                if model_dtype != torch.float32:
                    part = part.to(dtype=model_dtype)

                x = model(part.unsqueeze(0))[0]
                if x.dtype != torch.float32:
                    x = x.float()

                window = windowing_array.clone()
                if i == 0:
                    window[:fade_size] = 1
                elif i + C >= total_length:
                    window[-fade_size:] = 1

                result[..., i : i + length] += x[..., :length] * window[..., :length]
                counter[..., i : i + length] += window[..., :length]
                i += step

                if first_chunk and i == step:
                    first_chunk = False

            estimated_sources = result / counter
            estimated_sources = estimated_sources.cpu().numpy()
            np.nan_to_num(estimated_sources, copy=False, nan=0.0)

            if mix.shape[1] > 2 * border and border > 0:
                estimated_sources = estimated_sources[..., border:-border]

    if config.training.target_instrument is None:
        return {
            k: v for k, v in zip(config.training.instruments, estimated_sources)
        }, first_chunk_time
    return {
        k: v for k, v in zip([config.training.target_instrument], estimated_sources)
    }, first_chunk_time


def _path_md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _load_config(config_path: Path) -> ConfigDict:
    with config_path.open() as f:
        return ConfigDict(yaml.load(f, Loader=yaml.FullLoader))


def _load_model(
    *,
    config_path: Path,
    model_path: Path,
    is_gpu: bool,
    device_ids: Union[int, List[int]] = 0,
    chunk_size: Optional[int] = None,
    dtype: Optional[Union[str, torch.dtype]] = None,
    flash_attn: Optional[bool] = None,
):
    torch.backends.cudnn.benchmark = True
    config = _load_config(config_path)
    _apply_inference_knobs(config, chunk_size=chunk_size, flash_attn=flash_attn)
    model = get_model_from_config(_MODEL_TYPE, config)
    if model_path.is_file():
        try:
            state = torch.load(
                str(model_path),
                map_location=torch.device("cpu"),
                weights_only=True,
            )
        except TypeError:
            state = torch.load(str(model_path), map_location=torch.device("cpu"))
        model.load_state_dict(state)
        del state
        gc.collect()

    if not is_gpu:
        device = torch.device("cpu")
        model = model.to(device)
    elif torch.cuda.is_available():
        if isinstance(device_ids, int):
            device_ids = [device_ids]
        device = torch.device("cuda:%d" % device_ids[0])
        if len(device_ids) > 1:
            model = nn.DataParallel(model, device_ids=device_ids).to(device)
        else:
            model = model.to(device)
    else:
        device = torch.device("cpu")
        model = model.to(device)

    resolved = _resolve_torch_dtype(dtype)
    if resolved is not None and resolved != torch.float32:
        model = model.to(dtype=resolved)
        gc.collect()

    model.eval()
    return model, config, device


def _knobs_from_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    params = dict(params or {})
    knobs: Dict[str, Any] = {}
    if params.get("chunk_size") is not None:
        knobs["chunk_size"] = int(params["chunk_size"])
    if params.get("dtype") is not None:
        knobs["dtype"] = params["dtype"]
    if params.get("flash_attn") is not None:
        knobs["flash_attn"] = bool(params["flash_attn"])
    return knobs


def _stem_paths(
    store_dir: Path,
    input_path: Path,
    instruments: List[str],
) -> Tuple[Dict[str, Path], Path]:
    md5 = _path_md5(str(input_path.resolve()))
    stem = input_path.stem
    vocal_key = instruments[0]
    vocal_path = store_dir / ("%s_%s_%s.wav" % (md5, stem, vocal_key))
    inst_path = store_dir / ("%s_%s_instrumental.wav" % (md5, stem))
    return {vocal_key: vocal_path, "instrumental": inst_path}, inst_path


def run_folder(
    model,
    config,
    device,
    input_path: Path,
    store_dir: Path,
    *,
    select: SelectStem = "vocal",
) -> List[Path]:
    """Process one input file; write selected stem(s) under store_dir."""
    store_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    mix, sr = sf.read(str(input_path))
    original_mono = False
    if mix.ndim == 1:
        original_mono = True
        mix = np.stack([mix, mix], axis=-1)

    mixture = torch.tensor(mix.T, dtype=torch.float32)
    res, _ = demix_track(config, model, mixture, device)

    instruments = list(config.training.instruments)
    if config.training.target_instrument is not None:
        instruments = [config.training.target_instrument]

    stem_paths, inst_path = _stem_paths(store_dir, input_path, instruments)
    vocal_key = instruments[0]
    vocal_arr = res[vocal_key].T
    if original_mono:
        vocal_arr = vocal_arr[:, 0]

    vocal_path = stem_paths[vocal_key]
    sf.write(str(vocal_path), vocal_arr, sr, subtype="FLOAT")

    original_mix, _ = sf.read(str(input_path))
    instrumental = original_mix - vocal_arr
    sf.write(str(inst_path), instrumental, sr, subtype="FLOAT")

    if select == "vocal":
        return [vocal_path]
    if select == "instrumental":
        return [inst_path]
    return [vocal_path, inst_path]


def separate_array(
    audio: np.ndarray,
    sample_rate: int,
    *,
    model_path: Path,
    config_path: Path,
    select: SelectStem = "vocal",
    is_gpu: bool = False,
    device_ids: Union[int, List[int]] = 0,
    lib_path: Optional[Path] = None,
    chunk_size: Optional[int] = None,
    dtype: Optional[Union[str, torch.dtype]] = None,
    flash_attn: Optional[bool] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[np.ndarray, int]:
    """Separate in-memory audio; return selected stem waveform."""
    ensure_melband_import(lib_path)
    knobs = _knobs_from_params(params)
    if chunk_size is not None:
        knobs["chunk_size"] = int(chunk_size)
    if dtype is not None:
        knobs["dtype"] = dtype
    if flash_attn is not None:
        knobs["flash_attn"] = bool(flash_attn)
    model, config, device = _load_model(
        config_path=Path(config_path),
        model_path=Path(model_path),
        is_gpu=is_gpu,
        device_ids=device_ids,
        **knobs,
    )

    mix = np.asarray(audio, dtype=np.float32)
    original_mono = mix.ndim == 1
    if original_mono:
        mix_stereo = np.stack([mix, mix], axis=-1)
    elif mix.ndim == 2 and mix.shape[0] == 2:
        mix_stereo = mix.T
    else:
        mix_stereo = mix

    mixture = torch.tensor(mix_stereo.T, dtype=torch.float32)
    res, _ = demix_track(config, model, mixture, device)

    instruments = list(config.training.instruments)
    if config.training.target_instrument is not None:
        instruments = [config.training.target_instrument]
    vocal_key = instruments[0]
    vocal_arr = res[vocal_key].T
    if original_mono:
        vocal_arr = vocal_arr[:, 0]

    if select == "vocal":
        return vocal_arr, int(sample_rate)
    if select == "instrumental":
        original_mix = mix if not original_mono else mix
        instrumental = original_mix - vocal_arr
        return instrumental, int(sample_rate)
    return vocal_arr, int(sample_rate)


def separate_file(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    *,
    model_path: Union[str, Path],
    config_path: Union[str, Path],
    select: SelectStem = "vocal",
    is_gpu: bool = False,
    device_ids: Union[int, List[int]] = 0,
    lib_path: Optional[Path] = None,
    chunk_size: Optional[int] = None,
    dtype: Optional[Union[str, torch.dtype]] = None,
    flash_attn: Optional[bool] = None,
    params: Optional[Dict[str, Any]] = None,
) -> List[Path]:
    """Separate one file; return paths for the requested stem(s)."""
    ensure_melband_import(lib_path)
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    model_path = Path(model_path)
    config_path = Path(config_path)
    knobs = _knobs_from_params(params)
    if chunk_size is not None:
        knobs["chunk_size"] = int(chunk_size)
    if dtype is not None:
        knobs["dtype"] = dtype
    if flash_attn is not None:
        knobs["flash_attn"] = bool(flash_attn)

    if not config_path.is_file():
        raise FileNotFoundError("config not found: %s" % config_path)
    if not model_path.is_file():
        raise FileNotFoundError("checkpoint not found: %s" % model_path)

    model, config, device = _load_model(
        config_path=config_path,
        model_path=model_path,
        is_gpu=is_gpu,
        device_ids=device_ids,
        **knobs,
    )
    return run_folder(
        model,
        config,
        device,
        input_path,
        output_dir,
        select=select,
    )


def resolve_checkpoint(
    *,
    lib_path: Path,
    upstream_ref: str,
    params: Optional[Dict[str, Any]] = None,
    weight_paths: Optional[Dict[str, Path]] = None,
) -> Path:
    """Resolve checkpoint from params, env, cache, or weight_paths."""
    params = dict(params or {})
    explicit = params.get("model_path")
    if explicit:
        path = Path(str(explicit)).expanduser()
        if path.is_file():
            return path.resolve()

    env_key = "TAUDIO_MELBAND_VOCALS_CKPT"
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        path = Path(env_val).expanduser()
        if path.is_file():
            return path.resolve()

    if weight_paths:
        for p in weight_paths.values():
            p = Path(p)
            if p.is_file():
                return p.resolve()

    cache_name = upstream_ref or "MelBandRoformer.ckpt"
    cache_path = Path.home() / ".cache" / "taudio-models" / "models" / cache_name
    if cache_path.is_file():
        return cache_path.resolve()

    under_lib = lib_path / cache_name
    if under_lib.is_file():
        return under_lib.resolve()

    raise FileNotFoundError(
        "MelBand RoFormer checkpoint not found (tried params.model_path, %s, cache). "
        "Place %s on ECS or pass model_path=."
        % (env_key, cache_name)
    )


def resolve_config_path(
    *,
    lib_path: Path,
    config_rel: str,
    params: Optional[Dict[str, Any]] = None,
) -> Path:
    params = dict(params or {})
    explicit = params.get("config_path")
    if explicit:
        path = Path(str(explicit)).expanduser()
        if path.is_file():
            return path.resolve()
    path = lib_path / config_rel
    if path.is_file():
        return path.resolve()
    fallback = default_config_path(lib_path)
    if fallback.is_file():
        return fallback.resolve()
    raise FileNotFoundError("config not found: %s" % config_rel)
