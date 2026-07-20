# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Public capability: separate.bandit — Bandit cinematic stem separation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from taudio_models.backends.bandit import separate_array, separate_file
from taudio_models.registry.capabilities import (
    PublicCapability,
    PublicCapabilityRegistry,
    register_capability,
)


def _model_dir(params: Dict[str, Any], asset_ensure: Dict[str, Any]) -> Optional[Path]:
    raw = params.get("model_dir") or params.get("model_path")
    if raw:
        return Path(raw)
    env = os.environ.get("TAUDIO_BANDIT_DIR")
    if env:
        return Path(env)
    # Convention: sibling of models root / BanditIV
    root = asset_ensure.get("models_root") or asset_ensure.get("root")
    if root:
        return Path(root) / "BanditIV"
    return None


@register_capability("separate.bandit")
def build_separate_bandit(reg: PublicCapabilityRegistry) -> PublicCapability:
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
            model_dir=_model_dir(params, asset_ensure),
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
            model_dir=_model_dir(params, asset_ensure),
        )

    return PublicCapability(
        id="separate.bandit",
        display_name="Bandit cinematic stems",
        default_asset_id="bandit",
        description=(
            "Thin public expose of libs/banditv "
            "(source BanditIV / bdiv; m=db48|db64, g=speech|…)"
        ),
        kind="separate",
        run_file=run_file,
        run_array=run_array,
        meta={"family": "bandit"},
    )
