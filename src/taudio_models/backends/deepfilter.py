# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""DeepFilterNet backend — thin glue over libs/DeepFilterNet (not a reimplementation).

Primary path: vendor tree at libs/DeepFilterNet (`df.enhance_call`).
Fallback: pip `deepfilternet` only for file I/O when enhance_call is absent.
Do not add inference logic here — extend libs or call through this glue.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def ensure_deepfilter_import(lib_path: Optional[Path] = None) -> None:
    """Prepend vendored libs/DeepFilterNet so `import df` resolves to the OSS tree.

    Vendored trees often ship a pure-Python ``libdf/`` stub without the compiled
    extension. Prefer an already-installed ``deepfilterlib`` (``libdf*.so``) by
    importing it *before* the vendored path can shadow it.
    """
    if lib_path is None:
        return
    lib_path = Path(lib_path).resolve()
    if not lib_path.is_dir():
        return
    if not (lib_path / "df").is_dir():
        return

    vendored_libdf = lib_path / "libdf"
    has_native = False
    if vendored_libdf.is_dir():
        has_native = any(vendored_libdf.glob("libdf*.so")) or any(
            vendored_libdf.glob("*.so")
        )
    if not has_native and "libdf" not in sys.modules:
        # Load pip/system libdf first so vendored stub cannot shadow the .so.
        try:
            import libdf  # noqa: F401
        except ImportError:
            pass

    root = str(lib_path)
    if root not in sys.path:
        sys.path.insert(0, root)


def _import_error(detail: str) -> ImportError:
    return ImportError(
        "DeepFilterNet not available (%s).\n"
        "Preferred: vendor libs/DeepFilterNet (see scripts/vendor_deepfilternet.sh).\n"
        "Fallback: pip install 'taudio-models[denoise]' / deepfilternet."
        % detail
    )


def ensure_upstream_weights(upstream_ref: str, lib_path: Optional[Path] = None) -> Path:
    """Download pretrained DF model dir via upstream helper (weights not in git)."""
    ensure_deepfilter_import(lib_path)
    try:
        from df.enhance_call import maybe_download_model  # type: ignore
    except ImportError:
        try:
            from df.enhance import maybe_download_model  # type: ignore
        except ImportError as e:
            raise _import_error(str(e)) from e
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
    """Thin wrap: libs `df.enhance_call.enhance_main` (preferred)."""
    params = dict(params or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    ensure_deepfilter_import(lib_path)
    try:
        from df.enhance_call import enhance_main  # type: ignore
    except ImportError as e:
        raise _import_error(
            "df.enhance_call.enhance_main missing — use libs/DeepFilterNet: %s" % e
        ) from e

    outs = enhance_main(
        model_base_dir=upstream_ref,
        noisy_audio_files=[str(input_path)],
        output_dir=str(output_dir),
        pf=bool(params.get("pf", False)),
        atten_lim=params.get("atten_lim"),
        suffix=bool(params.get("suffix", True)),
        log_level=str(params.get("log_level", "ERROR")),
        compensate_delay=bool(params.get("compensate_delay", True)),
        is_gpu=bool(params.get("is_gpu", is_gpu)),
    )
    return [Path(p) for p in (outs or [])]


def enhance_array(
    audio: Any,
    sample_rate: int,
    *,
    upstream_ref: str = "DeepFilterNet3",
    lib_path: Optional[Path] = None,
    is_gpu: bool = False,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, int]:
    """
    Thin wrap: libs `init_enhancer` + `enhance_audio_data`.

    Returns (enhanced ndarray, sample_rate). No local inference reimplementation.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    params = dict(params or {})
    use_gpu = bool(params.get("is_gpu", is_gpu))

    ensure_deepfilter_import(lib_path)
    try:
        from df.enhance_call import (  # type: ignore
            get_model_basedir,
            init_enhancer,
            enhance_audio_data,
        )
    except ImportError as e:
        raise _import_error(
            "df.enhance_call PCM APIs missing — use libs/DeepFilterNet: %s" % e
        ) from e

    model_dir = get_model_basedir(upstream_ref)
    ctx = init_enhancer(
        model_base_dir=model_dir,
        pf=bool(params.get("pf", False)),
        log_level=str(params.get("log_level", "ERROR")),
        epoch=params.get("epoch", "best"),
        no_df_stage=bool(params.get("no_df_stage", False)),
        suffix=bool(params.get("suffix", True)),
        is_gpu=use_gpu,
    )
    if not ctx:
        raise RuntimeError(
            "init_enhancer failed for model_base_dir=%r (path missing?)" % model_dir
        )

    out = enhance_audio_data(
        audio,
        sample_rate,
        ctx,
        compensate_delay=bool(params.get("compensate_delay", True)),
        atten_lim=params.get("atten_lim"),
        is_gpu=use_gpu,
    )
    return out, int(sample_rate)
