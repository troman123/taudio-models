# taudio-models

Open-source **model layer** for audio AI: catalog, versions, `ModelParams` schemas, weight **download/cache**, and **load** handles.

The **engine layer** (how to process a file / PCM frame / bytes) lives in the private local project **TaudioProcess** and is not open-sourced.

License for packaging code: [MPL-2.0](LICENSE). See [NOTICE](NOTICE).

Modifications to this project's source files must remain under MPL-2.0.
Closed products may use the package as a Larger Work; keep attribution.

## What is (and is not) in git

| In git | Not in git |
|--------|------------|
| Model catalog + param schemas (`manifest.yaml`) | Weight binaries |
| Download/cache + `Model.load()` API | Engine / pipeline / file-or-frame I/O |
| Future `libs/` model implementations | Proprietary SDKs |

## Install

```bash
git clone https://github.com/troman123/taudio-models.git
cd taudio-models
python -m pip install -e .
```

## Query + load

```bash
export TAUDIO_MODELS_ROOT=/path/to/taudio-models
taudio-models-fetch --list-assets
taudio-models-fetch --list-capabilities
taudio-models-fetch --list-catalog
taudio-models-fetch --list           # weights: with urls (DF uses upstream)
```

```python
from taudio_models import open_registry, open_capability_registry

reg = open_registry()
print([m.to_dict() for m in reg.list_models()])

caps = open_capability_registry()
print([c.id for c in caps.list_capabilities()])  # denoise.speech
```

Public names are generic (`deepfilternet3`, `denoise.speech`). Internal short names
(`de3`, `dn.speech`) live only in closed TaudioProcess — see [docs/registries.md](docs/registries.md).

### DeepFilterNet (denoise MVP)

```bash
./scripts/vendor_deepfilternet.sh /path/to/DeepFilterNet   # on a machine with space
# then provide platform libdf / pip wheel before inference
```

Cache: `$TAUDIO_MODEL_CACHE` or `~/.cache/taudio-models/models`.

See [docs/api.md](docs/api.md) and [docs/model-cache.md](docs/model-cache.md).

## Cloud Agents

Work only on this GitHub repo. Follow [AGENTS.md](AGENTS.md). Do not add process/file pipeline APIs here.
