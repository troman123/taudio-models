# taudio-models

Open-source **model layer** for audio AI: catalog, versions, `ModelParams` schemas, weight **download/cache**, load handles, and public capability hooks.

License: [MPL-2.0](LICENSE). See [NOTICE](NOTICE).

## Ways to use (all supported)

| Method | When to use | Entry |
|--------|-------------|--------|
| **Local pip** | You have Python ≥ 3.10 and want CLI / library on the host | `pip install -e ".[denoise]"` |
| **Docker** | Keep host Python untouched; same denoise flow in a container | `docker compose build` + `run` |
| **Python API** | Embed in your own code (after pip install, or inside the image) | `open_capability_registry()` |

Pick whichever fits; capabilities and asset ids are the same in all three.

---

### 1) Local install (pip)

```bash
git clone https://github.com/troman123/taudio-models.git
cd taudio-models
python -m pip install -e ".[denoise]"

export TAUDIO_MODELS_ROOT="$PWD"
# optional: export TAUDIO_MODEL_CACHE="$HOME/.cache/taudio-models/models"

taudio-models-denoise noisy.wav -o out/
taudio-models-denoise noisy.wav -o out/ --asset deepfilternet2

taudio-models-fetch --list-assets
taudio-models-fetch --list-capabilities
```

Requires: Python ≥ 3.10. Extra `[denoise]` pulls the published `deepfilternet` package; weights download at runtime (not in git).

---

### 2) Docker

In-repo files: [`Dockerfile`](Dockerfile), [`compose.yaml`](compose.yaml), [`scripts/docker_smoke.sh`](scripts/docker_smoke.sh).

```bash
git clone https://github.com/troman123/taudio-models.git
cd taudio-models

docker compose build

# self-check (synthetic audio)
docker compose run --rm smoke

# denoise your file
cp /path/to/noisy.wav data/in/
docker compose run --rm denoise /data/in/noisy.wav -o /data/out
# results: ./data/out
# model cache: Docker volume taudio-model-cache
```

Same CLI as local (`taudio-models-denoise`); base image is published `python:3.10-slim-bookworm`.

---

### 3) Python API

Works after **local pip**, or from a shell inside the **Docker** image (`docker compose run --rm --entrypoint bash denoise`).

```python
import os
from taudio_models import open_capability_registry

# Point at the repo root that contains manifest.yaml
os.environ.setdefault("TAUDIO_MODELS_ROOT", "/path/to/taudio-models")

caps = open_capability_registry()
caps.run_file("denoise.speech", "noisy.wav", "out/")
# optional: asset_id="deepfilternet2"
```

Public names: `denoise.speech`, `deepfilternet3` (etc.).  
Product short names (`dn.speech`, `de3`) stay in closed TaudioProcess.

---

## What is (and is not) in git

| In git | Not in git |
|--------|------------|
| Catalog / assets / capability schemas | Weight binaries |
| Dockerfile + compose.yaml | Engine / product pipeline |
| Packaging + registries | Proprietary SDKs |

See [docs/api.md](docs/api.md), [docs/registries.md](docs/registries.md), [docs/usage.md](docs/usage.md).
