# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public capability: separate.demucs — Demucs instrumental mute / stem mix."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from taudio_models.backends.demucs import separate_array, separate_file
from taudio_models.registry.capabilities import (
    PublicCapability,
    PublicCapabilityRegistry,
    register_capability,
)


@register_capability("separate.demucs")
def build_separate_demucs(reg: PublicCapabilityRegistry) -> PublicCapability:
    def run_file(
        input_path: Path,
        output_dir: Path,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> List[Path]:
        lib_path = asset_ensure.get("lib_path")
        is_gpu = bool(params.get("is_gpu", False))
        return separate_file(
            input_path,
            output_dir,
            params=params,
            is_gpu=is_gpu,
            lib_path=Path(lib_path) if lib_path else None,
        )

    def run_array(
        audio: Any,
        sample_rate: int,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Tuple[Any, int]:
        lib_path = asset_ensure.get("lib_path")
        is_gpu = bool(params.get("is_gpu", False))
        return separate_array(
            audio,
            sample_rate,
            params=params,
            is_gpu=is_gpu,
            lib_path=Path(lib_path) if lib_path else None,
        )

    return PublicCapability(
        id="separate.demucs",
        display_name="Demucs instrumental filter",
        default_asset_id="demucs",
        description=(
            "Thin public expose of demucs.api.Separator "
            "(source DEMUCSIV / dmiv mute-vocals path)"
        ),
        kind="separate",
        run_file=run_file,
        run_array=run_array,
        meta={"family": "demucs"},
    )
