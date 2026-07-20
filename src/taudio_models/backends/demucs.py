# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Demucs backend — thin glue over pip/vendored demucs.api.Separator."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _install_runtime_stubs() -> None:
    """Provide minimal dora/julius stubs so demucsv inference can import offline."""
    import sys
    import types

    if "dora.log" not in sys.modules:
        dora = types.ModuleType("dora")
        dora_log = types.ModuleType("dora.log")

        def fatal(*args, **kwargs):  # noqa: ARG001
            raise RuntimeError(args[0] if args else "fatal")

        def bold(text):
            return str(text)

        class LogProgress:  # noqa: D401
            def __init__(self, *args, **kwargs):  # noqa: ARG002
                pass

            def __iter__(self):
                return iter(())

            def update(self, *args, **kwargs):  # noqa: ARG002
                return None

        dora_log.fatal = fatal
        dora_log.bold = bold
        dora_log.LogProgress = LogProgress
        dora.fatal = fatal
        dora.hydra_main = lambda *a, **k: (lambda fn: fn)
        sys.modules["dora"] = dora
        sys.modules["dora.log"] = dora_log

    if "julius" not in sys.modules:
        try:
            import julius  # noqa: F401
        except ImportError:
            julius = types.ModuleType("julius")

            def resample_frac(wav, from_sr, to_sr):
                import torchaudio

                if int(from_sr) == int(to_sr):
                    return wav
                return torchaudio.functional.resample(wav, int(from_sr), int(to_sr))

            julius.resample_frac = resample_frac
            sys.modules["julius"] = julius

    if "openunmix" not in sys.modules:
        try:
            import openunmix  # noqa: F401
        except ImportError:
            openunmix = types.ModuleType("openunmix")
            filtering = types.ModuleType("openunmix.filtering")

            def wiener(*args, **kwargs):  # noqa: ARG001
                raise RuntimeError(
                    "openunmix.filtering.wiener unavailable; install openunmix "
                    "for Wiener-filtered Demucs bags"
                )

            filtering.wiener = wiener
            openunmix.filtering = filtering
            sys.modules["openunmix"] = openunmix
            sys.modules["openunmix.filtering"] = filtering
        try:
            import omegaconf  # noqa: F401
        except ImportError:
            omegaconf = types.ModuleType("omegaconf")

            class OmegaConf:  # noqa: D401
                @staticmethod
                def to_container(obj, resolve=True):  # noqa: ARG001
                    if isinstance(obj, dict):
                        return dict(obj)
                    return obj

                @staticmethod
                def create(obj=None):
                    return obj if obj is not None else {}

            omegaconf.OmegaConf = OmegaConf
            sys.modules["omegaconf"] = omegaconf


def ensure_demucs_import(lib_path: Optional[Path] = None) -> Any:
    """Import Separator; prefer vendored demucsv when lib_path is set."""
    import sys

    _install_runtime_stubs()
    if lib_path is not None:
        lib_path = Path(lib_path).resolve()
        if lib_path.is_dir():
            # libs/ on path so `import demucsv` works; do NOT add demucsv/ itself
            # (that shadows package name `demucs` with demucsv/demucs.py).
            parent = str(lib_path.parent)
            if parent not in sys.path:
                sys.path.insert(0, parent)
    demucsv_err = None
    try:
        from demucsv.api import Separator  # type: ignore

        return Separator
    except ImportError as e:
        demucsv_err = e
    try:
        from demucs.api import Separator  # type: ignore

        return Separator
    except ImportError as e:
        raise ImportError(
            "Demucs not available (demucsv=%s; demucs=%s). "
            "Vendor libs/demucsv under models root or pip install demucs."
            % (demucsv_err, e)
        ) from e


def _as_ct(audio: Any) -> Any:
    import numpy as np

    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 1:
        return np.stack([arr, arr])
    if arr.ndim == 2:
        if arr.shape[0] <= 8 and arr.shape[0] < arr.shape[1]:
            if arr.shape[0] == 1:
                return np.vstack([arr, arr])
            return arr[:2]
        if arr.shape[1] <= 8:
            t = arr.T
            if t.shape[0] == 1:
                return np.vstack([t, t])
            return t[:2]
    raise ValueError("audio must be mono or stereo")


