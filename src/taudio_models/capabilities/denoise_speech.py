# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public capability: denoise.speech"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from taudio_models.backends.deepfilter import enhance_file
from taudio_models.registry.capabilities import (
    PublicCapability,
    PublicCapabilityRegistry,
    register_capability,
)


@register_capability("denoise.speech")
def build_denoise_speech(reg: PublicCapabilityRegistry) -> PublicCapability:
    def run_file(
        input_path: Path,
        output_dir: Path,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> List[Path]:
        upstream = str(asset_ensure.get("upstream_ref") or "DeepFilterNet3")
        lib_path = Path(asset_ensure["lib_path"])
        is_gpu = bool(params.get("is_gpu", False))
        return enhance_file(
            input_path,
            output_dir,
            upstream_ref=upstream,
            lib_path=lib_path,
            is_gpu=is_gpu,
            params=params,
        )

    return PublicCapability(
        id="denoise.speech",
        display_name="Speech denoise (DeepFilterNet)",
        default_asset_id="deepfilternet3",
        description="Generic speech denoising / enhancement via DeepFilterNet",
        kind="denoise",
        run_file=run_file,
        meta={"family": "deepfilternet"},
    )
