# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Bandit backend — thin glue over vendored libs/banditv (Apache-2.0)."""

from __future__ import annotations

import glob
import hashlib
import itertools
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_LOOKUP = {
    "db48": "dnr-3s-bark48-l1snr.ckpt",
    "db64": "dnr-3s-bark64-l1snr.ckpt",
}


def _find_yaml(model_dir: Path, model_filename: str) -> Path:
    target = Path(model_filename).with_suffix(".yaml").name
    for root, _dirs, files in os.walk(str(model_dir)):
        if target in files:
            return Path(root) / target
    raise FileNotFoundError(
        "bandit yaml not found for %s under %s" % (target, model_dir)
    )


def _resolve_ckpt(model_dir: Path, model_filename: str) -> Tuple[Path, Path]:
    ckpt_path = model_dir / model_filename
    if ckpt_path.is_dir():
        last = ckpt_path / "checkpoints" / "last.ckpt"
        if last.is_file():
            return last, ckpt_path
        ckpts = sorted(glob.glob(str(ckpt_path / "checkpoints" / "*.ckpt")))
        if not ckpts:
            raise FileNotFoundError("no checkpoints under %s" % ckpt_path)
        return Path(ckpts[-1]), ckpt_path
    if not ckpt_path.is_file():
        raise FileNotFoundError("bandit checkpoint missing: %s" % ckpt_path)
    return ckpt_path, model_dir


def ensure_bandit_import(lib_path: Optional[Path] = None) -> Any:
    """Put vendored banditv root on sys.path; return LightningSystem."""
    import sys
    import types

    # Inference-only stubs for optional training-time deps pulled by core/__init__.
    # Do NOT stub packages that torch._dynamo may probe (e.g. pandas).
    import importlib.machinery

    for name in (
        "pedalboard",
        "gooptim",
        "torch_audiomentations",
        "asteroid_filterbanks",
        "spafe",
    ):
        if name not in sys.modules:
            try:
                __import__(name)
            except ImportError:
                mod = types.ModuleType(name)
                mod.__spec__ = importlib.machinery.ModuleSpec(name, None)
                sys.modules[name] = mod

    if lib_path is not None:
        lib_path = Path(lib_path).resolve()
        if lib_path.is_dir():
            root = str(lib_path)
            if root not in sys.path:
                sys.path.insert(0, root)
            os.environ.setdefault("PROJECT_ROOT", root)
    from core import LightningSystem  # type: ignore

    return LightningSystem


def _select_stem_path(
    outresults: Dict[str, Any], get_name: str
) -> Optional[Path]:
    parts = [p for p in str(get_name).split("+") if p]
    if not parts:
        return None
    for perm in itertools.permutations(parts):
        key = "+".join(perm)
        if key in outresults:
            val = outresults[key]
            return Path(val) if not isinstance(val, Path) else val
    return None


