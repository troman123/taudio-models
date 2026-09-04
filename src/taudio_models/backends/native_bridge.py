# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Thin subprocess bridge to taudio-models-native `tmn_run` (optional).

Native binary is standalone C++; this module only shells out to it.
Requires a built `tmn_run` on PATH or TAUDIO_MODELS_NATIVE_BIN.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def _find_tmn_run() -> Path:
    env = (os.environ.get("TAUDIO_MODELS_NATIVE_BIN") or "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            raise FileNotFoundError("TAUDIO_MODELS_NATIVE_BIN not a file: %s" % p)
        return p
    found = shutil.which("tmn_run")
    if not found:
        raise FileNotFoundError(
            "tmn_run not found; set TAUDIO_MODELS_NATIVE_BIN or add to PATH"
        )
    return Path(found)


def run_file(
    capability_id: str,
    input_path: Path,
    output_dir: Path,
    *,
    asset_id: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> List[Path]:
    bin_path = _find_tmn_run()
    cmd: List[str] = [
        str(bin_path),
        "--capability",
        str(capability_id),
        "--input",
        str(input_path),
        "--output-dir",
        str(output_dir),
    ]
    if asset_id:
        cmd.extend(["--asset", str(asset_id)])
    if params:
        cmd.extend(["--params", json.dumps(params)])

    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    stdout = (proc.stdout or "").strip()
    if not stdout:
        raise RuntimeError(
            "tmn_run no stdout rc=%s stderr=%s"
            % (proc.returncode, (proc.stderr or "").strip())
        )
    payload = json.loads(stdout.splitlines()[-1])
    if proc.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(
            "%s (rc=%s)"
            % (payload.get("error") or payload.get("status") or "fail", proc.returncode)
        )
    return [Path(p) for p in (payload.get("outputs") or [])]


def backend_is_native() -> bool:
    return (os.environ.get("TAUDIO_MODELS_BACKEND") or "python").strip().lower() == "native"
