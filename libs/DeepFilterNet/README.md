# DeepFilterNet lib placeholder

This directory should contain the vendored upstream tree (`df/`, `libdf/`, …).

**Do not commit large native binaries** (`*.so` / `*.dylib`).

On a machine with disk space:

```bash
# from taudio-models root
./scripts/vendor_deepfilternet.sh /path/to/audioprocessPython/DeepFilterNet
```

Then provide a platform-matching `libdf` (build or pip wheel) before running inference.

Public asset ids: `deepfilternet` / `deepfilternet2` / `deepfilternet3`  
Public capability: `denoise.speech`
