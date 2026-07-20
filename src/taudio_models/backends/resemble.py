# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Resemble Enhance backend — thin glue over libs/resemble_enhancev (MIT)."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def ensure_resemble_import(lib_path: Optional[Path] = None) -> None:
    if lib_path is None:
        return
    lib_path = Path(lib_path).resolve()
    if not lib_path.is_dir():
        return
    # Parent of package so `import resemble_enhancev` works.
    parent = str(lib_path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)


def enhance_file(
    input_path: Path,
    output_dir: Path,
    *,
    params: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    lib_path: Optional[Path] = None,
    run_dir: Optional[Path] = None,
) -> List[Path]:
    import torch
    import torchaudio

    params = dict(params or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    ensure_resemble_import(lib_path)
    from resemble_enhancev.enhancer.inference import denoise, enhance  # type: ignore

    if run_dir is None:
        raw = params.get("run_dir") or params.get("model_dir") or os.environ.get(
            "TAUDIO_REENH_DIR"
        )
        if raw:
            run_dir = Path(raw)
        else:
            model_name = str(params.get("m") or "enhancer_stage2")
            root = os.environ.get("TAUDIO_MODELS_ROOT")
            if root:
                run_dir = Path(root) / "ResembleEnhance" / model_name
            else:
                run_dir = None

    device = torch.device(
        "cuda" if (is_gpu and torch.cuda.is_available()) else "cpu"
    )
    denoise_only = str(params.get("de", 0)).strip() in ("1", "true", "True")
    lambd = float(params.get("la", params.get("lambd", 1.0)))
    tau = float(params.get("tau", 0.5))
    nfe = int(params.get("nfe", 64))
    solver = str(params.get("sl", params.get("solver", "midpoint")))
    chunk_seconds = float(params.get("chunk_seconds", 30.0))
    overlap_seconds = float(params.get("overlap_seconds", 1.0))

    dwav, sr = torchaudio.load(str(input_path))
    dwav = dwav.mean(dim=0)
    run_dir_s = str(run_dir) if run_dir is not None else None
    if denoise_only:
        hwav, out_sr = denoise(
            dwav,
            int(sr),
            device,
            run_dir=run_dir_s,
            chunk_seconds=chunk_seconds,
            overlap_seconds=overlap_seconds,
        )
    else:
        hwav, out_sr = enhance(
            dwav,
            int(sr),
            device,
            nfe=nfe,
            solver=solver,
            lambd=lambd,
            tau=tau,
            run_dir=run_dir_s,
            chunk_seconds=chunk_seconds,
            overlap_seconds=overlap_seconds,
        )

    md5 = hashlib.md5(str(input_path.resolve()).encode("utf-8")).hexdigest()
    out_path = output_dir / ("%s_%s_reenh.wav" % (md5, input_path.stem))
    torchaudio.save(str(out_path), hwav[None], int(out_sr))
    return [out_path]


def enhance_array(
    audio: Any,
    sample_rate: int,
    *,
    params: Optional[Dict[str, Any]] = None,
    is_gpu: bool = False,
    lib_path: Optional[Path] = None,
    run_dir: Optional[Path] = None,
) -> Tuple[Any, int]:
    import tempfile

    import numpy as np
    import soundfile as sf

    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 2:
        write = arr.T if arr.shape[0] <= 8 else arr
    else:
        write = arr
    with tempfile.TemporaryDirectory(prefix="reenh_") as td:
        inp = Path(td) / "in.wav"
        out_dir = Path(td) / "out"
        sf.write(str(inp), write, int(sample_rate), subtype="FLOAT")
        outs = enhance_file(
            inp,
            out_dir,
            params=params,
            is_gpu=is_gpu,
            lib_path=lib_path,
            run_dir=run_dir,
        )
        y, sr = sf.read(str(outs[0]), always_2d=True, dtype="float32")
        return y.T, int(sr)
