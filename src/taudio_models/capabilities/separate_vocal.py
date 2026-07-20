# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public capability: separate.vocal — MelBand RoFormer vocal separation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from taudio_models.backends.mel_band_roformer import separate_array, separate_file
from taudio_models.registry.capabilities import (
    PublicCapability,
    PublicCapabilityRegistry,
    register_capability,
)


@register_capability("separate.vocal")
def build_separate_vocal(reg: PublicCapabilityRegistry) -> PublicCapability:
    def run_file(
        input_path: Path,
        output_dir: Path,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> List[Path]:
        lib_path = Path(asset_ensure["lib_path"])
        is_gpu = bool(params.get("is_gpu", False))
        return separate_file(
            input_path,
            output_dir,
            lib_path=lib_path,
            asset_ensure=asset_ensure,
            is_gpu=is_gpu,
            params=params,
        )

    def run_array(
        audio: Any,
        sample_rate: int,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Tuple[Any, int]:
        lib_path = Path(asset_ensure["lib_path"])
        is_gpu = bool(params.get("is_gpu", False))
        return separate_array(
            audio,
            sample_rate,
            lib_path=lib_path,
            asset_ensure=asset_ensure,
            is_gpu=is_gpu,
            params=params,
        )

    return PublicCapability(
        id="separate.vocal",
        display_name="Vocal separation (MelBand RoFormer)",
        default_asset_id="melband_vocals",
        description=(
            "Thin public expose of libs/MelBandRoformer "
            "(separate_file / separate_array via backend glue)"
        ),
        kind="separate",
        run_file=run_file,
        run_array=run_array,
        meta={"family": "mel_band_roformer"},
    )
