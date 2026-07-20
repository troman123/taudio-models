# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""DeepFilterNet backend — prefer pip package (deepfilternet), optional vendor tree."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def ensure_deepfilter_import(lib_path: Optional[Path] = None) -> None:
    """
    Optionally prepend a vendored libs/DeepFilterNet tree.

    Easiest path for users: `pip install deepfilternet` (no vendor needed).
    """
    if lib_path is None:
        return
    lib_path = Path(lib_path).resolve()
    if not lib_path.is_dir():
        return
    # Only useful if Python package `df` lives here
    if not (lib_path / "df").is_dir():
        return
    root = str(lib_path)
    if root not in sys.path:
        sys.path.insert(0, root)


def _stock_enhance_main(**kwargs: Any) -> List[str]:
    """Implement enhance_main using published deepfilternet (df.enhance) API."""
    from df.enhance import enhance, init_df, maybe_download_model  # type: ignore
    from df.io import load_audio, resample, save_audio  # type: ignore
    from df.model import ModelParams  # type: ignore

    model_base_dir = kwargs.get("model_base_dir") or "DeepFilterNet3"
    noisy_audio_files = kwargs.get("noisy_audio_files") or []
    output_dir = kwargs.get("output_dir") or "."
    pf = bool(kwargs.get("pf", False))
    log_level = str(kwargs.get("log_level", "ERROR"))
    use_suffix = bool(kwargs.get("suffix", True))
    atten_lim = kwargs.get("atten_lim")
    compensate_delay = bool(kwargs.get("compensate_delay", True))

    maybe_download_model(str(model_base_dir) if str(model_base_dir) in (
        "DeepFilterNet", "DeepFilterNet2", "DeepFilterNet3"
    ) else "DeepFilterNet3")

    model, df_state, model_suffix, _ = init_df(
        model_base_dir=model_base_dir,
        post_filter=pf,
        log_level=log_level,
        config_allow_defaults=True,
    )
    suffix = model_suffix if use_suffix else None
    os.makedirs(output_dir, exist_ok=True)

    df_sr = ModelParams().sr
    outs: List[str] = []
    for path in noisy_audio_files:
        audio, meta = load_audio(path, df_sr)
        # load_audio may return batch-less [C, T]
        enhanced = enhance(
            model,
            df_state,
            audio,
            pad=compensate_delay,
            atten_lim_db=atten_lim,
        )
        orig_sr = getattr(meta, "sample_rate", df_sr)
        if orig_sr != df_sr:
            enhanced = resample(enhanced.to("cpu"), df_sr, orig_sr)
        else:
            enhanced = enhanced.to("cpu")
        save_audio(
            path,
            enhanced,
            sr=orig_sr,
            output_dir=output_dir,
            suffix=suffix,
            log=False,
        )
        base = os.path.basename(path)
        if suffix:
            stem, ext = os.path.splitext(base)
            out_name = f"{stem}_{suffix}{ext}"
        else:
            out_name = base
        outs.append(os.path.join(output_dir, out_name))
    return outs


def _import_enhance_main():
    """Return enhance_main callable (vendored enhance_call or stock pip)."""
    try:
        from df.enhance_call import enhance_main  # type: ignore

        return enhance_main
    except ImportError:
        pass
    try:
        import df.enhance  # noqa: F401

        return _stock_enhance_main
    except ImportError as e:
        raise ImportError(
            "DeepFilterNet not importable. Easiest fix:\n"
            "  pip install 'taudio-models[denoise]'\n"
            "or: pip install deepfilternet\n"
            "Original error: %s" % e
        ) from e


def ensure_upstream_weights(upstream_ref: str, lib_path: Optional[Path] = None) -> Path:
    """Download pretrained DF model dir via upstream helper (weights not in git)."""
    ensure_deepfilter_import(lib_path)
    try:
        from df.enhance import maybe_download_model  # type: ignore
    except ImportError:
        from df.enhance_call import maybe_download_model  # type: ignore
    return Path(maybe_download_model(upstream_ref))


def enhance_file(
    input_path: Path,
    output_dir: Path,
    *,
    upstream_ref: str = "DeepFilterNet3",
    lib_path: Optional[Path] = None,
    is_gpu: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> List[Path]:
    """
    Run DeepFilterNet on one file.

    Preferred install for users/CI:
      pip install deepfilternet
    Optional vendor tree under libs/DeepFilterNet is supported when present.
    """
    _ = is_gpu  # stock CPU/GPU chosen inside df via torch; kept for API compat
    params = dict(params or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    ensure_deepfilter_import(lib_path)
    enhance_main = _import_enhance_main()

    outs = enhance_main(
        model_base_dir=upstream_ref,
        noisy_audio_files=[str(input_path)],
        output_dir=str(output_dir),
        pf=bool(params.get("pf", False)),
        atten_lim=params.get("atten_lim"),
        suffix=bool(params.get("suffix", True)),
        log_level=str(params.get("log_level", "ERROR")),
        compensate_delay=bool(params.get("compensate_delay", True)),
        is_gpu=bool(params.get("is_gpu", False)),
    )
    return [Path(p) for p in (outs or [])]
