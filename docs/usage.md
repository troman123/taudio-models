# Usage guide

Local **pip** and **Docker** are both supported end-to-end. Prefer the one that matches your environment; do not treat either as deprecated.

## Decision guide

| Situation | Use |
|-----------|-----|
| Developing on a machine with Python 3.10+ | Local pip (`.[denoise]`) |
| CI / laptop without polluting system Python | Docker Compose |
| Calling from another Python app | Python API after pip (or container shell) |
| Only browsing catalog / params | `pip install -e .` then `taudio-models-fetch` (no `[denoise]`) |

Public identifiers are identical across methods:

- capability: `denoise.speech`
- assets: `deepfilternet`, `deepfilternet2`, `deepfilternet3`

## How the data root is resolved

Runtime looks for `manifest.yaml` in this order:

1. `--repo` / constructor argument
2. `$TAUDIO_MODELS_ROOT`
3. Walk upward from the current working directory (git checkout)
4. Bundled copy inside the installed package (`taudio_models/resources/`)

So `pip install` users get a working catalog without cloning forever; checkout users keep editing `src/taudio_models/resources/manifest.yaml` (repo-root `manifest.yaml` is a symlink).

## Local pip

```bash
cd taudio-models
python -m pip install -e ".[denoise]"
export TAUDIO_MODELS_ROOT="$PWD"   # optional but explicit
taudio-models-denoise input.wav -o out/
taudio-models-fetch --list-assets
```

Cache: `$TAUDIO_MODEL_CACHE` or `~/.cache/taudio-models/models`.

### Troubleshooting (pip)

| Symptom | Likely cause | What to try |
|---------|--------------|-------------|
| `manifest.yaml not found` | Wrong cwd / no install | `export TAUDIO_MODELS_ROOT=...` or reinstall package |
| `DeepFilterNet not importable` | Missing extra | `pip install 'taudio-models[denoise]'` |
| Killed / OOM | RAM too small | Add swap, use shorter audio, or a larger machine |
| Slow first run | Weight download | Wait; subsequent runs use cache |

## Docker

```bash
cd taudio-models
docker compose build
docker compose run --rm smoke
docker compose run --rm denoise /data/in/input.wav -o /data/out
```

| Host path | Container |
|-----------|-----------|
| `./data/in` | `/data/in` |
| `./data/out` | `/data/out` |
| volume `taudio-model-cache` | `/cache` |

Image uses published `python:3.10-slim-bookworm` and installs `.[denoise]` non-editably.

### Troubleshooting (Docker)

| Symptom | What to try |
|---------|-------------|
| Cannot pull base image | Fix registry mirrors / network; image is `python:3.10-slim-bookworm` |
| Permission on `./data` | `chmod -R a+rw data` or run as your uid with compose `user:` |
| Rebuild after code change | `docker compose build --no-cache` |

## Python API

```python
from taudio_models import open_capability_registry, PublicAssetRegistry, resolve_models_root

print(resolve_models_root())
print([a.id for a in PublicAssetRegistry().list_assets()])

caps = open_capability_registry()
caps.run_file("denoise.speech", "input.wav", "out/", asset_id="deepfilternet3")
```

## Related

- [api.md](api.md)
- [registries.md](registries.md)
- [model-cache.md](model-cache.md)
