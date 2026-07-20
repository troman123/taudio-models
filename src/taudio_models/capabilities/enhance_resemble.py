# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public capability: enhance.resemble — Resemble Enhance / denoise."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from taudio_models.backends.resemble import enhance_array, enhance_file
from taudio_models.registry.capabilities import (
    PublicCapability,
    PublicCapabilityRegistry,
    register_capability,
)


def _run_dir(params: Dict[str, Any], asset_ensure: Dict[str, Any]) -> Optional[Path]:
    raw = params.get("run_dir") or params.get("model_dir")
    if raw:
        return Path(raw)
    env = os.environ.get("TAUDIO_REENH_DIR")
    if env:
        return Path(env)
    root = asset_ensure.get("models_root") or asset_ensure.get("root")
    if root:
        model_name = str(params.get("m") or "enhancer_stage2")
        return Path(root) / "ResembleEnhance" / model_name
    return None


@register_capability("enhance.resemble")
def build_enhance_resemble(reg: PublicCapabilityRegistry) -> PublicCapability:
    def run_file(
        input_path: Path,
        output_dir: Path,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> List[Path]:
        lib_path = asset_ensure.get("lib_path")
        is_gpu = bool(params.get("is_gpu", False))
        return enhance_file(
            input_path,
            output_dir,
            params=params,
            is_gpu=is_gpu,
            lib_path=Path(lib_path) if lib_path else None,
            run_dir=_run_dir(params, asset_ensure),
        )

    def run_array(
        audio: Any,
        sample_rate: int,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Tuple[Any, int]:
        lib_path = asset_ensure.get("lib_path")
        is_gpu = bool(params.get("is_gpu", False))
        return enhance_array(
            audio,
            sample_rate,
            params=params,
            is_gpu=is_gpu,
            lib_path=Path(lib_path) if lib_path else None,
            run_dir=_run_dir(params, asset_ensure),
        )

    return PublicCapability(
        id="enhance.resemble",
        display_name="Resemble Enhance",
        default_asset_id="resemble",
        description="Thin public expose of libs/resemble_enhancev (reenh)",
        kind="enhance",
        run_file=run_file,
        run_array=run_array,
        meta={"family": "resemble"},
    )
