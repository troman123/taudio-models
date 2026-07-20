import logging
from functools import cache
from pathlib import Path

import torch

from ..inference import inference
from .download import download
from .enhancer import Enhancer
from .hparams import HParams

logger = logging.getLogger(__name__)


@cache
def load_enhancer(run_dir: str | Path | None, device):
    import gc

    run_dir = download(run_dir)
    print("run_dir", run_dir)
    hp = HParams.load(run_dir)
    enhancer = Enhancer(hp)
    path = run_dir / "ds" / "G" / "default" / "mp_rank_00_model_states.pt"
    # mmap reduces peak RAM on tiny hosts when loading the ~681MB DeepSpeed ckpt.
    try:
        blob = torch.load(path, map_location="cpu", mmap=True)
    except TypeError:
        blob = torch.load(path, map_location="cpu")
    state_dict = blob["module"]
    del blob
    enhancer.load_state_dict(state_dict)
    del state_dict
    gc.collect()
    enhancer.eval()
    enhancer.to(device)
    return enhancer


@torch.inference_mode()
def denoise(dwav, sr, device, run_dir=None, chunk_seconds=30.0, overlap_seconds=1.0):
    enhancer = load_enhancer(run_dir, device)
    return inference(
        model=enhancer.denoiser,
        dwav=dwav,
        sr=sr,
        device=device,
        chunk_seconds=chunk_seconds,
        overlap_seconds=overlap_seconds,
    )


@torch.inference_mode()
def enhance(
    dwav,
    sr,
    device,
    nfe=32,
    solver="midpoint",
    lambd=0.5,
    tau=0.5,
    run_dir=None,
    chunk_seconds=30.0,
    overlap_seconds=1.0,
):
    assert 0 < nfe <= 128, f"nfe must be in (0, 128], got {nfe}"
    assert solver in ("midpoint", "rk4", "euler"), f"solver must be in ('midpoint', 'rk4', 'euler'), got {solver}"
    assert 0 <= lambd <= 1, f"lambd must be in [0, 1], got {lambd}"
    assert 0 <= tau <= 1, f"tau must be in [0, 1], got {tau}"
    enhancer = load_enhancer(run_dir, device)
    enhancer.configurate_(nfe=nfe, solver=solver, lambd=lambd, tau=tau)
    return inference(
        model=enhancer,
        dwav=dwav,
        sr=sr,
        device=device,
        chunk_seconds=chunk_seconds,
        overlap_seconds=overlap_seconds,
    )
