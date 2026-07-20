# Open adapter API (taudio-models)

Design: [adapter-layer.md](adapter-layer.md)

## Role

| Layer | Repo | Responsibility |
|-------|------|----------------|
| Upstream | `libs/` | OSS inference |
| Thin adapters | `backends/` | Map one lib → unified runners |
| **Adapter** | this package | Register capabilities; `run_file` / `run_array` |
| Product | TaudioProcess | Register private extensions; call adapter only |

## Call

```python
from taudio_models import open_capability_registry

adapter = open_capability_registry()
adapter.run_file("denoise.speech", "in.wav", "out/")
# enhanced, sr = adapter.run_array("denoise.speech", audio, sample_rate)
```

Private process uses `taudio.open_adapter()` so private extensions are registered on the same layer.

## Register (open or private runtime)

```python
from taudio_models import register_capability, PublicCapability

@register_capability("something.generic")
def build(reg):
    ...
    return PublicCapability(...)
```

Asset aliases (private short names): `PublicAssetRegistry.register_alias("de3", "deepfilternet3")`.
