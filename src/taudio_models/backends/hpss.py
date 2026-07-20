# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""HPSS backend — thin glue over librosa.decompose.hpss (source bashmodule.hpss_*)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

SelectStem = Literal["harmonic", "percussive", "both"]


def _resolve_select(params: Optional[Dict[str, Any]]) -> SelectStem:
    raw = str((params or {}).get("select") or "harmonic").strip().lower()
    if raw in ("percussive", "perc", "p"):
        return "percussive"
    if raw in ("both", "hp", "iv"):
        return "both"
    return "harmonic"


def _hpss_channel(x: Any, *, n_fft: int, hop: int, ksz: int) -> Tuple[Any, Any]:
    import librosa
    import numpy as np

    x = np.asarray(x, dtype=np.float32)
    if not np.isfinite(x).all():
        x = np.nan_to_num(x)
    S = librosa.stft(x, n_fft=n_fft, hop_length=hop, window="hann")
    try:
        Hc, Pc = librosa.decompose.hpss(S, kernel_size=(ksz | 1, ksz | 1))
    except TypeError:
        mag = np.abs(S)
        H, P = librosa.decompose.hpss(mag, kernel_size=(ksz | 1, ksz | 1))
        phase = np.exp(1j * np.angle(S))
        Hc, Pc = H * phase, P * phase
    y_h = librosa.istft(Hc, hop_length=hop, window="hann", length=len(x))
    y_p = librosa.istft(Pc, hop_length=hop, window="hann", length=len(x))
    return y_h.astype(np.float32), y_p.astype(np.float32)


def _hpss_stereo(lr: Any, *, n_fft: int, hop: int, ksz: int) -> Tuple[Any, Any]:
    import numpy as np

    L_h, L_p = _hpss_channel(lr[0], n_fft=n_fft, hop=hop, ksz=ksz)
    R_h, R_p = _hpss_channel(lr[1], n_fft=n_fft, hop=hop, ksz=ksz)
    return np.stack([L_h, R_h]), np.stack([L_p, R_p])


def _read_stereo(path: Path) -> Tuple[Any, int]:
    import numpy as np
    import soundfile as sf

    y, sr = sf.read(str(path), always_2d=True, dtype="float32")
    if y.ndim != 2 or y.size == 0:
        raise ValueError("failed to read audio: %s" % path)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return y.T[:2].astype(np.float32), int(sr)


def _write_stereo(path: Path, lr: Any, sr: int) -> None:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), lr.T, sr, subtype="FLOAT")


def separate_array(
    audio: Any,
    sample_rate: int,
    *,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, int]:
    import numpy as np

    params = dict(params or {})
    n_fft = int(params.get("n_fft") or 4096)
    hop = int(params.get("hop") or 1024)
    ksz = int(params.get("ksz") or 31)
    select = _resolve_select(params)

    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 1:
        lr = np.stack([arr, arr])
        mono = True
    elif arr.ndim == 2:
        if arr.shape[0] == 2:
            lr = arr
        elif arr.shape[1] == 2:
            lr = arr.T
        else:
            raise ValueError("audio must be mono or stereo")
        mono = False
    else:
        raise ValueError("audio must be 1D or 2D")

    harm, perc = _hpss_stereo(lr, n_fft=n_fft, hop=hop, ksz=ksz)
    if select == "percussive":
        out = perc
    elif select == "both":
        # Return harmonic as primary when array path asks for both.
        out = harm
    else:
        out = harm
    if mono:
        out = out.mean(axis=0)
    return out, int(sample_rate)


def separate_file(
    input_path: Path,
    output_dir: Path,
    *,
    params: Optional[Dict[str, Any]] = None,
) -> List[Path]:
    import numpy as np

    params = dict(params or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    n_fft = int(params.get("n_fft") or 4096)
    hop = int(params.get("hop") or 1024)
    ksz = int(params.get("ksz") or 31)
    select = _resolve_select(params)

    lr, sr = _read_stereo(input_path)
    harm, perc = _hpss_stereo(lr, n_fft=n_fft, hop=hop, ksz=ksz)

    md5 = hashlib.md5(str(input_path.resolve()).encode("utf-8")).hexdigest()
    stem = input_path.stem
    harm_path = output_dir / ("%s_%s_harmonic.wav" % (md5, stem))
    perc_path = output_dir / ("%s_%s_percussive.wav" % (md5, stem))
    _write_stereo(harm_path, harm.astype(np.float32), sr)
    _write_stereo(perc_path, perc.astype(np.float32), sr)

    if select == "percussive":
        return [perc_path]
    if select == "both":
        return [harm_path, perc_path]
    return [harm_path]
