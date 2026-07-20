# taudio-models

Open-source **model layer** for audio AI: catalog, versions, parameter schemas, weight download/cache, load handles, and public capability hooks.

License: [MPL-2.0](LICENSE). See [NOTICE](NOTICE).

## Supported ways to use

Local install and Docker are **both first-class**. Same public ids (`denoise.speech`, `deepfilternet3`, …) in every path.

| Method | Best when | Start here |
|--------|-----------|------------|
| **Local pip** | You already use Python ≥ 3.10 on the host | § Local install |
| **Docker** | You want an isolated runtime / no host Python changes | § Docker |
| **Python API** | Embedding in your own code | § Python API |

Full detail: [docs/usage.md](docs/usage.md).

### Requirements (denoise)

- **CPU RAM:** plan ~2 GB+ free (DeepFilterNet + PyTorch). Smaller hosts may need swap.
- **Disk:** model weights download on first run (not stored in git).
- **OS:** Linux/macOS; Windows via WSL2 recommended for native `libdf` wheels.

---

### Local install

```bash
git clone https://github.com/troman123/taudio-models.git
cd taudio-models
python -m pip install -e ".[denoise]"

# Optional: pin the checkout as data root (otherwise auto-detect / bundled manifest)
export TAUDIO_MODELS_ROOT="$PWD"

taudio-models-fetch --list-assets
taudio-models-fetch --list-capabilities
taudio-models-denoise path/to/noisy.wav -o out/
```

Catalog-only (no denoise runtime):

```bash
python -m pip install -e .
taudio-models-fetch --list-catalog
```

After `pip install`, a **bundled** `manifest.yaml` ships inside the package, so you do not have to keep a git checkout on `PYTHONPATH` for basic use. Setting `TAUDIO_MODELS_ROOT` still wins when you need a custom checkout.

---

### Docker

Files: [`Dockerfile`](Dockerfile), [`docker-compose.yml`](docker-compose.yml).

```bash
git clone https://github.com/troman123/taudio-models.git
cd taudio-models

docker compose build
docker compose run --rm smoke

cp path/to/noisy.wav data/in/
docker compose run --rm denoise /data/in/noisy.wav -o /data/out
# outputs → ./data/out
# weight cache → Docker volume taudio-model-cache
```

---

### Python API

Works with **local pip** or inside the **Docker** image.

```python
from taudio_models import open_capability_registry

caps = open_capability_registry()  # uses TAUDIO_MODELS_ROOT, cwd checkout, or bundled manifest
paths = caps.run_file("denoise.speech", "noisy.wav", "out/")
```

---

## Layout notes

| Path | Role |
|------|------|
| `src/taudio_models/resources/manifest.yaml` | Canonical public catalog / assets / capabilities |
| `manifest.yaml` | Symlink to the resources file (checkout convenience) |
| `Dockerfile` / `docker-compose.yml` | Isolated denoise runtime |

Weights and `*.so` are never committed.

See also: [docs/api.md](docs/api.md) · [docs/registries.md](docs/registries.md) · [docs/model-cache.md](docs/model-cache.md)
