# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public capability: separate.hpss — harmonic/percussive separation via librosa."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from taudio_models.backends.hpss import separate_array, separate_file
from taudio_models.registry.capabilities import (
    PublicCapability,
    PublicCapabilityRegistry,
    register_capability,
)


@register_capability("separate.hpss")
def build_separate_hpss(reg: PublicCapabilityRegistry) -> PublicCapability:
    def run_file(
        input_path: Path,
        output_dir: Path,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> List[Path]:
        _ = asset_ensure
        import os

        if (os.environ.get("TAUDIO_MODELS_BACKEND") or "python").strip().lower() == "native":
            from taudio_models.backends.native_bridge import run_file as native_run_file

            return native_run_file(
                "separate.hpss",
                Path(input_path),
                Path(output_dir),
                params=params,
            )
        return separate_file(input_path, output_dir, params=params)

    def run_array(
        audio: Any,
        sample_rate: int,
        asset_ensure: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Tuple[Any, int]:
        _ = asset_ensure
        return separate_array(audio, sample_rate, params=params)

    return PublicCapability(
        id="separate.hpss",
        display_name="HPSS (harmonic / percussive)",
        default_asset_id="",
        description="Thin public expose of librosa HPSS (source HPSSIV / hpiv compatible)",
        kind="separate",
        run_file=run_file,
        run_array=run_array,
        meta={"family": "hpss"},
    )