def _ensure_ct_tensor(t: Any) -> Any:
    import torch

    if not torch.is_tensor(t):
        t = torch.as_tensor(t)
    if t.dim() == 3 and t.size(0) == 1:
        return t.squeeze(0)
    return t


def _rms_dbfs(t: Any, sr: int) -> float:
    import torch

    x = t.detach().float()
    if x.numel() == 0:
        return -120.0
    rms = torch.sqrt(torch.mean(x * x) + 1e-12)
    return float(20.0 * torch.log10(rms + 1e-12))


def separate_stems_array(
    audio: Any,
    sample_rate: int,
    *,
    params: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    lib_path: Optional[Path] = None,
) -> Tuple[Any, int]:
    """Return instrumental mix (non-vocal stems) matching source demucs_filter mute path."""
    import numpy as np
    import torch

    params = dict(params or {})
    model_name = str(params.get("model") or params.get("m") or "hdemucs_mmi")
    harmonic = bool(params.get("harmonic", params.get("hm", True)))
    if isinstance(harmonic, (int, str)):
        harmonic = str(harmonic).strip() not in ("0", "false", "False", "")
    ivocals = bool(params.get("ivocals", params.get("ivol", False)))
    if "ivol" in params:
        ivocals = str(params.get("ivol")).strip() in ("1", "true", "True", "yes")
    iother = True
    if "iot" in params:
        iother = str(params.get("iot")).strip() not in ("0", "false", "False")
    elif "iother" in params:
        iother = bool(params.get("iother"))
    filterdb = bool(params.get("filterdb", True))

    Separator = ensure_demucs_import(lib_path)
    separator = Separator(model=model_name)
    lr = _as_ct(audio)
    device = "cuda" if (is_gpu and torch.cuda.is_available()) else "cpu"
    wav = torch.from_numpy(lr)
    if device == "cuda":
        wav = wav.cuda()

    out = separator.separate_tensor(wav, int(sample_rate))
    stems = out[1] if isinstance(out, (tuple, list)) and len(out) >= 2 else out
    if not isinstance(stems, dict):
        raise TypeError("unexpected demucs return: %s" % type(stems))
    if "vocals" not in stems:
        raise KeyError("demucs stems missing vocals: %s" % list(stems))

    instrumental = None
    for name, tensor in stems.items():
        t = _ensure_ct_tensor(tensor)
        n = str(name).lower()
        avg_db = _rms_dbfs(t, int(sample_rate))
        if not ivocals and n == "vocals":
            continue
        if (not iother or not harmonic) and n == "other":
            continue
        if filterdb and harmonic and n == "drums" and avg_db <= -47:
            continue
        instrumental = t if instrumental is None else instrumental + t

    if instrumental is None:
        instrumental = torch.zeros_like(_ensure_ct_tensor(stems["vocals"]))

    out_np = instrumental.detach().cpu().numpy().astype(np.float32)
    return out_np, int(sample_rate)


def separate_file(
    input_path: Path,
    output_dir: Path,
    *,
    params: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    lib_path: Optional[Path] = None,
) -> List[Path]:
    import soundfile as sf

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    y, sr = sf.read(str(input_path), always_2d=True, dtype="float32")
    audio = y.T
    out, out_sr = separate_stems_array(
        audio, int(sr), params=params, is_gpu=is_gpu, lib_path=lib_path
    )

    md5 = hashlib.md5(str(input_path.resolve()).encode("utf-8")).hexdigest()
    out_path = output_dir / ("%s_%s_dmiv.wav" % (md5, input_path.stem))
    if out.ndim == 1:
        sf.write(str(out_path), out, out_sr, subtype="FLOAT")
    else:
        sf.write(str(out_path), out.T, out_sr, subtype="FLOAT")
    return [out_path]


def separate_array(
    audio: Any,
    sample_rate: int,
    *,
    params: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    lib_path: Optional[Path] = None,
) -> Tuple[Any, int]:
    return separate_stems_array(
        audio, sample_rate, params=params, is_gpu=is_gpu, lib_path=lib_path
    )
