# taudio-models

Open-source **model layer** for audio AI: catalog, versions, `ModelParams` schemas, weight **download/cache**, and **load** handles.

The **engine layer** (how to process a file / PCM frame / bytes) lives in the private local project **TaudioProcess** and is not open-sourced.

License for packaging code: [MIT](LICENSE). See [NOTICE](NOTICE).

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
taudio-models-fetch --list-engines   # lists catalog models + params
taudio-models-fetch --list           # lists downloadable weights
```

```python
from taudio_models import open_registry
reg = open_registry()
print([m.to_dict() for m in reg.list_models()])
# loaded = reg.load_model("ause", {"variant": "vocal"})
```

Cache: `$TAUDIO_MODEL_CACHE` or `~/.cache/taudio-models/models`.

See [docs/api.md](docs/api.md) and [docs/model-cache.md](docs/model-cache.md).

## Cloud Agents

Work only on this GitHub repo. Follow [AGENTS.md](AGENTS.md). Do not add process/file pipeline APIs here.
