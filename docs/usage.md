# Usage guide

`taudio-models` supports **multiple** ways to run. They are all first-class; choose by environment.

## Comparison

| | Local pip | Docker | Python API |
|--|-----------|--------|------------|
| Needs Python 3.10+ on host | Yes | No (only Docker) | Yes (or use inside container) |
| Install | `pip install -e ".[denoise]"` | `docker compose build` | same as pip / image |
| Denoise CLI | `taudio-models-denoise` | `docker compose run --rm denoise ...` | — |
| List assets | `taudio-models-fetch --list-assets` | `docker compose run --rm --entrypoint taudio-models-fetch denoise --list-assets` | `PublicAssetRegistry` |
| Weight cache | `$TAUDIO_MODEL_CACHE` or `~/.cache/taudio-models/models` | volume `taudio-model-cache` | same as install path |

Public capability / asset ids are identical across methods (`denoise.speech`, `deepfilternet3`, …).

## Local pip

```bash
cd taudio-models
python -m pip install -e ".[denoise]"
export TAUDIO_MODELS_ROOT="$PWD"
taudio-models-denoise input.wav -o out/
```

Minimal install (catalog / fetch only, no denoise runtime):

```bash
python -m pip install -e .
taudio-models-fetch --list-catalog
```

## Docker

```bash
cd taudio-models
docker compose build
docker compose run --rm smoke
docker compose run --rm denoise /data/in/input.wav -o /data/out
```

Put inputs in `data/in/`; read outputs from `data/out/`.

## Python API

```python
from taudio_models import open_capability_registry, PublicAssetRegistry

reg_assets = PublicAssetRegistry()  # uses TAUDIO_MODELS_ROOT or finds manifest.yaml
print([a.id for a in reg_assets.list_assets()])

caps = open_capability_registry()
caps.run_file("denoise.speech", "input.wav", "out/", asset_id="deepfilternet3")
```

## Related docs

- [api.md](api.md) — registries and types
- [registries.md](registries.md) — public vs internal naming
- [model-cache.md](model-cache.md) — weight cache
