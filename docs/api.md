# Fixed API: open-source model layer (taudio-models) vs closed engine layer (TaudioProcess)

## Boundary

| Layer | Repo | Responsibility |
|-------|------|----------------|
| **Model layer** (open) | `taudio-models` | Model structure, version, `ModelParams` schema, weight download/cache, `load()` handle |
| **Engine layer** (closed) | `TaudioProcess` only | How to call: file / PCM frame / bytes; orchestration; writing stems |

Open source must **not** implement `process_file` / pipeline run. That stays private.

## Model layer Python API

```python
from pathlib import Path
from taudio_models import open_registry

reg = open_registry(Path("/path/to/taudio-models"))

# query
for m in reg.list_models(include_planned=True):
    print(m.id, m.version, m.status.value, [p.name for p in m.params])

info = reg.get_model("ause")   # or alias "ausev"

# download weights (if weight_ids registered) + load handle
loaded = reg.load_model("ause", {"variant": "vocal", "model_weight": "rofep"})
# loaded.info / loaded.params / loaded.weight_paths / loaded.backend
```

## Types

| Type | Role |
|------|------|
| `ModelInfo` | Queryable card: id, version, capabilities, params, stems |
| `ModelParam` | One parameter definition |
| `ModelParams` | Runtime values; `validated(info)` |
| `Model` | `info()` / `ensure_weights()` / `load()` |
| `LoadedModel` | Opaque handle for the closed engine layer |

## Engine layer (TaudioProcess, not in this repo)

```python
# private
engine.process_file(path, model_id, params)
engine.process_array(pcm, sr, model_id, params)
engine.process_bytes(data, model_id, params)
```

These call `load_model` then run inference / I/O privately.
