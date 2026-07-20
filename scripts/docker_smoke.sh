#!/usr/bin/env bash
# Docker smoke: synthetic 1s wav -> denoise.speech -> /data/out
set -euo pipefail

mkdir -p /data/in /data/out /cache/models

python - <<'PY'
import numpy as np
import soundfile as sf
from pathlib import Path

path = Path("/data/in/smoke_noisy.wav")
sr = 48000
t = np.linspace(0, 1.0, sr, endpoint=False)
audio = (0.2 * np.sin(2 * np.pi * 220 * t) + 0.05 * np.random.randn(sr)).astype(
    np.float32
)
sf.write(path, audio, sr)
print("wrote", path)
PY

taudio-models-denoise /data/in/smoke_noisy.wav -o /data/out --asset deepfilternet3
echo "smoke outputs:"
ls -la /data/out
