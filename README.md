# taudio-models

Open-source **model layer** for audio AI: catalog, versions, `ModelParams` schemas, weight **download/cache**, load handles, and public capability hooks.

License: [MPL-2.0](LICENSE). See [NOTICE](NOTICE).

## How to use

### Option A — pip (local Python ≥ 3.10)

```bash
git clone https://github.com/troman123/taudio-models.git
cd taudio-models
python -m pip install -e ".[denoise]"

export TAUDIO_MODELS_ROOT="$PWD"
taudio-models-denoise noisy.wav -o out/
```

### Option B — Docker (recommended if you don't want to touch host Python)

Files in-repo: [`Dockerfile`](Dockerfile), [`compose.yaml`](compose.yaml).

```bash
git clone https://github.com/troman123/taudio-models.git
cd taudio-models

# build image once (uses published python:3.10-slim-bookworm + pip deepfilternet)
docker compose build

# self-check (synthetic audio, no input file needed)
docker compose run --rm smoke

# denoise your file
cp /path/to/noisy.wav data/in/
docker compose run --rm denoise /data/in/noisy.wav -o /data/out
# outputs land in ./data/out ; model cache in Docker volume taudio-model-cache
```

Weights download at runtime into the cache volume (never committed to git).

### Python API

```python
from taudio_models import open_capability_registry

caps = open_capability_registry()  # needs TAUDIO_MODELS_ROOT or cwd with manifest.yaml
caps.run_file("denoise.speech", "noisy.wav", "out/")
```

### Query

```bash
taudio-models-fetch --list-assets
taudio-models-fetch --list-capabilities
taudio-models-fetch --list-catalog
```

Public names: `denoise.speech`, `deepfilternet3`.  
Product short names (`dn.speech`, `de3`) stay in closed TaudioProcess.

## What is (and is not) in git

| In git | Not in git |
|--------|------------|
| Catalog / assets / capability schemas | Weight binaries |
| Dockerfile + compose.yaml | Engine / product pipeline |
| Packaging + registries | Proprietary SDKs |

Cache: `$TAUDIO_MODEL_CACHE` or `~/.cache/taudio-models/models` (pip); Docker volume `taudio-model-cache` (compose).

See [docs/api.md](docs/api.md), [docs/registries.md](docs/registries.md).
