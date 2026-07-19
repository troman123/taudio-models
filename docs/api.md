# Fixed API between taudio-engines and TaudioProcess

TaudioProcess must not call engine internals. It only uses:

1. `list_models` / `get_model` — discover what can be run and each model's `ModelParam` schema
2. `run_model(model_id, input_path, output_dir, params: dict)` — one fixed execute entry
3. `ModelParams` — every model accepts the same envelope; values are validated against that model's schema

## Python (engines side)

```python
from pathlib import Path
from taudio_engines import open_registry, Capability

reg = open_registry(Path("/path/to/taudio-engines"))

# query
for m in reg.list_models(include_planned=True):
    print(m.id, m.status.value, [p.name for p in m.params])

info = reg.get_model("ause")          # or alias "ausev"
print(info.to_dict())                 # JSON-serializable card

# run (when status=available and Engine wired)
# result = reg.run_model("ause", "in.wav", "out/", {"variant": "vocal", "model_weight": "rofep"})
```

## Contract types

| Type | Role |
|------|------|
| `ModelInfo` | Queryable card: id, capabilities, params, stems, status |
| `ModelParam` | One parameter definition (name/type/default/range/choices) |
| `ModelParams` | Runtime values dict; `validated(info)` before run |
| `RunRequest` / `RunResult` | Fixed request/response for execute |
| `Engine` | Interface every model implements: `info()` + `run(...)` |

## Adding a new model

1. Add engine entry under `engines:` in `manifest.yaml` with `params`, `capabilities`, `output_stems`.
2. Implement `Engine` subclass and `@register_engine("id")`.
3. Set `status: available` only when runnable.
4. Register weight download entries under `models:` (urls/sha256); never commit binaries.

## JSON shape (for future iOS / IPC)

`ModelInfo.to_dict()` and `RunRequest.to_dict()` / `RunResult.to_dict()` are the wire format.
Do not invent a second parameter system in TaudioProcess.
