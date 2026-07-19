from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from taudio_engines.manifest import get_model


def cache_root() -> Path:
    """
    Resolve model cache directory.

    1. $TAUDIO_MODEL_CACHE
    2. ~/.cache/taudio-engines/models
    """
    env = os.environ.get("TAUDIO_MODEL_CACHE", "").strip()
    if env:
        root = Path(env).expanduser().resolve()
    else:
        root = Path.home() / ".cache" / "taudio-engines" / "models"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def cached_path(manifest: Dict[str, Any], model_id: str) -> Path:
    entry = get_model(manifest, model_id)
    key = entry.get("cache_key") or model_id
    return cache_root() / str(key)


def ensure_model(
    manifest: Dict[str, Any],
    model_id: str,
    *,
    force: bool = False,
) -> Path:
    """
    Ensure model file exists in cache with matching sha256 (when provided).

    Downloads from the first working URL in manifest entry `urls`.
    """
    entry = get_model(manifest, model_id)
    dest = cached_path(manifest, model_id)
    expected = (entry.get("sha256") or "").strip().lower()
    urls = entry.get("urls") or []
    if not isinstance(urls, list) or not urls:
        raise ValueError("model %s has no urls in manifest" % model_id)

    if dest.is_file() and not force:
        if not expected or _sha256_file(dest) == expected:
            return dest
        # mismatch: re-download

    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Optional[BaseException] = None
    for url in urls:
        url = str(url).strip()
        if not url:
            continue
        try:
            _download(url, dest, expected_sha256=expected or None)
            return dest
        except Exception as e:  # noqa: BLE001 - try next mirror
            last_err = e
            if dest.exists():
                dest.unlink(missing_ok=True)
    raise RuntimeError(
        "failed to download model %s from urls=%s: %s" % (model_id, urls, last_err)
    )


def _download(url: str, dest: Path, expected_sha256: Optional[str]) -> None:
    with tempfile.NamedTemporaryFile(delete=False, dir=str(dest.parent)) as tmp:
        tmp_path = Path(tmp.name)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "taudio-engines/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp, tmp_path.open("wb") as out:
            shutil.copyfileobj(resp, out)
        if expected_sha256:
            digest = _sha256_file(tmp_path)
            if digest != expected_sha256:
                raise ValueError(
                    "sha256 mismatch for %s: got %s want %s" % (url, digest, expected_sha256)
                )
        tmp_path.replace(dest)
    except urllib.error.URLError as e:
        tmp_path.unlink(missing_ok=True)
        raise e
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
