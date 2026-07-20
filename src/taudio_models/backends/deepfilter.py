# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""DeepFilterNet backend helpers (public, generic)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def ensure_deepfilter_import(lib_path: Path) -> None:
    """
    Put vendored DeepFilterNet on sys.path.

    Expected layout:
      libs/DeepFilterNet/df/...
      libs/DeepFilterNet/libdf/...   # platform native ext (not committed .so)
    """
    lib_path = Path(lib_path).resolve()
    if not lib_path.is_dir():
        raise FileNotFoundError(
            "DeepFilterNet lib missing at %s. On a machine with disk space, run "
            "scripts/vendor_deepfilternet.sh (or pip install deepfilternet)."
            % lib_path
        )
    # Prefer vendored tree: parent so `import df` resolves to libs/DeepFilterNet/df
    root = str(lib_path)
    if root not in sys.path:
        sys.path.insert(0, root)


def _import_enhance() -> Tuple[Any, Any]:
    """Return (enhance_main, maybe_download_model)."""
    try:
        from df.enhance_call import enhance_main, maybe_download_model  # type: ignore

        return enhance_main, maybe_download_model
    except ImportError:
        pass
    try:
        from df.enhance import enhance as _enhance  # type: ignore
        from df.enhance import init_df, maybe_download_model  # type: ignore

        def enhance_main(**kwargs):  # type: ignore[no-untyped-def]
            # Minimal fallback for stock deepfilternet package API shape
            raise NotImplementedError(
                "stock df.enhance has no enhance_main; vendor source enhance_call.py "
                "via scripts/vendor_deepfilternet.sh"
            )

        return enhance_main, maybe_download_model
    except ImportError as e:
        raise ImportError(
            "DeepFilterNet Python package not importable (need vendored libs/DeepFilterNet "
            "with working libdf for this platform, or pip install deepfilternet). "
            "Original error: %s" % e
        ) from e


def ensure_upstream_weights(upstream_ref: str, lib_path: Optional[Path] = None) -> Path:
    """Download pretrained DF model dir via upstream helper (weights not in git)."""
    if lib_path is not None:
        ensure_deepfilter_import(lib_path)
    _, maybe_download_model = _import_enhance()
    model_dir = maybe_download_model(upstream_ref)
    return Path(model_dir)


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
    Run DeepFilterNet on one file. Returns output path list.

    Platform note: native libdf is often Linux-only in vendored trees; test env
    must provide a matching libdf or a pip wheel for the host.
    """
    params = dict(params or {})
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise FileNotFoundError("input audio not found: %s" % input_path)

    if lib_path is not None:
        ensure_deepfilter_import(lib_path)

    enhance_main, maybe_download_model = _import_enhance()
    # Ensure weights exist (upstream cache, not git)
    maybe_download_model(upstream_ref)

    outs = enhance_main(
        model_base_dir=upstream_ref,
        noisy_audio_files=[str(input_path)],
        output_dir=str(output_dir),
        pf=bool(params.get("pf", False)),
        is_gpu=bool(params.get("is_gpu", is_gpu)),
        atten_lim=params.get("atten_lim"),
        suffix=bool(params.get("suffix", True)),
        log_level=str(params.get("log_level", "ERROR")),
    )
    return [Path(p) for p in (outs or [])]
