# Open model layer API (taudio-models)

## Boundary

| Layer | Repo | Responsibility |
|-------|------|----------------|
| **Public assets + capabilities** | `taudio-models` | Generic ids, download, thin `run_file` hooks, libs |
| **Internal assets + capabilities + engine** | `TaudioProcess` | Short names, product I/O (`process_file` / array / bytes), pipeline |

Public ids and internal ids must **never** be the same string. Internal `alias_of` / `extends` public entries.

## Public registries

```python
from taudio_models import PublicAssetRegistry, open_capability_registry, register_capability

assets = PublicAssetRegistry()
print([a.id for a in assets.list_assets()])  # deepfilternet3, ...

caps = open_capability_registry()
print([c.id for c in caps.list_capabilities()])  # denoise.speech
# caps.run_file("denoise.speech", "in.wav", "out/")  # needs vendored DF + libdf
```

Register more public capabilities with `@register_capability("something.generic")`.

## Catalog ModelRegistry (still available)

```python
from taudio_models import open_registry

reg = open_registry()
loaded = reg.load_model("deepfilter", {"version": "3", "is_gpu": False})
# loaded.backend describes public_capability + public_asset for the engine bridge
```

## Types

| Type | Role |
|------|------|
| `PublicAsset` | Public resource card |
| `PublicCapability` | Public capability + optional `run_file` |
| `ModelInfo` / `ModelParams` | Catalog cards |
| `LoadedModel` | Handle for closed engine |

## Engine (closed)

Prefer internal capability ids:

```python
engine.process_file("noisy.wav", "dn.speech", "out/")
```
