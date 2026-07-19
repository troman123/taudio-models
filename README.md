# taudio-engines

Open-source **audio separation engine libraries** and a **model download/cache** layer for local [TaudioProcess](https://github.com/) (framework stays private/local; this repo is public).

License for packaging code in this repository: [MIT](LICENSE). See [NOTICE](NOTICE) for third-party attribution.

## What is (and is not) in git

| In git | Not in git |
|--------|------------|
| Engine source under `libs/` | Model weight files |
| `manifest.yaml` (URLs, sha256, licenses) | Git LFS weight blobs |
| Download/cache Python API | Proprietary SDKs (`mpa_sdk`, etc.) |

At runtime, models are downloaded into a cache directory and reused.

## Install

```bash
git clone https://github.com/troman123/taudio-engines.git
cd taudio-engines
python -m pip install -e .
```

## Model cache

```bash
# optional override
export TAUDIO_MODEL_CACHE=/path/to/fast/disk/taudio-models

# list models from manifest
taudio-engines-fetch --list

# download one or all registered models
taudio-engines-fetch --model <id>
taudio-engines-fetch --all
```

Default cache root: `~/.cache/taudio-engines/models`.

From Python:

```python
from pathlib import Path
from taudio_engines.cache import ensure_model
from taudio_engines.manifest import load_manifest

root = Path(__file__).resolve().parents[1]  # repo root when developing
manifest = load_manifest(root / "manifest.yaml")
# path = ensure_model(manifest, "some_model_id")
```

See [docs/model-cache.md](docs/model-cache.md).

## Layout

```text
libs/                 # vendored engine code (added over time)
src/taudio_engines/   # manifest + cache API
manifest.yaml         # engines + model metadata
scripts/              # bootstrap / checks / fetch CLI helper
docs/                 # cache policy, non-free components
```

## Use with local TaudioProcess

Fixed interface (query + run): see [docs/api.md](docs/api.md).

```bash
export TAUDIO_ENGINES_ROOT=/path/to/taudio-engines
```

```python
from taudio_engines import open_registry
reg = open_registry()
models = reg.list_models()          # what can be called + ModelParam schemas
# reg.run_model("ause", "in.wav", "out/", {"variant": "vocal"})
```

## Cloud Agents

Cursor Cloud Agents should clone this GitHub repo. Conventions for agents are in [AGENTS.md](AGENTS.md). Put task instructions in the prompt; put durable policy in this repo.

## Status

Skeleton (`v0.1.0`): packaging, manifest schema, download/cache helpers. Engine libs and concrete model URLs arrive in follow-up PRs.