def separate_file(
    input_path: Path,
    output_dir: Path,
    *,
    params: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    lib_path: Optional[Path] = None,
    model_dir: Optional[Path] = None,
) -> List[Path]:
    """Run BanditIV inference; return selected stem wav path(s)."""
    import shutil

    import torch
    import torchaudio as ta

    params = dict(params or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    model_code = str(params.get("m") or params.get("model") or "db48")
    if model_code not in MODEL_LOOKUP:
        raise ValueError("unknown bandit model code: %s" % model_code)
    model_filename = MODEL_LOOKUP[model_code]

    if model_dir is None:
        raw = params.get("model_dir") or params.get("model_path")
        if raw:
            model_dir = Path(raw)
        elif lib_path is not None:
            # weights live beside or under BanditIV cache, not in source tree
            model_dir = Path(lib_path).resolve().parent.parent / "BanditIV"
        else:
            model_dir = Path("BanditIV")
    model_dir = Path(model_dir).resolve()
    if not model_dir.is_dir():
        raise FileNotFoundError(
            "bandit model_dir missing: %s (set params.model_dir or TAUDIO_BANDIT_DIR)"
            % model_dir
        )

    LightningSystem = ensure_bandit_import(lib_path)
    from utils.config import read_nested_yaml  # type: ignore

    ckpt, _ckpt_dir = _resolve_ckpt(model_dir, model_filename)
    yaml_path = _find_yaml(model_dir, model_filename)
    config = read_nested_yaml(str(yaml_path))

    import pytorch_lightning as pl

    pl.seed_everything(seed=config.get("seed", 42), workers=True)

    get_residual = str(params.get("gr", 0)).strip() in ("1", "true", "True")
    get_no_vox = str(params.get("gnv", 0)).strip() in ("1", "true", "True")
    get_no_muc = str(params.get("gnm", 1)).strip() not in ("0", "false", "False")
    include_track_name = str(params.get("itn", 0)).strip() in ("1", "true", "True")
    get_name = str(params.get("g") or params.get("get") or "speech")
    channel_filter = params.get("cf")

    device = torch.device(
        "cuda" if (is_gpu and torch.cuda.is_available()) else "cpu"
    )
    # mmap reduces peak during lightning pickle load when supported
    _orig = torch.load

    def _mmap_load(*args, **kwargs):
        kwargs.setdefault("map_location", "cpu")
        if "mmap" not in kwargs:
            try:
                return _orig(*args, mmap=True, **kwargs)
            except TypeError:
                pass
        return _orig(*args, **kwargs)

    torch.load = _mmap_load  # type: ignore[assignment]
    try:
        model = LightningSystem.load_from_checkpoint(
            str(ckpt),
            config=config["system"],
            map_location=device,
        )
    finally:
        torch.load = _orig  # type: ignore[assignment]

    model.to(device)
    sub = hashlib.md5(str(input_path.resolve()).encode("utf-8")).hexdigest()
    pred_dir = output_dir / ("%s_%s" % (sub, model_code))
    pred_dir.mkdir(parents=True, exist_ok=True)
    model.set_predict_output_path(str(pred_dir))
    model.fader.__init__(**config["system"]["inference"]["fader"]["kwargs"])  # type: ignore[misc]
    model.fader.to(model.device)  # type: ignore[arg-type]
    model.eval()

    audio, fs = ta.load(str(input_path))
    target_fs = int(config["system"]["model"]["kwargs"]["fs"])
    if int(fs) != target_fs:
        audio = ta.functional.resample(audio, int(fs), target_fs)
        fs = target_fs

    track_name = input_path.stem
    track = [track_name]
    treat_batch_as_channels = False
    if channel_filter is not None:
        if isinstance(channel_filter, int):
            channel_filter = [channel_filter]
        audio = audio[channel_filter, :]

    in_ch_audio = int(audio.shape[0])
    in_ch_model = int(config["system"]["model"]["kwargs"]["in_channel"])
    if in_ch_audio != in_ch_model:
        if in_ch_audio == 1 and in_ch_model > 1:
            audio = audio.repeat(in_ch_model, 1)
        elif in_ch_audio > 1 and in_ch_model == 1:
            audio = audio[:, None, :]
            treat_batch_as_channels = True
            track = ["%s_%d" % (track_name, i) for i in range(in_ch_audio)]
        else:
            raise ValueError(
                "channel mismatch audio=%s model=%s" % (in_ch_audio, in_ch_model)
            )
    if in_ch_audio == 1 and in_ch_model == 1:
        audio = audio[None, ...]

    audio = audio.to(model.device)
    with torch.inference_mode():
        outresults, _basenames = model.predict_step(
            {"audio": {"mixture": audio}, "track": track},
            get_residual=get_residual,
            get_no_vox_combinations=get_no_vox,
            get_no_muc_combinations=get_no_muc,
            include_track_name=include_track_name,
            treat_batch_as_channels=treat_batch_as_channels,
            fs=fs,
        )

    match = _select_stem_path(outresults or {}, get_name)
    if match is None or not Path(match).is_file():
        raise RuntimeError(
            "bandit stem %r not in results keys=%s"
            % (get_name, list((outresults or {}).keys()))
        )

    out_path = output_dir / (
        "%s_%s_bdiv.wav"
        % (
            hashlib.md5(str(input_path.resolve()).encode("utf-8")).hexdigest(),
            input_path.stem,
        )
    )
    if Path(match).resolve() != out_path.resolve():
        shutil.copy2(str(match), str(out_path))
    return [out_path]


def separate_array(
    audio: Any,
    sample_rate: int,
    *,
    params: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    lib_path: Optional[Path] = None,
    model_dir: Optional[Path] = None,
) -> Tuple[Any, int]:
    """Array path: write temp wav, run file path, read back."""
    import tempfile

    import numpy as np
    import soundfile as sf

    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 1:
        write = arr
    elif arr.ndim == 2:
        write = arr.T if arr.shape[0] <= 8 else arr
    else:
        raise ValueError("audio must be 1D or 2D")

    with tempfile.TemporaryDirectory(prefix="bandit_") as td:
        inp = Path(td) / "in.wav"
        out_dir = Path(td) / "out"
        sf.write(str(inp), write, int(sample_rate), subtype="FLOAT")
        outs = separate_file(
            inp,
            out_dir,
            params=params,
            is_gpu=is_gpu,
            lib_path=lib_path,
            model_dir=model_dir,
        )
        y, sr = sf.read(str(outs[0]), always_2d=True, dtype="float32")
        return y.T, int(sr)
